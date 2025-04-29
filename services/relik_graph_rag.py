from datetime import datetime
import logging
from typing import Dict, List, Any
import asyncio
from pathlib import Path
import signal
from contextlib import contextmanager

from llama_index.core import Document, PropertyGraphIndex
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from extractor import RelikPathExtractor
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import SimpleDirectoryReader
from neo4j import GraphDatabase

from core.config import settings
import spacy
from fastcoref import spacy_component

logger = logging.getLogger(__name__)

class RelikGraphRAGService:
    def __init__(self):
        self.processing_status = {
            "status": "idle",
            "message": "",
            "progress": 0,
            "total_documents": 0,
            "processed_documents": 0
        }
        
        # Initialize spaCy with fastcoref
        self.nlp = spacy.load('en_core_web_lg')
        self.nlp.add_pipe('fastcoref')
        
        # Initialize core components
        # Initialize Local models
        #self.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        #self.llm = Ollama(model="phi4", request_timeout=1200)
        
        # Initialize Open Ai models
        self.embed_model = OpenAIEmbedding(model_name="text-embedding-3-small")
        self.llm = OpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-4o-mini")
        self.splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
        
        # Initialize Neo4j components
        self.neo4j_store = Neo4jPropertyGraphStore(
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
            url=settings.NEO4J_URI,
        )
        
        self.neo4j_driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )
        
        # Initialize Relik extractor
        self.relik = RelikPathExtractor(
            model="relik-ie/relik-relation-extraction-small",
            model_config={"skip_metadata": True, "device": "mps"}
        )
        
        self.index = None

    def coref_resolution(self, text: str) -> str:
        """Apply coreference resolution to the text"""
        try:
            # Split text into manageable chunks (around 1000 characters)
            chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
            resolved_chunks = []
            
            for chunk in chunks:
                try:
                    # Process each chunk with spaCy
                    doc = self.nlp(chunk, component_cfg={
                        "fastcoref": {
                            'resolve_text': True,
                            'chunk_size': 1000,
                            'threshold': 0.4  # Adjust threshold for statistical text
                        }
                    })
                    resolved_chunks.append(doc._.resolved_text if doc._.resolved_text else chunk)
                except Exception as e:
                    logger.warning(f"Chunk processing failed, using original: {str(e)}")
                    resolved_chunks.append(chunk)
            
            return " ".join(resolved_chunks)
        except Exception as e:
            logger.error(f"Coreference resolution failed: {str(e)}")
            return text

    async def process_document(self, content: str) -> Dict:
        """Process a single document and create knowledge graph"""
        try:
            # Validate input
            if not content or not isinstance(content, str):
                return {
                    "status": "error",
                    "message": "Invalid content provided. Must be a non-empty string."
                }
            
            try:
                # Sanitize content to handle control characters and special characters
                sanitized_content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\r\t')
                
                # Apply coreference resolution
                resolved_text = self.coref_resolution(sanitized_content)
                
                # Create document and split into nodes
                doc = Document(text=resolved_text)
                nodes = self.splitter.get_nodes_from_documents([doc])
                
                # Create property graph index
                self.index = PropertyGraphIndex(
                    nodes=nodes,
                    kg_extractors=[self.relik],
                    # llm=self.llm,
                    embed_model=self.embed_model,
                    property_graph_store=self.neo4j_store,
                    show_progress=True,
                )
                
                return {
                    "status": "success",
                    "message": "Document processed successfully",
                    "nodes_created": len(nodes)
                }
            except Exception as inner_e:
                logger.error(f"Error in document processing: {str(inner_e)}")
                return {
                    "status": "error",
                    "message": f"Error in document processing: {str(inner_e)}"
                }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    def flatten_json(self, json_text: str) -> str:
        """Convert JSON content to flat text"""
        try:
            import json
            
            # Parse JSON string to dict
            data = json.loads(json_text)
            print("Original JSON data:", data)  # Debug print
            
            # Function to recursively extract text and format it
            def extract_text(obj, parent_key="") -> str:
                if isinstance(obj, str):
                    return f"{parent_key} {obj}. " if parent_key else f"{obj}. "
                elif isinstance(obj, (int, float)):
                    return f"{parent_key} {str(obj)}. " if parent_key else f"{str(obj)}. "
                elif isinstance(obj, bool):
                    return f"{parent_key} {str(obj)}. " if parent_key else f"{str(obj)}. "
                elif isinstance(obj, dict):
                    text = []
                    for k, v in obj.items():
                        # Use the key as context for nested values
                        extracted = extract_text(v, k)
                        if extracted.strip():
                            text.append(extracted)
                    return " ".join(text)
                elif isinstance(obj, list):
                    text = []
                    for item in obj:
                        extracted = extract_text(item, parent_key)
                        if extracted.strip():
                            text.append(extracted)
                    return " ".join(text)
                return ""
            
            processed_text = extract_text(data).strip()
            print("Processed text:", processed_text)  # Debug print
            
            if not processed_text:
                # Fallback: if no text was extracted, convert the entire JSON to string
                processed_text = f"JSON content: {json.dumps(data, ensure_ascii=False)}"
            
            return processed_text
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return f"Invalid JSON content: {json_text[:100]}..."  # Return first 100 chars for debugging
        except Exception as e:
            logger.error(f"Error flattening JSON: {str(e)}")
            return f"Error processing JSON: {str(e)}"

    async def process_documents(self) -> Dict:
        """Process all documents from the processed files directory"""
        try:
            self.processing_status.update({
                "status": "processing",
                "message": "Initializing document processing",
                "progress": 0,
                "processed_documents": 0,
                "total_documents": 0
            })
    
            # First, delete all existing nodes and relationships
            with self.neo4j_driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("Cleared existing graph data")
                self.processing_status.update({
                    "message": "Cleared existing graph data",
                    "progress": 10
                })
    
            # Initialize SimpleDirectoryReader with metadata
            reader = SimpleDirectoryReader(
                input_dir=str(settings.PROCESSED_FILES_DIR),
                required_exts=[".md", ".json", ".txt", ".docx", ".doc"],
                file_metadata=lambda path: {"source": path, "file_type": Path(path).suffix}
            )

            documents = reader.load_data()
            total_documents = len(documents)
            
            print("Total documents:", total_documents)
            
            #print("Documents:", documents)
            
            self.processing_status.update({
                "message": f"Found {total_documents} documents to process",
                "total_documents": total_documents,
                "progress": 20
            })
    
            try:
                all_nodes = []
                for idx, doc in enumerate(documents, 1):
                    try:
                        logger.info(f"Processing document {idx}/{total_documents}")
                        
                        # Get the file type from metadata
                        file_type = doc.metadata.get('file_type', '').lower()
                        
                        # Process document based on file type
                        try:
                            if file_type == '.json':
                                # Flatten JSON before processing
                                flattened_text = self.flatten_json(doc.text)
                                print(f"Flattened text: {flattened_text}")
                                
                                # Clean the flattened text
                                cleaned_text = ' '.join(
                                    sent.strip()
                                    for sent in flattened_text.split('.')
                                    if sent.strip() and len(sent.split()) > 3  # Only keep meaningful sentences
                                )
                                
                                if not cleaned_text:
                                    logger.warning(f"Empty text after cleaning for document {idx}")
                                    continue
                                
                                resolved_text = self.coref_resolution(cleaned_text)
                                print(f"Resolved text: {resolved_text}")
                            else:
                                # For other file types, apply minimal sanitization
                                resolved_text = self.coref_resolution(doc.text)
                            
                            if not resolved_text:
                                logger.warning(f"Empty text after processing document {idx}")
                                continue
                            
                            print(f"Processing file type: {file_type}")
                            print("Resolved text length:", len(resolved_text))
                            
                            # Create document and split into nodes
                            processed_doc = Document(text=resolved_text)
                            nodes = self.splitter.get_nodes_from_documents([processed_doc])
                            
                            if nodes:
                                all_nodes.extend(nodes)
                                logger.info(f"Document {idx} processed with {len(nodes)} nodes")
                            else:
                                logger.warning(f"No nodes generated for document {idx}")
                            
                            self.processing_status.update({
                                "message": f"Completed document {idx} of {total_documents}",
                                "processed_documents": idx,
                                "progress": 20 + (60 * idx // total_documents)
                            })
                            
                        except Exception as e:
                            logger.error(f"Error processing document {idx}: {str(e)}")
                            continue
                        
                    except Exception as e:
                        logger.error(f"Error processing document {idx}: {str(e)}")
                        continue
    
                self.processing_status.update({
                    "message": "Building knowledge graph index",
                    "progress": 80
                })
    
                # Create property graph index with timeout handling
                try:
                    # Set a timeout for index creation
                    with self.timeout(6000):  # 10 minute timeout
                        self.index = PropertyGraphIndex(
                            nodes=all_nodes,
                            kg_extractors=[self.relik],
                            # llm=self.llm,
                            max_triplets_per_chunk=15,
                            max_object_length=100,
                            embed_model=self.embed_model,
                            property_graph_store=self.neo4j_store,
                            use_async=True,
                            show_progress=True,
                        )
                except TimeoutError:
                    logger.error("Index creation timed out after 10 minutes")
                    self.processing_status.update({
                        "status": "error",
                        "message": "Index creation timed out after 10 minutes",
                        "progress": 0
                    })
                    return {
                        "status": "error",
                        "message": "Index creation timed out"
                    }
    
                self.processing_status.update({
                    "status": "completed",
                    "message": "Processing completed successfully",
                    "progress": 100,
                    "processed_documents": total_documents
                })
    
                return {
                    "status": "success",
                    "processed_documents": total_documents,
                    "total_nodes": len(all_nodes),
                }
    
            except Exception as e:
                error_msg = f"Error in graph processing: {str(e)}"
                logger.error(error_msg)
                self.processing_status.update({
                    "status": "error",
                    "message": error_msg,
                    "progress": 0
                })
                raise
    
        except Exception as e:
            error_msg = f"Error processing documents: {str(e)}"
            logger.error(error_msg)
            self.processing_status.update({
                "status": "error",
                "message": error_msg,
                "progress": 0
            })
            raise

    # Add this context manager for timeout handling
    @contextmanager
    def timeout(self, seconds):
        def signal_handler(signum, frame):
            raise TimeoutError(f"Function timed out after {seconds} seconds")
        
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)

    async def get_processing_status(self) -> Dict:
        """Get the current processing status"""
        return self.processing_status

    def __del__(self):
        if hasattr(self, 'neo4j_driver'):
            self.neo4j_driver.close()