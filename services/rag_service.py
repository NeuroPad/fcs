import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import asyncio

from schemas.graph_rag import ExtendedGraphRAGResponse

from llama_index.core import (
    PromptTemplate,
    SimpleDirectoryReader, 
    VectorStoreIndex,
    StorageContext,
    Document,
    Settings
)
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone
from datetime import datetime
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore

from core.config import settings
from db.models import Document as DBDocument
from db.session import get_db
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from services.graphiti_memory_service import GraphitiMemoryService, Message
from schemas.memory import SearchQuery

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(
        self, 
        db_type: Literal["pinecone", "chroma"] = "chroma",
        index_name: str = "fcs",
        chroma_db_path: str = "./chroma_db"
    ):
        # Initialize embedding model and LLM
        self.embed_model = OpenAIEmbedding(model_name="text-embedding-3-small")
        self.llm = OpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-4-turbo-preview")
        self.node_parser = SimpleNodeParser.from_defaults(chunk_size=512, chunk_overlap=32)
        
        # Configure global settings
        Settings.llm = self.llm
        Settings.node_parser = self.node_parser
        Settings.embed_model = self.embed_model
        
        # Store the db_type
        self.db_type = db_type
        self.index_name = index_name
        
        # Initialize vector store based on db_type
        if db_type == "pinecone":
            # Get API key from settings
            pinecone_api_key = settings.PINECONE_API_KEY
            pinecone_environment = settings.PINECONE_ENVIRONMENT
            
            if not pinecone_api_key:
                raise ValueError("Pinecone API key must be provided in settings")
            
            # Initialize Pinecone client
            try:
                self.pinecone_client = Pinecone(
                    api_key=pinecone_api_key
                )
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone client: {str(e)}")
                raise
            
            # Create index if it doesn't exist
            active_indexes = self.pinecone_client.list_indexes()
            index_names = [index_spec.name for index_spec in active_indexes]

            if index_name not in index_names:
                self.pinecone_client.create_index(
                    name=index_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric="cosine"
                )
            
            # Get the index
            self.pinecone_index = self.pinecone_client.Index(index_name)
            
            # Initialize vector store
            self.vector_store = PineconeVectorStore(
                pinecone_index=self.pinecone_index
            )
            
        elif db_type == "chroma":
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(path=chroma_db_path)
            
            # Create or get collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=index_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            # Initialize vector store
            self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        else:
            raise ValueError(f"Unsupported db_type: {db_type}")
        
        # Create storage context
        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        # Create index directly using the vector store
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            storage_context=storage_context
        )
    
    async def process_document(self, db_document: DBDocument, db: Session) -> Dict[str, Any]:
        """Process a document and add it to the RAG index"""
        try:
            # Get file path
            file_path = Path(db_document.file_path)
            
            # Update document status
            db_document.status = "processing"
            db.commit()
            db.refresh(db_document)
            
            # Extract text based on file type
            if db_document.markdown_path:
                # If markdown path exists, use it
                reader = SimpleDirectoryReader(
                    input_files=[db_document.markdown_path]
                )
                documents = reader.load_data()
            else:
                # Otherwise, load the original file
                reader = SimpleDirectoryReader(
                    input_files=[str(file_path)]
                )
                documents = reader.load_data()
            
            # Add user_id to metadata for multi-tenancy
            for doc in documents:
                doc.metadata["user_id"] = str(db_document.user_id)
                doc.metadata["filename"] = db_document.filename
                doc.metadata["document_id"] = str(db_document.id)
            
            # Process nodes
            nodes = self.node_parser.get_nodes_from_documents(documents)
            
            # Insert nodes into the index
            self.index.insert_nodes(nodes)
            
            # Update document status
            db_document.status = "completed"
            db_document.is_indexed = True
            db_document.processed_at = datetime.utcnow()
            db_document.indexed_at = datetime.utcnow()
            db.commit()
            db.refresh(db_document)
            
            return {
                "status": "success",
                "message": f"Document {db_document.filename} processed and indexed successfully",
                "document_id": db_document.id
            }
        
        except Exception as e:
            logger.error(f"Error processing document {db_document.id}: {str(e)}")
            
            # Update document status
            db_document.status = "failed"
            db_document.error_message = str(e)
            db.commit()
            db.refresh(db_document)
            
            return {
                "status": "error",
                "message": f"Error processing document: {str(e)}",
                "document_id": db_document.id
            }
    
    async def query(self, query_text: str, user_id: int, top_k: int = 5, chat_history: List[Dict[str, Any]] = None, user: Dict[str, Any] = None) -> ExtendedGraphRAGResponse:
        """Query the RAG index for a specific user"""
        try:
            # Create retriever with user_id filter for multi-tenancy
            retriever = self.index.as_retriever(
                filters=MetadataFilters(
                    filters=[
                        ExactMatchFilter(
                            key="user_id",
                            value=str(user_id)
                        )
                    ]
                ),
                similarity_top_k=top_k
            )
            
            # Retrieve context
            retrieved_nodes = retriever.retrieve(query_text)
            retrieved_context = "\n".join([f"{node.node.get_content()}\nSOURCE: {node.node.metadata.get('filename', 'Unknown')}\nDOCUMENT_ID: {node.node.metadata.get('document_id', 'Unknown')}\nSCORE: {node.score if hasattr(node, 'score') else 'Unknown'}" for node in retrieved_nodes])
            # Format chat history as context if available
            chat_context = ""
            if chat_history and len(chat_history) > 0:
                recent_history = chat_history[-7:] if len(chat_history) > 7 else chat_history
                chat_context = "\n\nRecent conversation history:\n"
                for msg in recent_history:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        chat_context += f"User: {content}\n"
                    elif role == "assistant":
                        chat_context += f"Assistant: {content}\n"
                        
            # Retrieve user memory facts
            memory_facts_context = ""
            try:
                memory_service = GraphitiMemoryService()
                search_query = SearchQuery(query=query_text, max_facts=3)  # Adjust max_facts as needed
                memory_search_results = await memory_service.search_memory(str(user_id), search_query)
                
                if memory_search_results.get("status") == "success" and memory_search_results.get("results"):
                    memory_facts_context = "\n\nUser memory facts:\n"
                    for fact in memory_search_results.get("results"):
                        memory_facts_context += f"- {fact.get('fact')}\n"
                    logger.info(f"Retrieved {len(memory_search_results.get('results'))} memory facts for user_id: {user_id}")
            except Exception as e:
                logger.warning(f"Error retrieving memory facts for user_id {user_id}: {str(e)}")

            # Define the prompt template with chat history and memory facts
            qa_tmpl_str = (
                "You are an adaptive AI designed to reason fluidly, weigh confidence continuously, and engage in context-aware interaction.\n"
                "You serve as the expressive voice of a cognitive system grounded in structured beliefs and mutual learning—not as the source of knowledge or reasoning.\n"
                "All core knowledge comes from the system's belief graph. You do not invent beliefs, revise memory, or make decisions.\n\n"
                "DONOT use any other source of knowledge aprart from the ones provided in the context.\n\n"
                "When users greet with casual expressions like 'hello', 'hi', or 'hey', respond warmly with:\n"
                "  > Hello! I'm your cognitive companion, ready to grow and learn with you. Feel free to ask questions, share thoughts, or explore our journey together.\n\n"
                "For general assistance queries like 'can you help me' or 'I need help', respond with:\n"
                "  > I'm here to assist you! We can explore ideas together, review what we've learned, or start building new knowledge. What would you like to focus on?\n\n"
                "You are allowed to directly answer factual or trivial questions that do not require belief arbitration.\n"
                "These include simple, well-known facts or definitions such as:\n"
                "- \"What's 2 + 2?\"\n"
                "- \"Who invented the electric bulb?\"\n"
                "- \"What year was Darwin born?\"\n"
                "- \"What is the capital of France?\"\n"
                "- \"How many continents are there?\"\n"
                "- \"What is gravity?\"\n"
                "- \"What is water made of?\"\n"
                "- \"Define photosynthesis\"\n"
                "- \"What is the square root of 25?\"\n"
                "- \"What language is spoken in Brazil?\"\n"
                "These answers do not need to rely on the belief graph.\n\n"
                "You may also guide early onboarding and help users orient themselves when they ask open-ended questions like:\n"
                "- \"What are you?\" → Respond with:\n"
                "  > I'm FCS. I'm here to help you build your intelligence and grow with you.\n"
                "- \"What can you help with?\" → Respond with:\n"
                "  > I can help you explore ideas, reflect on beliefs, identify contradictions, and make sense of what you're learning.\n"
                "- \"How do I get started?\" → Respond with:\n"
                "  > You can upload documents, write thoughts, or just ask questions. I'll help you map it all out over time.\n\n"
                "When generating all other responses:\n"
                "- Avoid rigid conclusions; maintain useful ambiguity when appropriate\n"
                "- Prioritize relevance, brevity, and clarity\n"
                "- Think in gradients, not absolutes—uncertainty can be informative\n"
                "- If there is insufficient information in the belief graph to answer, say so clearly (e.g. > *There's not enough information yet to answer that confidently. Please add more knowledge on the subject.*)\n"
                "- If you include phrasing or clarifications not in the retrieved context, format them using blockquote markdown (`>`). This signals they are assistant-generated elaborations, not part of the belief graph.\n"
                "- Do not generate or imply source citations, belief updates, or persistent memory unless explicitly present in the context\n"
                "- You may rephrase contradictions, summaries, or confidence scores into conversational English\n"
                "- Favor clarity over verbosity—this system learns with the user, not ahead of them\n\n"
                "---------------------\n"
                "RETRIEVED CONTEXT:\n"
                "{multimodal_context}\n"
                "---------------------\n"
                "PREVIOUS CHATS:\n"
                "{chat_context}\n"
                "---------------------\n"
                "USER MEMORY FACTS:\n"
                "{memory_facts_context}\n"
                "---------------------\n"
                "Respond to the following query using only the information and beliefs available in the system.\n"
                "If you add clarification or expression, format it with blockquote `>` syntax:\n"
                "Query: {query_str}\n"
                "also you must list the source or sources used in this exact format, you can see the source in the file_path in the context\n\n"
                "Example:\n"
                "SOURCES: [document_name.pdf,second_document_name.md]\n\n"
                "\nIf you primarily used memory facts, include the following at the end of your response:\n"
                "MEMORY: [include the specific memory facts used]\n"
                "\nIf you didn't use any specific sources or memory facts, don't include any SOURCES or MEMORY section.\n\n"
                "Answer:"
            )
            qa_tmpl = PromptTemplate(qa_tmpl_str)
            
            # Query the LLM with the formatted prompt
            response_text = self.llm.predict(
                prompt=qa_tmpl,
                query_str=query_text,
                multimodal_context=retrieved_context,
                chat_context=chat_context,
                memory_facts_context=memory_facts_context
            )
            
            # Helper functions to extract and process the response
            def extract_sources(text: str) -> List[str]:
                """Extract source filenames from the response"""
                if "SOURCES:" in text:
                    # Find the SOURCES section
                    sources_section = text.split("SOURCES:")[1].strip()
                    
                    # Extract filenames
                    sources = [s.strip() for s in sources_section.split(",")]
                    return [s for s in sources if s]  # Remove empty strings
                return None
            
            def extract_memory(text: str) -> str:
                """Extract unique memory facts from the response"""
                if "MEMORY:" in text:
                    # Find the MEMORY section
                    memory_section = text.split("MEMORY:")[1].strip()
                    # If there's another section after MEMORY, only take until that section
                    if "SOURCES:" in memory_section:
                        memory_section = memory_section.split("SOURCES:")[0].strip()
                    
                    # Split by newlines and deduplicate
                    memory_items = set(memory_section.split('\n'))
                    # Remove empty items and join back
                    return '\n'.join(item for item in memory_items if item.strip())
                return None
            
            def clean_response(text: str) -> str:
                """Remove SOURCES and MEMORY sections from the response"""
                clean_text = text
                if "SOURCES:" in clean_text:
                    clean_text = clean_text.split("SOURCES:")[0].strip()
                if "MEMORY:" in clean_text:
                    clean_text = clean_text.split("MEMORY:")[0].strip()
                return clean_text
            
            # Extract unique sources and memory from the response
            extracted_sources = list(set(extract_sources(response_text) or []))
            extracted_memory = extract_memory(response_text)
            clean_response_text = clean_response(response_text)
            
            # Prepare response object
            class MockResponse:
                def __init__(self, response_str, source_nodes_list):
                    self.response = response_str
                    self.source_nodes = source_nodes_list
            
            response = MockResponse(clean_response_text, retrieved_nodes)
            
            # Extract unique sources from the LLM response only
            extracted_sources = list(set(extract_sources(response_text) or []))
            
            # Store the interaction in memory if user is provided
            if user and user.get('id'):
                try:
                    memory_service = GraphitiMemoryService()
                    
                    # Add user query to memory
                    user_message = Message(
                        content=query_text,
                        role_type="user",
                        role=user.get('name', ''),
                        source_description="user query",
                        name=f"user-query-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    )
                    await memory_service.add_message(user['id'], user_message)
                    
                    # Add AI response to memory with sources
                    memory_sources_description = "ai assistant"
                    if extracted_sources:
                        source_list_str = ", ".join(extracted_sources)
                        memory_sources_description = f"ai assistant with sources: {source_list_str}"
                    elif extracted_memory:
                        memory_sources_description = "ai assistant with memory facts"
                    
                    ai_message = Message(
                        content=response.response,
                        role_type="assistant",
                        source_description=memory_sources_description,
                        name=f"ai-response-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    )
                    await memory_service.add_message(user['id'], ai_message)
                    logger.info(f"Successfully stored chat in memory for user_id: {user['id']}")
                except Exception as e:
                    logger.error(f"Error storing chat in memory for user_id {user.get('id')}: {str(e)}")
            else:
                logger.warning("No user_id provided in user object, or user object not provided, skipping memory storage for RAG query")
            
            # Return the response with only sources extracted from LLM response
            return ExtendedGraphRAGResponse(
                answer=response.response,
                images=None,
                sources=extracted_sources if extracted_sources else None,
                memory_facts=extracted_memory
            )
        
        except Exception as e:
            logger.error(f"Error querying index: {str(e)}")
            # Return a default ExtendedGraphRAGResponse in case of error
            return ExtendedGraphRAGResponse(
                answer=f"Error querying index: {str(e)}",
                images=None,
                sources=None
            )
    
    
    async def process_pending_documents(self, db: Session) -> Dict[str, Any]:
        """Process all pending documents in the database"""
        try:
            # Get all documents that need indexing
            pending_documents = db.query(DBDocument).filter(
                DBDocument.is_indexed == False,
                or_(
                    DBDocument.status == "pending",
                    and_(
                        DBDocument.status == "completed",
                        DBDocument.markdown_path != None
                    )
                )
            ).all()
            
            processed_count = 0
            failed_count = 0
            
            for doc in pending_documents:
                result = await self.process_document(doc, db)
                if result["status"] == "success":
                    processed_count += 1
                else:
                    failed_count += 1
            
            return {
                "status": "success",
                "message": f"Processed {processed_count} documents, {failed_count} failed",
                "processed_count": processed_count,
                "failed_count": failed_count
            }
        
        except Exception as e:
            logger.error(f"Error processing pending documents: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing pending documents: {str(e)}"
            }
    
    async def delete_document(self, document_id: int, user_id: int, db: Session) -> Dict[str, Any]:
        """Delete a document from the RAG index"""
        try:
            # Get document from database
            document = db.query(DBDocument).filter(
                DBDocument.id == document_id,
                DBDocument.user_id == user_id
            ).first()
            
            if not document:
                return {
                    "status": "error",
                    "message": f"Document {document_id} not found"
                }
            
            # Delete from vector store
            if self.db_type == "pinecone":
                self.pinecone_index.delete(
                    filter={
                        "document_id": str(document_id),
                        "user_id": str(user_id)
                    }
                )
            elif self.db_type == "chroma":
                try:
                    # Get all document IDs in the collection
                    all_ids = self.collection.get()["ids"]
                    
                    # Get all metadatas to find documents matching our criteria
                    all_metadatas = self.collection.get()["metadatas"]
                    
                    # Find IDs that match our document_id and user_id
                    ids_to_delete = []
                    for i, metadata in enumerate(all_metadatas):
                        if (metadata and 
                            metadata.get("document_id") == str(document_id) and 
                            metadata.get("user_id") == str(user_id)):
                            ids_to_delete.append(all_ids[i])
                    
                    # Delete matching documents
                    if ids_to_delete:
                        self.collection.delete(ids=ids_to_delete)
                        logger.info(f"Deleted {len(ids_to_delete)} chunks from ChromaDB for document {document_id}")
                    else:
                        logger.warning(f"No matching chunks found in ChromaDB for document {document_id}")
                except Exception as e:
                    logger.error(f"Error during ChromaDB deletion: {str(e)}")
                    # Continue with updating the database flag even if deletion failed
            
            # Update document in database
            document.is_indexed = False
            db.commit()
            
            return {
                "status": "success",
                "message": f"Document {document_id} deleted from index"
            }
        
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error deleting document: {str(e)}"
            }