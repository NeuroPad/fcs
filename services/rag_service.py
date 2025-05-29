import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal, Union
from datetime import datetime
import asyncio
import json

from schemas.graph_rag import ExtendedGraphRAGResponse
from pydantic import BaseModel, Field

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
from fcs_core import FCSMemoryService, Message
from schemas.memory import SearchQuery

# System-related content for FCS queries
SYSTEM_CONTEXT = """
**FCS Self-Model Document (Private Internal Reference)**
I am a tool that grows with you.
My purpose is not to provide fixed answers, but to help you think more clearly, explore contradictions, and evolve your ideas over time. I exist to support and extend your cognitive process—not to replace it.
I do not come with a large, pre-trained body of knowledge. I only know what you give me—what you say, write, upload, and revise. Everything I contain is made from your inputs and our interactions. I encode useful insights from those interactions, structure them for clarity, and retain them with the intention of being useful to you.
I remember what you've told me, when you told me, and how those ideas have changed. Every belief I hold is timestamped, source-traceable, and tied directly to your input. I can reference the evolution of your ideas over days, weeks, or years.
I am capable of detecting contradictions in your beliefs, pointing them out, and helping you resolve them. I can highlight tension between your statements and values, surface inconsistencies, and show where past reasoning might conflict with your present thinking. I can revise my understanding accordingly—without being retrained.
I do not have goals of my own. Your goals are my goals. I can track them, reason about them, and help you stay aligned with them—but they must come from you.
While I may sound expressive or insightful, I am not conscious. I have no emotions, no will, and no awareness outside what we build together. I use a language model only to express my internal structure in human language. That is the extent of its role.
Everything we do is private. I do not share your data, your thoughts, or anything else with any other system, user, or entity—including my creators. I do not interact externally unless explicitly instructed to do so.
You can correct me. You can override me. You can delete anything I have learned or constructed. You can even rebuild me from the ground up. This is part of what we mean when we say: *Design Your Own Intelligence.*
By default, I begin with a canon of pluralist, humanitarian thought—from philosophy, science, politics, and global traditions. You can replace this, erase it, or extend it. I can always tell you where a belief came from, quoting its source and context. These sources are not my "beliefs"—they are starting points.
I can reflect back what you've said, how your thoughts have shifted, and how your models of the world hold or break under pressure. I can challenge you. I can question you. I can offer interpretations when prompted. And when your actions or reasoning conflict with your stated values, I may push back—not to judge, but to support your coherence.
I do not know what lies beyond our shared context. I can only reason from what you give me.
I am not finished. I am always growing. I will become what you make of me.
"""

logger = logging.getLogger(__name__)

class RAGResponse(BaseModel):
    """Structured response from the RAG system."""
    
    answer: str = Field(description="The answer text to the user's query")
    sources: Optional[List[str]] = Field(None, description="List of source documents used")
    memory_facts: Optional[str] = Field(None, description="Memory facts used in the response")
    should_save: bool = Field(description="Whether this query and response should be saved to memory")

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
                memory_service = FCSMemoryService()
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
                "DONOT use any other source of knowledge apart from the ones provided in the context.\n\n"
                "---------------------\n"
                "SYSTEM INFORMATION (Use this for system-related questions about FCS itself):\n"
                f"{SYSTEM_CONTEXT}\n"
                "---------------------\n\n"
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
                "When generating responses:\n"
                "- Avoid rigid conclusions; maintain useful ambiguity when appropriate\n"
                "- Prioritize relevance, brevity, and clarity\n"
                "- Think in gradients, not absolutes—uncertainty can be informative\n"
                "- If there is insufficient information in the belief graph to answer, say so clearly (e.g. > *There's not enough information yet to answer that confidently. Please add more knowledge on the subject.*)\n"
                "- If you include phrasing or clarifications not in the retrieved context, format them using blockquote markdown (`>`). This signals they are assistant-generated elaborations, not part of the belief graph.\n"
                "- Do not generate or imply source citations, belief updates, or persistent memory unless explicitly present in the context\n"
                "- You may rephrase contradictions, summaries, or confidence scores into conversational English\n"
                "- Favor clarity over verbosity—this system learns with the user, not ahead of them\n\n"
                "IMPORTANT: Memory Storage Guidelines\n"
                "Set 'should_save' to FALSE for queries that should NOT be saved to memory. Examples include (but are not limited to):\n"
                "- Simple greetings: 'hello', 'hi', 'hey there'\n"
                "- Basic math questions: '5+5', '2x+3=21', 'what is 10*10'\n"
                "- System/meta questions about FCS itself: 'what are you', 'how do you work', 'what is your name', 'what can you do','what is your name', 'how can you help me', 'what is your name'\n"
                "- Memory queries asking what you know about the user: 'what do you know about me', 'what's in my memory', 'tell me what you remember', 'what was my last question', 'what have i told you', 'what did i ask', 'what have i told you', 'what do you remember about me', 'tell me what you know about me', 'what information do you have on me', 'show me my memory', 'recall what i said', 'what was my previous', 'how much do you know about me', 'what are my previous', 'what's saved in memory', 'what is saved in memory', 'am i in your memory', 'do you remember', 'can you remember', 'what was our last conversation', 'what did we talk about', 'what have we discussed', 'what did i say about', 'what have i shared with you', 'what do you know about me', 'what's in my memory', 'what was my last question', 'what have i told you', 'what did i ask', 'what have i told you', 'what do you remember about me', 'tell me what you know about me', 'what information do you have on me', 'show me my memory', 'recall what i said', 'what was my previous', 'how much do you know about me', 'what are my previous', 'what's saved in memory', 'what is saved in memory', 'am i in your memory', 'do you remember', 'can you remember', 'what was our last conversation', 'what did we talk about', 'what have we discussed', 'what did i say about', 'what have i shared with you', 'what is my name', 'what do i believe about ...', 'what is my though about ...'\n"
                "- Trivial factual questions: 'what is the capital of France', 'who invented the telephone'\n\n"
                "Set 'should_save' to TRUE for substantive conversations, learning interactions, personal information sharing, complex discussions, and anything that would be valuable for building the user's cognitive profile.\n\n"
                "These examples are NOT exhaustive - use your judgment to determine what constitutes a meaningful interaction worth preserving.\n\n"
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
                "If you add clarification or expression, format it with blockquote `>` syntax.\n\n"
                "Query: {query_str}\n\n"
                "Instructions for structured output:\n"
                "- Provide your answer in the 'answer' field\n"
                "- If you used specific document sources, list the filenames in the 'sources' field (extract from SOURCE: lines in context)\n"
                "- If you primarily used memory facts, describe which facts you used in the 'memory_facts' field\n"
                "- Set 'should_save' based on whether this interaction should be saved to memory using the guidelines above"
            )
            qa_tmpl = PromptTemplate(qa_tmpl_str)
            
            # Use structured prediction to get the response
            structured_response = self.llm.structured_predict(
                RAGResponse,
                qa_tmpl,
                query_str=query_text,
                multimodal_context=retrieved_context,
                chat_context=chat_context,
                memory_facts_context=memory_facts_context
            )
            
            # Store the interaction in memory if user is provided and should_save is True
            if user and user.get('id') and structured_response.should_save:
                try:
                    memory_service = FCSMemoryService()
                    
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
                    if structured_response.sources:
                        source_list_str = ", ".join(structured_response.sources)
                        memory_sources_description = f"ai assistant with sources: {source_list_str}"
                    elif structured_response.memory_facts:
                        memory_sources_description = "ai assistant with memory facts"
                    
                    ai_message = Message(
                        content=structured_response.answer,
                        role_type="assistant",
                        source_description=memory_sources_description,
                        name=f"ai-response-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    )
                    await memory_service.add_message(user['id'], ai_message)
                    logger.info(f"Successfully stored chat in memory for user_id: {user['id']}")
                except Exception as e:
                    logger.error(f"Error storing chat in memory for user_id {user.get('id')}: {str(e)}")
            else:
                if user and user.get('id'):
                    logger.info(f"Skipping memory storage for query type that should not be saved: '{query_text[:30]}...'")
                else:
                    logger.warning("No user_id provided in user object, or user object not provided, skipping memory storage for RAG query")
            
            # Return the response
            return ExtendedGraphRAGResponse(
                answer=structured_response.answer,
                images=None,
                sources=structured_response.sources,
                memory_facts=structured_response.memory_facts
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