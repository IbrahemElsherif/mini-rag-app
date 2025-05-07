import time
import random
import logging
from google import genai
from google.genai import types
from ..LLMInterface import LLMInterface
from ..LLMEnums import GoogleEnums

class GoogleProvider(LLMInterface):
    
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
        
        # from google docs
        self.client = genai.Client(api_key=self.api_key)
        
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting parameters
        self.request_tokens = 60  # Number of requests per minute allowed
        self.last_request_time = time.time()
        self.token_refresh_rate = 1.0  # Tokens refreshed per second
        self.batch_size = 5  # Number of texts to batch in a single request
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
        self.request_tokens = min(60, self.request_tokens + tokens_to_add)
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
            self.logger.error("Google client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Google was not set")
            return None
        
        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_generation_temperaure

        # Add the current prompt to chat history if provided
        if prompt:
            chat_history.append(self.construct_prompt(prompt=prompt, role=GoogleEnums.USER.value))
        
        # Wait for rate limit token
        self._wait_for_token()
        
        try:
            response = self.client.models.generate_content(
                model = self.generation_model_id,
                contents = chat_history,
                config = types.GenerateContentConfig(
                    max_output_tokens = max_output_tokens,
                    temperature = temperature
                )
            )
            
            if not response or not hasattr(response, 'text'):
                self.logger.error("Error while generating text with Google")
                return None
        
            return response.text
        except Exception as e:
            self.logger.error(f"Error while generating text with Google: {str(e)}")
            return None
    
    def embed_text(self, text: str, document_type: str=None):
        """Embed a single text with rate limiting and error handling"""
        return self.embed_texts([text], document_type)[0] if text else None
    
    def embed_texts(self, texts: list, document_type: str=None):
        """Embed multiple texts with batching and rate limiting"""
        if not self.client:
            self.logger.error("Google client was not set")
            return [None] * len(texts)
            
        if not self.embedding_model_id:
            self.logger.error("Embedding model for Google was not set")
            return [None] * len(texts)
        
        if not texts:
            return []
            
        # Process texts
        processed_texts = [self.process_text(text) for text in texts]
        
        # Map document types to Google's expected format
        task_type_mapping = {
            "document": "RETRIEVAL_DOCUMENT",
            "query": "RETRIEVAL_QUERY"
        }
        
        google_task_type = None
        if document_type:
            google_task_type = task_type_mapping.get(document_type.lower(), "RETRIEVAL_DOCUMENT")
        
        # Prepare config
        embed_config = None
        if google_task_type:
            embed_config = types.EmbedContentConfig(
                task_type=google_task_type
            )
        
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
                    embedding_result = self.client.models.embed_content(
                        model=self.embedding_model_id,
                        contents=batch,
                        config=embed_config
                    )
                    
                    if embedding_result and hasattr(embedding_result, 'embeddings') and len(embedding_result.embeddings) > 0:
                        batch_results = [emb.values for emb in embedding_result.embeddings]
                        results.extend(batch_results)
                        success = True
                    else:
                        self.logger.error("No embeddings found in response")
                        results.extend([None] * len(batch))
                        success = True  # Still mark as success to move on
                        
                except Exception as e:
                    if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                        # Severe rate limiting - reduce tokens and wait longer
                        self.request_tokens = 0  # Force a longer wait
                        retry_count += 1
                        wait_time = (4 ** retry_count) + random.uniform(0, 2)  # More aggressive backoff
                        self.logger.warning(f"Rate limited. Retrying in {wait_time:.2f} seconds... (Attempt {retry_count}/{max_retries})")
                        time.sleep(wait_time)
                    elif "INVALID_ARGUMENT" in str(e) and "task_type" in str(e):
                        # Task type issue - try without specifying task type
                        self.logger.warning("Invalid task_type. Retrying without task type specification.")
                        embed_config = None
                        retry_count += 1
                    else:
                        self.logger.error(f"Error while embedding text with Google: {str(e)}")
                        results.extend([None] * len(batch))
                        success = True  # Mark as success to move on
            
            if not success:
                self.logger.error(f"Max retries exceeded when embedding batch")
                results.extend([None] * len(batch))
            
            # Always add a small delay between batches
            time.sleep(1)
                
        return results

    def construct_prompt(self, prompt: str, role: str):
        # According to Google Generative AI documentation
        return {
            "role": role,
            "parts": [{"text": self.process_text(prompt)}]
        }