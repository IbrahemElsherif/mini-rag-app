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
        
class CoHereEnums(Enum):
    
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT"
    
    DOCUMENT = "search_document"
    QUERY = "search_query"
    
class GoogleEnums(Enum):
    pass
class DocumentTypeEnum(Enum):
    DOCUMENT = "document"
    QUERY = "query"