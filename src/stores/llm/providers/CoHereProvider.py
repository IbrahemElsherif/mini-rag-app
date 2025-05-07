import time
import random
import logging
from ..LLMInterface import LLMInterface
from ..LLMEnums import CoHereEnums, DocumentTypeEnum
import cohere

class CoHereProvider(LLMInterface):
    
    def __init__(self, api_key: str, 
                        default_input_max_characters: int=1000,
                        default_generation_max_output_tokens: int=1000,
                        default_generation_temperaure: float=0.1):
        
        self.api_key = api_key
        
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperaure = default_generation_temperaure
        
        self.generation_model_id = None
        
        self.embedding_model_id = None
        self.embedding_size = None
        
        self.client = cohere.Client(api_key=self.api_key)

        self.enums = CoHereEnums

        self.logger = logging.getLogger(__name__)
        
        # Rate limiting parameters
        self.request_tokens = 100  # Number of requests per minute allowed (Cohere allows 100/min on free tier)
        self.last_request_time = time.time()
        self.token_refresh_rate = 100/60.0  # Tokens refreshed per second (100 tokens per minute)
        self.batch_size = 10  # Number of texts to batch in a single request
        self.last_token_refresh = time.time()

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        # helper method 
        return text[:self.default_input_max_characters].strip()
    
    def _refresh_tokens(self):
        """Refresh tokens based on the time elapsed since last refresh"""
        now = time.time()
        time_elapsed = now - self.last_token_refresh
        tokens_to_add = time_elapsed * self.token_refresh_rate
        self.request_tokens = min(100, self.request_tokens + tokens_to_add)
        self.last_token_refresh = now
    
    def _wait_for_token(self):
        """Wait until a token is available for a new request"""
        self._refresh_tokens()
        
        if self.request_tokens < 1:
            # Calculate time to wait until we have at least one token
            time_to_wait = (1 - self.request_tokens) / self.token_refresh_rate
            time_to_wait = max(0.1, time_to_wait)  # at least 100ms
            self.logger.warning(f"Rate limit reached. Waiting {time_to_wait:.2f} seconds for quota refresh...")
            time.sleep(time_to_wait)
            self._refresh_tokens()
        
        # Use a token
        self.request_tokens -= 1

    def generate_text(self, prompt: str, chat_history: list=[], max_output_tokens: int=None,
                            temperature: float = None):
        if not self.client:
            self.logger.error("Cohere client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Cohere was not set")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_generation_temperaure

        # Wait for rate limit token
        self._wait_for_token()
        
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = self.client.chat(
                    model = self.generation_model_id,
                    chat_history = chat_history,
                    message = self.process_text(prompt),
                    temperature=temperature,
                    max_tokens = max_output_tokens
                )

                if not response or not response.text:
                    self.logger.error("Error while generating text with CoHere")
                    return None

                return response.text
                
            except Exception as e:
                if "429" in str(e) or "too many requests" in str(e).lower():
                    # Severe rate limiting - reduce tokens and wait longer
                    self.request_tokens = 0  # Force a longer wait
                    retry_count += 1
                    wait_time = (4 ** retry_count) + random.uniform(0, 2)  # More aggressive backoff
                    self.logger.warning(f"Rate limited. Retrying in {wait_time:.2f} seconds... (Attempt {retry_count}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Error while generating text with Cohere: {str(e)}")
                    return None
        
        self.logger.error(f"Max retries exceeded when generating text with Cohere")
        return None

    def embed_text(self, text: str, document_type: str=None):
        """Embed a single text with rate limiting and error handling"""
        if not text:
            return None
        return self.embed_texts([text], document_type)[0]
    
    def embed_texts(self, texts: list, document_type: str=None):
        """Embed multiple texts with batching and rate limiting"""
        if not self.client:
            self.logger.error("Cohere client was not set")
            return [None] * len(texts)
            
        if not self.embedding_model_id:
            self.logger.error("Embedding model for Cohere was not set")
            return [None] * len(texts)
        
        if not texts:
            return []
            
        # Process texts
        processed_texts = [self.process_text(text) for text in texts]
        
        # Set input type based on document_type
        input_type = CoHereEnums.DOCUMENT.value
        if document_type == DocumentTypeEnum.QUERY.value:
            input_type = CoHereEnums.QUERY.value
        
        # Split into batches to reduce API calls
        results = []
        for i in range(0, len(processed_texts), self.batch_size):
            batch = processed_texts[i:i+self.batch_size]
            
            # Wait for rate limit token
            self._wait_for_token()
            
            # Implement exponential backoff
            max_retries = 5
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    self.logger.info(f"Embedding batch of {len(batch)} texts")
                    response = self.client.embed(
                        model = self.embedding_model_id,
                        texts = batch,
                        input_type = input_type,
                        embedding_types=['float']
                    )
                    
                    if response and hasattr(response, 'embeddings') and response.embeddings.float:
                        batch_results = response.embeddings.float
                        results.extend(batch_results)
                        success = True
                    else:
                        self.logger.error("No embeddings found in response")
                        results.extend([None] * len(batch))
                        success = True  # Still mark as success to move on
                        
                except Exception as e:
                    if "429" in str(e) or "too many requests" in str(e).lower():
                        # Severe rate limiting - reduce tokens and wait longer
                        self.request_tokens = 0  # Force a longer wait
                        retry_count += 1
                        wait_time = (4 ** retry_count) + random.uniform(0, 2)  # More aggressive backoff
                        self.logger.warning(f"Rate limited. Retrying in {wait_time:.2f} seconds... (Attempt {retry_count}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        self.logger.error(f"Error while embedding text with Cohere: {str(e)}")
                        results.extend([None] * len(batch))
                        success = True  # Mark as success to move on
            
            if not success:
                self.logger.error(f"Max retries exceeded when embedding batch")
                results.extend([None] * len(batch))
            
            # Always add a small delay between batches
            time.sleep(1)
                
        return results
    
    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "text": self.process_text(prompt),
        }