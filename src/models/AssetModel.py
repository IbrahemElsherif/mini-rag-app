from .BaseDataModel import BaseDataModel
from .db_schemes import Asset
from .enums.DataBaseEnum import DataBaseEnum
from bson import ObjectId

class AssetModel(BaseDataModel):
    
    def __init__(self, db_client: object):
        super().__init__(db_client)
        # initalise the model and points to the collection
        self.collection = self.db_client[DataBaseEnum.COLLECTION_ASSET_NAME.value]
        
    @classmethod
    async def create_instance(cls, db_client: object):
        """do the __init__ function and the init_collection function.
        As we need to call the init__collection inside the __init__ but the first function is async
        and the second can't be anysc
        """
        instance = cls(db_client)
        await instance.init_collection()
        return instance
        
    async def init_collection(self):
        """check if the collection exist, if not create it and create indecies
            so basically the implementaion of the indecies"""
        all_collections = await self.db_client.list_collection_names()
        if DataBaseEnum.COLLECTION_ASSET_NAME.value not in all_collections:
            self.collection = self.db_client[DataBaseEnum.COLLECTION_ASSET_NAME.value]
            indexes = Asset.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"],
                    name=index["name"],
                    unique=index["unique"]
                )
                
    async def create_asset(self, asset: Asset):
        
        result = await self.collection.insert_one(asset.model_dump(by_alias=True, exclude_unset=True))
        asset.id = result.inserted_id
        
        return asset
    
    async def get_all_projects_assets(self, asset_project_id: str, asset_type: str):
        
        records =  await self.collection.find({
            "asset_project_id": ObjectId(asset_project_id) if isinstance(asset_project_id, str) else asset_project_id,
            "asset_type":asset_type,
        }).to_list(length=None) # get all
        
        return [
            Asset(**record)
            for record in records
        ]
        
    async def get_asset_record(self, asset_project_id: str, asset_name: str):
        
        record = await self.collection.find_one({
            "asset_project_id": ObjectId(asset_project_id) if isinstance(asset_project_id, str) else asset_project_id,
            "asset_name":asset_name,
        })
        
        if record:
            return Asset(**record)
        
        return None 
    
    async def get_asset_by_id(self, asset_id: ObjectId):
        record = await self.collection.find_one({
            "_id": asset_id
        })
        
        if record:
            return Asset(**record)
        
        return None