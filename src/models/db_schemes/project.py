from pydantic import BaseModel, Field, field_validator
from typing import Optional
from bson.objectid import ObjectId

class Project(BaseModel):
    id: Optional[ObjectId] = Field(None, alias="_id")
    project_id: str = Field(..., min_length=1)

    @field_validator('project_id') # static method 
    def validate_project_id(cls, value):
        if not value.isalnum():
            raise ValueError('project_id must be alphanumeric')
        
        return value

    class Config:
        arbitrary_types_allowed = True
        
    @classmethod  # static method 
    def get_indexes(cls):
        # definig the shape of the indecies
        return [
            {
                "key": [
                    ("project_id", 1) # 1 for ascending 
                ],
                "name": "project_id_index_1",
                "unique":True
            }
        ] 
    