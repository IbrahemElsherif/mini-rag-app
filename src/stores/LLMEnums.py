from enum import Enum

class LLMEnums(Enum):
    
    # names of the providers
    OPENAI= "OPENAI"
    COHERE= "COHERE"
    GOOGLE= "GOOGLE" 
    
class OpenAIEnums(Enum):
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"