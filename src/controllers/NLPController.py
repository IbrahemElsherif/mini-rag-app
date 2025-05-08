from .BaseController import BaseController
from models.db_schemes import Project, DataChunk
from stores.llm.LLMEnums import DocumentTypeEnum
from typing import List
import json
import re

class NLPController(BaseController):

    def __init__(self, vectordb_client, generation_client, 
                embedding_client, template_parser):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser

    def create_collection_name(self, project_id: str):
        return f"collection_{project_id}".strip()
    
    def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        return self.vectordb_client.delete_collection(collection_name=collection_name)
    
    def get_vector_db_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info = self.vectordb_client.get_collection_info(collection_name=collection_name)

        # Turn any objects into JSON safe type
        return json.loads(
            json.dumps(collection_info, default=lambda x: x.__dict__)
        )

    def index_into_vector_db(self, project: Project, chunks: List[DataChunk],
                               chunks_ids: List[int], 
                               do_reset: bool = False):
        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: manage items
        texts = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]
        
        # Use batch embedding instead of individual embeddings
        vectors = self.embedding_client.embed_texts(
            texts=texts,
            document_type=DocumentTypeEnum.DOCUMENT.value
        )

        # step3: create collection if not exists
        _ = self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset,
        )

        # step4: insert into vector db
        _ = self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=chunks_ids,
        )

        return True
    
    def search_vector_db_collection(self, project: Project, text: str, limit: int = 10):

        # step1: get collection name
        collection_name = self.create_collection_name(project_id=project.project_id)

        # step2: get text embedding vector
        vector = self.embedding_client.embed_text(text=text, 
                                                document_type=DocumentTypeEnum.QUERY.value)

        if not vector or len(vector) == 0:
            return False

        # step3: do semantic search
        results = self.vectordb_client.search_by_vector(
            collection_name=collection_name,
            vector=vector,
            limit=limit
        )

        if not results:
            return False

        return results
    
    def answer_rag_question(self, project: Project, query: str, limit: int = 10):
        # Define common questions with exact answers
        common_questions = {
            "من أنت": "أنا مساعد طلاب ومتدربين المعهد السعودي العالي المتخصص للتدريب، هنا لمساعدتك ومعلوماتك عن برامج المعهد.",
            "من انت": "أنا مساعد طلاب ومتدربين المعهد السعودي العالي المتخصص للتدريب، هنا لمساعدتك ومعلوماتك عن برامج المعهد.",
            "عرف نفسك": "أنا مساعد طلاب ومتدربين المعهد السعودي العالي المتخصص للتدريب، هنا لمساعدتك ومعلوماتك عن برامج المعهد.",
        }
        
        # Check for common questions first
        for question_fragment, predefined_answer in common_questions.items():
            if question_fragment in query.lower():
                return predefined_answer, "", []
        
        # Process other questions
        answer, full_prompt, chat_history = None, None, None
        
        # Get related documents
        retrieved_documents = self.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit,
        )
        
        if not retrieved_documents or len(retrieved_documents) == 0:
            return "عذراً، لا توجد لدي معلومات كافية عن هذا الموضوع. يرجى التواصل مع المعهد السعودي العالي للحصول على مزيد من المعلومات.", "", []
        
        # step2: Construct LLM prompt
        system_prompt = self.template_parser.get("rag", "system_prompt")

        documents_prompts = "\n".join([
            self.template_parser.get("rag", "document_prompt", {
                    "doc_num": idx + 1,
                    "chunk_text": doc.text,
            })
            for idx, doc in enumerate(retrieved_documents)
        ]) 

        footer_prompt = self.template_parser.get("rag", "footer_prompt",{
            "query":query
        })

        # step3: Construct Generation Client Prompts
        chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value,
            )
        ]

        full_prompt = "\n\n".join([ documents_prompts,  footer_prompt])

        # step4: Retrieve the Answer
        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history
        )
        
        # CRITICAL: Complete replacement of post-processing
        if answer:
            import re
            
            # DRASTIC APPROACH: Extract only clear Arabic text content
            # This removes ALL document markers, formatting, English text
            
            # 1. Remove any line with document markers
            lines = answer.split('\n')
            clean_lines = []
            for line in lines:
                if not any(marker in line.lower() for marker in [
                    'document', 'content', 'المستند', 'المحتوى', '##', '###', 
                    'doc', 'no:', 'رقم:'
                ]):
                    clean_lines.append(line)
            
            # 2. Join filtered lines
            answer = '\n'.join(clean_lines)
            
            # 3. Apply more aggressive cleaning
            # Remove any remaining document markers
            patterns = [
                r'document no:.*?content:',
                r'document \d+:.*?content:',
                r'##.*?##',
                r'###.*?###',
                r'المستند رقم:.*?المحتوى:',
                r'المستند \d+:.*?المحتوى:',
                r'content:.*?:',
            ]
            
            for pattern in patterns:
                answer = re.sub(pattern, '', answer, flags=re.DOTALL|re.IGNORECASE)
            
            # 4. Remove any single-character lines which are often remnants
            lines = answer.split('\n')
            answer = '\n'.join([l for l in lines if len(l.strip()) > 1])
            
            # 5. Final cleanup
            answer = re.sub(r'[#]+', '', answer)
            answer = re.sub(r'\n{3,}', '\n\n', answer)
            answer = re.sub(r'\s{2,}', ' ', answer)
            answer = answer.strip()
            
            # 6. Validate if answer still contains document markers
            if any(marker in answer.lower() for marker in ['document', 'content', '##', '###']):
                return "عذراً، لا توجد لدي معلومات كافية عن هذا الموضوع. يرجى التواصل مع المعهد السعودي العالي للحصول على مزيد من المعلومات.", "", []
        
        return answer, full_prompt, chat_history

