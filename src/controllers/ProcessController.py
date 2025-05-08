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
import logging
import traceback
from langchain.schema import Document

logger = logging.getLogger('uvicorn.error')

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
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        # Check if its txt
        if file_ext == ProcessingEnum.TXT.value:
            try:
                return TextLoader(file_path, encoding="utf-8")
            except Exception as e:
                logger.error(f"Error loading text file {file_id}: {str(e)}")
                return None
            
        # Check if its pdf
        if file_ext == ProcessingEnum.PDF.value:
            try:
                # Create a safe PDF loader class that handles errors
                class SafePyMuPDFLoader:
                    def __init__(self, file_path):
                        self.file_path = file_path
                    
                    def load(self):
                        try:
                            # Try PyMuPDF first
                            loader = PyMuPDFLoader(self.file_path)
                            return loader.load()
                        except Exception as e:
                            logger.error(f"PyMuPDF failed: {str(e)}")
                            logger.error(traceback.format_exc())
                            
                            # Fallback to manual PDF text extraction
                            try:
                                import fitz  # PyMuPDF
                                text = ""
                                metadata = {"source": self.file_path}
                                
                                doc = fitz.open(self.file_path)
                                for page_num, page in enumerate(doc):
                                    text += page.get_text()
                                    text += "\n\n"
                                
                                # Return at least something if we found text
                                if text.strip():
                                    return [Document(page_content=text, metadata=metadata)]
                                return []
                            except Exception as inner_e:
                                logger.error(f"Fallback PDF extraction failed: {str(inner_e)}")
                                # Return empty document rather than failing
                                return [Document(page_content="", metadata={"source": self.file_path, "error": "Failed to extract text"})]
                
                return SafePyMuPDFLoader(file_path)
                
            except Exception as e:
                logger.error(f"Error setting up PDF loader for {file_id}: {str(e)}")
                return None
        
        return None
    
    def get_file_content(self, file_id: str):
    
        loader = self.get_file_loader(file_id=file_id)
        # check for data in loader
        if loader:
            return loader.load()

        return None
    
    def process_file_content(self, file_content: list, file_id: str, 
                            chunk_size: int=1000, overlap_size: int=200):
        # If file_content is empty or None, return empty list instead of None
        if not file_content or len(file_content) == 0:
            logger.error(f"No content found in file: {file_id}")
            return []
        
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=overlap_size,
                length_function=len,
            )
            
            file_content_texts = [
                rec.page_content
                for rec in file_content
                # Skip empty content
                if hasattr(rec, 'page_content') and rec.page_content and rec.page_content.strip()
            ]
            
            # If we have no valid text content, return empty list
            if not file_content_texts:
                logger.error(f"No valid text content in file: {file_id}")
                return []
            
            file_content_metadata = [
                rec.metadata
                for rec in file_content
                if hasattr(rec, 'page_content') and rec.page_content and rec.page_content.strip()
            ]
            
            chunks = text_splitter.create_documents(
                file_content_texts,
                metadatas=file_content_metadata
            )
            
            return chunks
        except Exception as e:
            logger.error(f"Error processing file content for {file_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return []