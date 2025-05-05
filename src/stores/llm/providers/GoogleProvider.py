from google import genai
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


        response = self.client.models.generate_content(
            model = self.generation_model_id,
            contents = chat_history,
            config = self.client.models.types.GenerateContentConfigOrDict(
                max_tokens = max_output_tokens,
                temperature = temperature
            )
        )
        
        if not response or not hasattr(response, 'text'):
            self.logger.error("Error while generating text with Google")
            return None
    
        return response.text