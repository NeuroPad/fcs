from pathlib import Path
from typing import List, Dict, Any
import logging
from llama_index.core import SimpleDirectoryReader, StorageContext, Document, PromptTemplate
from llama_index.core.indices import MultiModalVectorStoreIndex
from llama_index.core.indices.property_graph import VectorContextRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.schema import ImageNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from core.config import settings
from schemas.graph_rag import ExtendedGraphRAGResponse
from services.store import GraphRAGStore

logger = logging.getLogger(__name__)

class MultiModalRAGService:
    def __init__(self, chroma_db_path: str = "./chroma_db"):
        self.chroma_client = chromadb.PersistentClient(path=chroma_db_path)
        
         # Initialize models
        # Initialize models
        hf_model_name = "BAAI/bge-small-en-v1.5"
        hf_model_path = settings.MODELS_DIR / "bge-small-en-v1.5"
        
        # if hf_model_path.exists():
        #     self.embed_model = HuggingFaceEmbedding(
        #         model_name=str(hf_model_path),
        #         cache_folder=str(settings.MODELS_DIR)
        #     )
        # else:
        #     # Fallback to downloading if not found locally
        #     self.embed_model = HuggingFaceEmbedding(
        #         model_name=hf_model_name,
        #         cache_folder=str(settings.MODELS_DIR)
        #     )
        #self.llm = Ollama(model="command-r7b", request_timeout=1200)
        
         # Initialize Open Ai models
        self.embed_model = OpenAIEmbedding(model_name="text-embedding-ada-002")
        self.llm = OpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-4o-mini")
        
        # Create text collection
        self.text_collection = self.chroma_client.get_or_create_collection(
            name="text_collection",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Create image collection
        self.image_collection = self.chroma_client.get_or_create_collection(
            name="image_collection",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Create separate vector stores for text and images
        self.text_store = ChromaVectorStore(chroma_collection=self.text_collection)
        self.image_store = ChromaVectorStore(chroma_collection=self.image_collection)
        
        # Create storage context with both stores
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.text_store,
            image_store=self.image_store
        )

        self.graph_store = GraphRAGStore()
        self.index = None

    async def process_documents(self, markdown_dir: Path) -> Dict[str, Any]:
        try:
            # Load markdown documents from root directory
            reader = SimpleDirectoryReader(
                input_dir=str(markdown_dir),
                required_exts=[".md", ".json", ".txt", ".docx", ".doc"],
                recursive=False  # Only get markdown files from root
            )
            llama_documents = reader.load_data()
            
            # Load image documents from artifact directories
            image_documents = []
            for subdir in markdown_dir.glob("*_artifacts"):
                if subdir.is_dir():
                    image_reader = SimpleDirectoryReader(
                        input_dir=str(subdir),
                        required_exts=[".jpg", ".png", ".jpeg"],
                        recursive=True
                    )
                    try:
                        image_docs = image_reader.load_data()
                        image_documents.extend(image_docs)
                    except Exception as e:
                        logger.warning(f"Error loading images from {subdir}: {str(e)}")

            # Create and store the index with both document types
            self.index = MultiModalVectorStoreIndex.from_documents(
                documents=llama_documents + image_documents,
                storage_context=self.storage_context,
                embed_model=self.embed_model
            )

            return {
                "status": "success",
                "message": f"Processed {len(llama_documents)} text documents and {len(image_documents)} image documents",
                "document_count": len(llama_documents) + len(image_documents)
            }
        except Exception as e:
            logger.error(f"Error processing documents: {str(e)}")
            raise

    async def query_index(self, query_text: str, top_k: int = 3) -> Dict[str, Any]:
        try:
            if not self.index:
                # Create a new index from the vector stores
                self.index = MultiModalVectorStoreIndex(
                    nodes=[],  # Empty nodes list as we're using existing stores
                    storage_context=self.storage_context,
                    embed_model=self.embed_model
                )

            # Initialize retriever with parameters for both text and images
            retriever = self.index.as_retriever(
                similarity_top_k=top_k,
                image_similarity_top_k=top_k
            )
            
            # Perform the query
            results = retriever.retrieve(query_text)
            
            # Process results
            processed_results = []
            for result in results:
                node_info = {
                    "content": result.node.get_content(),
                    "score": result.score,
                    "type": "image" if isinstance(result.node, ImageNode) else "text"
                }
                if hasattr(result.node, "metadata"):
                    node_info["metadata"] = result.node.metadata
                processed_results.append(node_info)
            
            return {
                "status": "success",
                "results": processed_results
            }
        except Exception as e:
            logger.error(f"Error querying index: {str(e)}")
            raise

    async def enhanced_query(self, query_text: str, top_k: int = 3) -> ExtendedGraphRAGResponse:
        try:
            # Ensure the index is initialized.
            if not self.index:
                self.index = MultiModalVectorStoreIndex(
                    nodes=[],
                    storage_context=self.storage_context,
                    embed_model=self.embed_model
                )


            # Retrieve multimodal results.
            multimodal_retriever = self.index.as_retriever(
                similarity_top_k=top_k,
                image_similarity_top_k=top_k
            )

            # Retrieve graph results.
            vector_retriever = VectorContextRetriever(
                graph_store=self.graph_store,
                embed_model=self.embed_model,
                similarity_top_k=top_k,
                path_depth=3,
                include_text=True,
            )

            # Get both types of results.
            graph_results = vector_retriever.retrieve(query_text)
            multimodal_results = multimodal_retriever.retrieve(query_text)

            # Prepare the contexts from the retrieved results.
            graph_context = "\n".join([node.node.get_content() for node in graph_results])
            multimodal_context = "\n".join([result.node.get_content() for result in multimodal_results])

            # Define the prompt template.
            qa_tmpl = PromptTemplate(
                "You have two types of context information below.\n"
                "---------------------\n"
                "GRAPH CONTEXT (showing relationships and connections):\n"
                "{graph_context}\n"
                "---------------------\n"
                "MULTIMODAL CONTEXT (including text and images):\n"
                "{multimodal_context}\n"
                "---------------------\n"
                "Using only this context and no prior knowledge, provide a comprehensive response that:\n"
                "1. Directly addresses all aspects of the query\n"
                "2. Explains key concepts clearly\n"
                "3. Uses lists/numbered steps for multi-part information where necessary\n"
                "4. Provides relevant examples where appropriate\n"
                "5. Breaks down complex ideas into simpler components\n"
                "6. Maintains logical flow between ideas\n"
                "7. Highlights important relationships or patterns\n"
                "8. States assumptions when necessary\n"
                "NOTE: answer the query using the context given dont mention the word CONTEXT in your answer\n" 
                "Query: {query_str}\n"
                "Answer: "
            )

           
            # Call the LLM directly with the formatted prompt.
            # If your LLM supports async, you might use:
            # response_text = await llm.apredict(formatted_prompt)
            response_text = self.llm.predict(
                prompt=qa_tmpl,
                query_str=query_text,
                graph_context=graph_context,
                multimodal_context=multimodal_context
            )

            # Extract images from the multimodal results.
            # Extract images with proper path formatting
            images = []
            for result in multimodal_results:
                if isinstance(result.node, ImageNode):
                    if "file_path" in result.node.metadata:
                        file_path = result.node.metadata["file_path"]
                        if not file_path.startswith("processed_files/"):
                            file_path = f"processed_files/{file_path.split('/')[-2]}/{file_path.split('/')[-1]}"
                        images.append(file_path)

            # Extract sources with proper path formatting
            sources = set()  # Use set to avoid duplicates
            for node in graph_results:
                if hasattr(node.node, "metadata") and "file_path" in node.node.metadata:
                    file_path = node.node.metadata["file_path"]
                    if file_path.endswith(".md"):  # Only include markdown files
                        if not file_path.startswith("processed_files/"):
                            file_path = f"processed_files/{file_path.split('/')[-1]}"
                        sources.add(file_path)

            # Return ExtendedGraphRAGResponse
            return ExtendedGraphRAGResponse(
                answer=response_text,
                images=list(dict.fromkeys(images)),  # Remove any duplicate images while preserving order
                sources=list(sources)  # Convert set to list
            )

        except Exception as e:
            logger.error(f"Error in enhanced query: {str(e)}")
            raise

    async def normal_query(self, query_text: str, top_k: int = 9) -> ExtendedGraphRAGResponse:
        try:
            if not self.index:
                self.index = MultiModalVectorStoreIndex(
                    nodes=[],
                    storage_context=self.storage_context,
                    embed_model=self.embed_model
                )

            # Retrieve multimodal results
            multimodal_retriever = self.index.as_retriever(
                similarity_top_k=top_k,
                image_similarity_top_k=top_k
            )
            
            # Get results
            multimodal_results = multimodal_retriever.retrieve(query_text)
            
            # Prepare the context from the retrieved results
            multimodal_context = "\n".join([result.node.get_content() for result in multimodal_results])

            # Define the prompt template
            qa_tmpl = PromptTemplate(
                "Based strictly on the following context information:\n"
                "---------------------\n"
                "{multimodal_context}\n"
                "---------------------\n"
                "Using only this context and no prior knowledge, provide a comprehensive response that:\n"
                "1. Directly addresses all aspects of the query\n"
                "2. Explains key concepts clearly\n"
                "3. Uses lists/numbered steps for multi-part information where necessary\n"
                "4. Provides relevant examples where appropriate\n"
                "5. Breaks down complex ideas into simpler components\n"
                "6. Maintains logical flow between ideas\n"
                "7. Highlights important relationships or patterns\n"
                "8. States assumptions when necessary\n"
                "NOTE: answer the query using the context given dont mention the word CONTEXT in your answer\n" 
                "\n"
                "Query: {query_str}\n"
                "Answer: "
            )

            # Call the LLM with the formatted prompt
            response_text = self.llm.predict(
                prompt=qa_tmpl,
                query_str=query_text,
                multimodal_context=multimodal_context
            )

            # Extract images with proper path formatting
            images = []
            for result in multimodal_results:
                if isinstance(result.node, ImageNode):
                    if "file_path" in result.node.metadata:
                        file_path = result.node.metadata["file_path"]
                        if not file_path.startswith("processed_files/"):
                            file_path = f"processed_files/{file_path.split('/')[-2]}/{file_path.split('/')[-1]}"
                        images.append(file_path)

            # Extract sources with proper path formatting
            sources = set()  # Use set to avoid duplicates
            for result in multimodal_results:
                if hasattr(result.node, "metadata") and "file_path" in result.node.metadata:
                    file_path = result.node.metadata["file_path"]
                    if file_path.endswith(".md"):  # Only include markdown files
                        if not file_path.startswith("processed_files/"):
                            file_path = f"processed_files/{file_path.split('/')[-1]}"
                        sources.add(file_path)

            return ExtendedGraphRAGResponse(
                answer=response_text,
                images=list(dict.fromkeys(images)),  # Remove any duplicate images while preserving order
                sources=list(sources)  # Convert set to list
            )

        except Exception as e:
            logger.error(f"Error in normal query: {str(e)}")
            raise

