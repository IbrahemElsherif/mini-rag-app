# pylint: disable=trailing-whitespace
from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from .enums.DataBaseEnum import DataBaseEnum

class ProjectModel(BaseDataModel):
    
    def __init__(self, db_client: object):
        super().__init__(db_client)
        # initalise the model and points to the collection
        self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]

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
        if DataBaseEnum.COLLECTION_PROJECT_NAME.value not in all_collections:
            self.collection = self.db_client[DataBaseEnum.COLLECTION_PROJECT_NAME.value]
            indexes = Project.get_indexes()
            for index in indexes:
                await self.collection.create_index(
                    index["key"],
                    name=index["name"],
                    unique=index["unique"]
                )
            
    async def creat_project(self, project: Project):
        
        result = await self.collection.insert_one(project.model_dump(by_alias=True, exclude_unset=True))
        project.id = result.inserted_id
        # return result.inserted_id
        return project
    
    async def get_project_or_create_one(self, project_id: str):
        record = await self.collection.find_one({
            "project_id":project_id
            })

        if record is None:
            # create new project
            project= Project(project_id=project_id)
            project = await self.creat_project(project=project)
        
            return project

        return Project(**record) # turns the dict 
    
    async def get_all_projects(self, page: int=1, page_size: int=10): 
        
        # count total number of documents
        total_documents = await self.collection.count_documents({})
        
        # calculate total number of pages
        total_pages = total_documents // page_size
        if total_documents % page_size > 0:
            total_pages += 1
            
        cursor = self.collection.find().skip( (page -1) * page_size).limit(page_size)
        projects = []
        async for document in cursor:
            projects.append(
                Project(**document)
            )
        return projects, total_pages
