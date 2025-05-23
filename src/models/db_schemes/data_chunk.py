from pydantic import BaseModel, Field, validator
from typing import Optional
from bson.objectid import ObjectId

class DataChunk(BaseModel):
    id: Optional[ObjectId] = Field(None, alias="_id")
    chunk_text: str = Field(..., min_length=1)
    chunk_metadata: dict
    chunk_order: int = Field(..., gt=0)
    chunk_project_id: ObjectId
    chunk_asset_id: ObjectId

    class Config:
        arbitrary_types_allowed = True

    @classmethod  # static method 
    def get_indexes(cls):
        # definig the shape of the indecies
        return [
            {
                "key": [
                    ("chunk_project_id", 1) # 1 for ascending 
                ],
                "name": "chunk_project_id_index_1",
                "unique": False # because of multiple chunks with the same project_id
            }
        ] 
    
# class RetrievedDocument(BaseModel):
#     id: str = None
#     score: float 
#     text: str  # This is the required field that was missing
#     metadata: dict = None
    
#     def dict(self):
#         return {
#             "id": self.id,
#             "score": self.score,
#             "text": self.text,
#             "metadata": self.metadata
#         }
class RetrievedDocument(BaseModel):
    text: str
    score: float
