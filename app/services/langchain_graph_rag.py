from langchain.text_splitter import TokenTextSplitter
from langchain_openai import ChatOpenAI
from langchain_experimental.graph_transformers import LLMGraphTransformer

# from langchain_community.graphs import Neo4jGraph
# from langchain_community.vectorstores import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.chains import LLMChain
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph, Neo4jVector

import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class LangchainGraphRAGService:
    def __init__(self, settings):
        self.settings = settings
        self.llm = ChatOpenAI(
            temperature=0,
            model_name="gpt-3.5-turbo-0125",
            openai_api_key=settings.OPENAI_API_KEY,
        )
        self.graph = Neo4jGraph(
            url=settings.NEO4J_URI,
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
        )
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        self.text_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=24)
        self.llm_transformer = LLMGraphTransformer(llm=self.llm)

    async def process_documents(self, markdown_dir: str) -> Dict[str, Any]:
        """Process all markdown documents in the specified directory"""
        try:
            documents = []
            md_path = Path(markdown_dir)

            # Read all markdown files
            for file_path in md_path.glob("*.md"):
                with open(file_path, "r", encoding="utf-8") as file:
                    text = file.read()
                    doc = Document(
                        page_content=text, metadata={"source": file_path.name}
                    )
                    documents.append(doc)

            if not documents:
                return {"status": "error", "message": "No documents found"}

            # Split documents into chunks
            splits = self.text_splitter.split_documents(documents)

            # Convert to graph documents
            graph_documents = self.llm_transformer.convert_to_graph_documents(splits)

            # Add to Neo4j graph
            self.graph.add_graph_documents(
                graph_documents, baseEntityLabel=True, include_source=True
            )

            # Create vector index
            vector_index = Neo4jVector.from_existing_graph(
                self.embeddings,
                url=self.settings.NEO4J_URI,
                username=self.settings.NEO4J_USERNAME,
                password=self.settings.NEO4J_PASSWORD,
                search_type="hybrid",
                node_label="Document",
                text_node_properties=["text"],
                embedding_node_property="embedding",
            )

            return {
                "status": "success",
                "processed_documents": len(documents),
                "total_chunks": len(splits),
            }

        except Exception as e:
            logger.error(f"Error processing documents: {str(e)}")
            raise

    def _create_cypher_generation_prompt(self) -> PromptTemplate:
        """Create the prompt template for Cypher query generation"""
        template = """Task: Generate Cypher statement to query a graph database.
        Instructions:
        Use only the provided relationship types and properties in the schema.
        Do not use any other relationship types or properties that are not provided.
        Schema:
        {schema}

        Note: Do not include any explanations or apologies in your responses.
        Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
        Do not include any text except the generated Cypher statement.

        The question is:
        {question}"""

        return PromptTemplate(input_variables=["schema", "question"], template=template)

    async def query_knowledge_graph(self, question: str, top_k: int = 10) -> str:
        """Query the knowledge graph using GraphCypherQAChain"""
        try:
            # Create the chain with custom configuration
            chain = GraphCypherQAChain.from_llm(
                cypher_llm=self.llm,
                qa_llm=self.llm,
                graph=self.graph,
                verbose=True,
                top_k=top_k,
                cypher_prompt=self._create_cypher_generation_prompt(),
                validate_cypher=True,
                use_function_response=True,
                allow_dangerous_requests=True,
            )

            # Execute the query
            result = chain.invoke({"query": question})

            return result["result"]

        except Exception as e:
            logger.error(f"Error querying knowledge graph: {str(e)}")
            raise

    async def get_similar_documents(
        self, query: str, k: int = 5
    ) -> List[Dict[str, Any]]:
        """Get similar documents from the vector store"""
        try:
            vector_store = Neo4jVector(
                embedding=self.embeddings,
                url=self.settings.NEO4J_URI,
                username=self.settings.NEO4J_USERNAME,
                password=self.settings.NEO4J_PASSWORD,
            )

            results = vector_store.similarity_search_with_score(query, k=k)

            return [
                {"content": doc.page_content, "metadata": doc.metadata, "score": score}
                for doc, score in results
            ]

        except Exception as e:
            logger.error(f"Error retrieving similar documents: {str(e)}")
            raise
