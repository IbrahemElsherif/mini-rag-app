# pylint: disable=unused-import
import os
from .BaseController import BaseController
from .ProjectController import ProjectController
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from models import ProcessingEnum
from langchain_community.document_loaders import JSONLoader
import json

class ProcessController(BaseController):
    
    def __init__(self,project_id: str):
        super().__init__()
        
        self.project_id = project_id
        self.project_path = ProjectController.get_project_path(self, project_id=project_id)
        
    def get_file_extension(self, file_id: str):
        return os.path.splitext(file_id)[-1]
    
    def get_file_loader(self, file_id: str):
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(
            self.project_path, 
            file_id
        )
        
        # check if file exists
        if not os.path.exists(file_path):
            return None
        
        # Check if its txt
        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")
        # Check if its pdf
        if file_ext == ProcessingEnum.PDF.value:
            try:
                # Add error handling for PDF loading
                loader = PyMuPDFLoader(file_path)
                # Test if the loader works by loading a sample
                test = loader.load_and_split()
                return loader
            except Exception as e:
                print(f"Error loading PDF {file_id}: {str(e)}")
                # Fallback to plain text extraction if PyMuPDF fails
                import pdfplumber
                class SimplePDFLoader:
                    def __init__(self, file_path):
                        self.file_path = file_path
                    
                    def load(self):
                        from langchain.schema import Document
                        text = ""
                        with pdfplumber.open(self.file_path) as pdf:
                            for page in pdf.pages:
                                text += page.extract_text() or ""
                                text += "\n\n"
                        
                        metadata = {"source": self.file_path}
                        return [Document(page_content=text, metadata=metadata)]
                
                return SimplePDFLoader(file_path)
        
        return None
    
    def get_file_content(self, file_id: str):
    
        loader = self.get_file_loader(file_id=file_id)
        # check for data in loader
        if loader:
            return loader.load()

        return None
    
    def process_file_content(self, file_content: list, file_id: str, 
                            chunk_size: int=1000, overlap_size: int=200):
    
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            length_function=len, # can be lambda function
        )
        
        file_content_texts = [
            rec.page_content
            for rec in file_content
        ]
        
        file_content_metadata = [
            rec.metadata
            for rec in file_content
        ]
        
        chunks = text_splitter.create_documents(
            file_content_texts,
            metadatas=file_content_metadata # to get meta data for each subof text
        )
        
        return chunks