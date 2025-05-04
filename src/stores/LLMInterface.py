# pylint: disable=trailing-whitespace
from abc import ABC, abstractmethod

class LLMInterface(ABC):
    """
    An abstract base class for defining the interface of a Large Language Model (LLM).
    This interface includes methods for setting models, generating text, embedding text,
    and constructing prompts.
    """
    
    @abstractmethod # to force using the method
    def set_generation_model(self, model_id: str):
        """
        Set the generation model to be used by the LLM.

        Args:
            model_id (str): The identifier of the generation model.
        """
        
    
    @abstractmethod # to force using the method
    def set_embedding_model(self, model_id: str, embedding_size: int):
        """
        Set the embedding model to be used by the LLM.

        Args:
            model_id (str): The identifier of the embedding model.
        """

    
    @abstractmethod # to force using the method
    def generate_text(self, prompt: str, max_output_tokens:int,
                            temperature: float = None):
        """
        Generate text based on the given prompt using the specified parameters.

        Args:
            prompt (str): The input text to generate a response for.
            max_output_tokens (int): The maximum number of tokens in the output.
            temperature (float, optional): The sampling temperature for text generation.

        Returns:
            str: The generated text.
        """
        
    
    @abstractmethod # to force using the method
    def embed_text(self, text: str, document_type: str):
        """
        Embed the given text based on the specified document type.

        Args:
            text (str): The text to be embedded.
            document_type (str): The type of document the text belongs to.
        """
        
    
    @abstractmethod # to force using the method
    def construct_prompt(self, prompt: str, role: str):
        """
        Construct a prompt based on the given input and role.

        Args:
            prompt (str): The input text for the prompt.
            role (str): The role or context for the prompt construction.
        """
        
