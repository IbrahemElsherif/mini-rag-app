from google import genai
from google.genai import types
import logging
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

    def set_generation_model(self, model_id: str):
        
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):

        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        # helper method 
        return text[:self.default_input_max_characters].strip()
    
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
            
        response = self.client.models.generate_content(
            model = self.generation_model_id,
            contents = chat_history,
            config = types.GenerateContentConfig(
                max_tokens = max_output_tokens,
                temperature = temperature
            )
        )
        
        if not response or not hasattr(response, 'text'):
            self.logger.error("Error while generating text with Google")
            return None
    
        return response.text
    
    # def embed_text(self, text: str, document_type: str=None):
    #     if not self.client:
    #         self.logger.error("Google client was not set")
    #         return None
    #     if not self.embedding_model_id:
    #         self.logger.error("Embedding model for Google was not set")
    #         return None
            
    #     text = self.process_text(text)
       
    #     embed_config = None
    #     if document_type:
    #         embed_config = types.EmbedContentConfig(
    #             task_type=document_type
    #             )
    #     try:    # According to Google Generative AI SDK documentation
    #         embedding_result = self.client.models.embed_content(
    #             model=self.embedding_model_id,
    #             contents=text,  # Parameter is named "contents", not "content"
    #             config=config
    #         )
    #         if not embedding_result or not hasattr(embedding_result, 'embedding'):
    #             self.logger.error("Error while embedding text with Google")
    #             return None
        
    #     return embedding_result.embeddings
    def embed_text(self, text: str, document_type: str=None):
        if not self.client:
            self.logger.error("Google client was not set")
            return None
        if not self.embedding_model_id:
            self.logger.error("Embedding model for Google was not set")
            return None
            
        text = self.process_text(text)

        embed_config = None
        if document_type:
            embed_config = types.EmbedContentConfig(
                task_type=document_type
                )
        try:    # According to Google Generative AI SDK documentation
            embedding_result = self.client.models.embed_content(
                model=self.embedding_model_id,
                contents=text,  # Parameter is named "contents", not "content"
                config=embed_config  # Changed from config to embed_config to match the variable name
            )

            if embedding_result and hasattr(embedding_result, 'embeddings') and len(embedding_result.embeddings) > 0:
                return embedding_result.embeddings[0].values
            else:
                self.logger.error("No embeddings found in response")
                return None

        except Exception as e:
            self.logger.error(f"Error while embedding text with Google: {str(e)}")
            return None

    def construct_prompt(self, prompt: str, role: str):
        # According to Google Generative AI documentation
        return {
            "role": role,
            "parts": [{"text": self.process_text(prompt)}]
        }