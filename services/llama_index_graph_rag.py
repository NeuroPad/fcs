import asyncio
from datetime import datetime

from llama_index.core import Document, PropertyGraphIndex, PromptTemplate
from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama
from llama_index.core.node_parser import SentenceSplitter
from typing import List
import networkx as nx
from pyvis.network import Network
import networkx as nx
from core.config import settings
from schemas.graph_rag import ExtendedGraphRAGResponse
from services.extractor import GraphRAGExtractor
from services.store import GraphRAGStore
from services.engine import GraphRAGQueryEngine
from llama_index.graph_stores.neo4j import Neo4jGraphStore, Neo4jPropertyGraphStore
from llama_index.core.indices import MultiModalVectorStoreIndex

from neo4j import GraphDatabase

from llama_index.core.indices.property_graph import VectorContextRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core import SimpleDirectoryReader
from typing import Dict

import re
from typing import Any

import logging

logger = logging.getLogger(__name__)

KG_TRIPLET_EXTRACT_TMPL = """
-Goal-
Analyze any document containing text and images to extract:
1. Core conceptual entities
2. Visual elements (images/diagrams)
3. Relationships between all elements

-Universal Image Handling-
1. Image Extraction:
   - Extract full filename from any ![](path) syntax
   - Classify images as:
     * "Illustration" (general images)
     * "Diagram" (flowcharts/schematics)
     * "Photo" (real-world images)
     * "Interface" (UI/screenshots)
     * "Warning" (danger/safety symbols)

2. Contextual Linking:
   - Connect images to nearest section header
   - Relate images to adjacent text elements (within 3 lines)
   - Preserve document hierarchy through relationships

-Steps-
1. Extract Entities:
   A. Text Concepts:
      - entity_name: Capitalized key term
      - entity_type: ["Concept", "Process", "Component", "Warning", "Instruction"]
      - entity_description: Concise summary from context

   B. Images:
      - entity_name: Full image filename
      - entity_type: Image classification from above
      - entity_description: "Visual element associated with [nearest heading/list item]"

   Format: ("entity"$$$$"<name>"$$$$"<type>"$$$$"<description>")

2. Extract Relationships:
   A. Between Concepts:
      - "requires", "part_of", "related_to", "precedes"

   B. Concept-Image Links:
      - "illustrates", "supports", "depicts", "shows_step", "documents"

   Format: ("relationship"$$$$"<source>"$$$$"<target>"$$$$"<relation>"$$$$"<context>")

-Examples-
Medical Document:
Text: "Administer vaccine ![Injection Diagram](inject.png) using proper technique"
Output:
("entity"$$$$"Vaccine Administration"$$$$"Process"$$$$"Medical injection procedure")
("entity"$$$$"inject.png"$$$$"Diagram"$$$$"Visual guide for injection technique")
("relationship"$$$$"inject.png"$$$$"Vaccine Administration"$$$$"illustrates"$$$$"Diagram shows proper injection method")

Toy Assembly:
Text: "Attach wheels ![Step 4](step4.jpg) to axle using provided bolts"
Output:
("entity"$$$$"Wheel Assembly"$$$$"Instruction"$$$$"Attaching wheels to axle")
("entity"$$$$"step4.jpg"$$$$"Illustration"$$$$"Visual reference for assembly step 4")
("relationship"$$$$"step4.jpg"$$$$"Wheel Assembly"$$$$"shows_step"$$$$"Image demonstrates wheel attachment process")

-Real Input-
######################
text: {text}
######################
output:"""


class GraphRAGService:
    def __init__(self):
        self.processing_status = {
            "status": "idle",
            "message": "",
            "progress": 0,
            "total_documents": 0,
            "processed_documents": 0
        }
        
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
        
        # Initialize graph stores
        self.graph_store = GraphRAGStore()  # Remove the parameters
        
        space_name = "llamaindex"
        edge_types, rel_prop_names = ["relationship"], ["relationship"]
        tags = ["entity"]
        
        self.neo_store = Neo4jPropertyGraphStore(
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
            url=settings.NEO4J_URI,
        )

        # Add direct Neo4j driver
        self.neo4j_driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )


        self.splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=20)

        # Define patterns
        self.entity_pattern = (
            r'\("entity"\$\$\$\$"(.+?)"\$\$\$\$"(.+?)"\$\$\$\$"(.+?)"\)'
        )
        # Update the relationship pattern to match the format in KG_TRIPLET_EXTRACT_TMPL
        self.relationship_pattern = (
            r'\("relationship"\$\$\$\$"(.+?)"\$\$\$\$"(.+?)"\$\$\$\$"(.+?)"\$\$\$\$"(.+?)"\)'
        )

        # Create extractor with proper prompt and parse function
        self.extractor = GraphRAGExtractor(
            llm=self.llm,
            extract_prompt=KG_TRIPLET_EXTRACT_TMPL,
            parse_fn=self._parse_response,
            max_paths_per_chunk=2,
        )
        self.index = None
        self.query_engine = None

    def _parse_response(self, response_str: str) -> Any:
        entities = re.findall(self.entity_pattern, response_str)
        relationships = re.findall(self.relationship_pattern, response_str)
        return entities, relationships

    async def process_document(self, content: str) -> None:
        doc = Document(text=content)
        nodes = self.splitter.get_nodes_from_documents([doc])

        self.index = PropertyGraphIndex(
            nodes=nodes,
            kg_extractors=[self.extractor],
            property_graph_store=self.graph_store,
        )
        
        # self.index.property_graph_store.save_networkx_graph(
        #     name="./SimpleGraph.html"
        # )

        self.graph_store.build_communities()
        self.query_engine = GraphRAGQueryEngine(
            graph_store=self.graph_store,
            llm=self.llm,
            index=self.index,
            similarity_top_k=10,
        )

    async def get_answer(self, question: str) -> ExtendedGraphRAGResponse:

        # Initialize VectorContextRetriever
        vector_retriever = VectorContextRetriever(
            graph_store=self.neo_store,
            embed_model=self.embed_model,
            similarity_top_k=12,
            path_depth=3,
            include_text=True,
        )

        # Append additional instructions to the query
        qa_tmpl_str = (
            "Context information is below.\n"
            "---------------------\n"
            "{context_str}\n"
            "---------------------\n"
            "Given the context information and not prior knowledge, "
            "answer the query don't mention the word CONTEXT in your answer. If there are images in the context_str that are relevant to your answer, "
            "you MUST list them after your response in this exact format:\n\n"
            "image(s): processed_files/[document_name]_artifacts/[image_filename]\n\n"
            "Example:\n"
            "image(s): processed_files/Adebisi_Joseph_CV-with-refs_artifacts/image_000001_cb38f16cd497655883fbf4717e084dc6d4206c0258e92b225301d8b3cf8bb6a4.png\n"
            "IMPORTANT: Do not repeat an image. You MUST include images where they are available. If no images are found, explicitly state 'No relevant images found.'\n\n"
            "Query: {query_str}\n"
            "Answer: "
        )

        qa_tmpl = PromptTemplate(qa_tmpl_str)

        # Create Query Engine
        query_engine = RetrieverQueryEngine.from_args(vector_retriever, text_qa_template=qa_tmpl, llm=self.llm)

        # Perform a query with the modified question
        response = query_engine.query(question)

        # Extract the response text
        full_response = response.response

        # Get formatted sources by calling the method
        formatted_sources = response.get_formatted_sources()

        # Extract sources from source_nodes
        def extract_sources_from_nodes(source_nodes) -> List[str]:
            sources = set()  # Use a set to automatically handle duplicates
            for node in source_nodes:
                file_path = node.node.metadata.get("file_path", "")
                if file_path:
                    # Extract the file name and extension from the file_path
                    file_name = file_path.split("/")[-1]  # Get the last part of the path
                    sources.add(f"processed_files/{file_name}")  # Add to the set
            return list(sources)

        # Helper functions to extract information
        def extract_images(text: str) -> List[str]:
            image_pattern = r'processed_files/[^,\s]+\.png'
            matches = re.findall(image_pattern, text)
            return list(dict.fromkeys(matches))  # Remove duplicates while preserving order

        def clean_answer(text: str) -> str:
            # Remove the image and source lines from the answer
            answer_lines = []
            for line in text.split('\n'):
                if not any(marker in line.lower() for marker in ['image(s):', 'source(s):']):
                    answer_lines.append(line)
            return '\n'.join(answer_lines).strip()

        # Extract components
        images = extract_images(full_response)
        sources = extract_sources_from_nodes(response.source_nodes)  # Extract sources from source_nodes
        clean_response = clean_answer(full_response)
        logger.debug(f"Processed result: {response}")

        # Create and return ExtendedGraphRAGResponse
        result = ExtendedGraphRAGResponse(
            answer=clean_response,
            images=images,
            sources=sources
        )

        # Log the result
        print("Formatted Sources:", formatted_sources)
        print("Sources from Nodes:", sources)
        print("Result:", result)
        logger.info("Response processed successfully")
        logger.debug(f"Processed result: {result}")

        return result

    def extract_images_from_context(self, context_str: str) -> List[str]:
        image_pattern = r'processed_files/[^,\s]+\.png'
        matches = re.findall(image_pattern, context_str)
        return list(dict.fromkeys(matches))  # Remove duplicates while preserving order

    def extract_sources_from_context(self, context_str: str) -> List[str]:
        source_pattern = r'processed_files/[^,\s]+\.md'
        matches = re.findall(source_pattern, context_str)
        return list(dict.fromkeys(matches))  # Remove duplicates while preserving order


    async def get_processing_status(self) -> Dict:
        """Get the current processing status"""
        return self.processing_status

    async def process_documents(self) -> Dict:
        """Process all Markdown documents in the markdown directory"""
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

            # Initialize SimpleDirectoryReader
            reader = SimpleDirectoryReader(
                input_dir=str(settings.PROCESSED_FILES_DIR), required_exts=[".md", ".json", ".txt", ".docx", ".doc"]
            )

            documents = reader.load_data()
            total_documents = len(documents)
            
            self.processing_status.update({
                "message": f"Found {total_documents} documents to process",
                "total_documents": total_documents,
                "progress": 20
            })

            try:
                nodes = []
                for idx, doc in enumerate(documents, 1):
                    try:
                        doc_nodes = self.splitter.get_nodes_from_documents([doc])
                        nodes.extend(doc_nodes)
                        self.processing_status.update({
                            "message": f"Processing document {idx} of {total_documents}",
                            "processed_documents": idx,
                            "progress": 20 + (60 * idx // total_documents)
                        })
                        await asyncio.sleep(0.1)  # Prevent blocking
                    except Exception as e:
                        logger.error(f"Error processing document {idx}: {str(e)}")
                        continue

                self.processing_status.update({
                    "message": "Building knowledge graph index",
                    "progress": 80
                })

                # Add error handling for PropertyGraphIndex creation
                try:
                    self.index = PropertyGraphIndex(
                        nodes=nodes,
                        kg_extractors=[self.extractor],
                        property_graph_store=self.graph_store,
                        max_triplets_per_chunk=5,
                        include_embeddings=False,
                        max_object_length=100,
                        embed_model=self.embed_model,
                        use_async=True
                    )
                    self.index.storage_context.persist(persist_dir="./storage")
                except Exception as e:
                    logger.error(f"Error creating PropertyGraphIndex: {str(e)}")
                    raise

                self.processing_status.update({
                    "message": "Building communities",
                    "progress": 90
                })
                
                self.graph_store.build_communities()

                self.processing_status.update({
                    "status": "completed",
                    "message": "Processing completed successfully",
                    "progress": 100,
                    "processed_documents": total_documents
                })

                return {
                    "status": "success",
                    "processed_documents": total_documents,
                    "total_nodes": len(nodes),
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

    async def get_similar_nodes(self, question: str) -> List[str]:
        if not self.index:
            raise ValueError("No document processed yet")
        nodes = self.index.as_retriever(similarity_top_k=5).retrieve(question)
        return [node.text for node in nodes]

    async def get_graph_stats(self) -> Dict:
        """Get statistics about the knowledge graph"""
        try:
            with self.neo4j_driver.session() as session:
                # Get all stats in one query
                result = session.run("""
                    MATCH (n) 
                    OPTIONAL MATCH ()-[r]->()
                    OPTIONAL MATCH (d:Documents)
                    RETURN 
                        count(DISTINCT n) as total_nodes,
                        count(DISTINCT r) as total_relationships,
                        count(DISTINCT d) as total_documents
                """)

                stats = result.single()
                total_nodes = stats["total_nodes"]
                total_relationships = stats["total_relationships"]
                total_documents = stats["total_documents"]

                # Calculate average relations
                avg_relations = total_relationships / total_nodes if total_nodes > 0 else 0

                return {
                    "totalNodes": total_nodes,
                    "totalRelationships": total_relationships,
                    "totalDocuments": total_documents,
                    "averageRelationsPerNode": round(avg_relations, 2),
                    "lastIndexed": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error getting graph stats: {str(e)}")
            raise

    async def get_relationships(self) -> List[Dict]:
        """Get relationships from the knowledge graph"""
        try:
            with self.neo4j_driver.session() as session:
                result = session.run("""
                    MATCH (source)-[r]->(target)
                    RETURN 
                        id(r) as id,
                        type(r) as relationship_type,
                        source.name as source_node,
                        target.name as target_node,
                        r.confidence as confidence,
                        r.timestamp as timestamp
                    ORDER BY id
                    LIMIT 1000
                """)

                relationships = []
                for record in result:
                    relationships.append({
                        "id": str(record["id"]),
                        "sourceNode": record["source_node"],
                        "relationship": record["relationship_type"],
                        "targetNode": record["target_node"],
                        "confidence": float(record["confidence"] if record["confidence"] else 0.7),
                        "lastUpdated": str(record["timestamp"]).split('T')[0] if record["timestamp"] else ""
                    })

                return relationships

        except Exception as e:
            logger.error(f"Error getting relationships: {str(e)}")
            raise

    def __del__(self):
        if hasattr(self, 'neo4j_driver'):
            self.neo4j_driver.close()