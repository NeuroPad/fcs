import re
import networkx as nx
from graspologic.partition import hierarchical_leiden
from collections import defaultdict

from llama_index.core.llms import ChatMessage
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.core.config import settings

import logging
from pathlib import Path
import sys

# Create logs directory
Path("logs").mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/error.log"), logging.StreamHandler(sys.stdout)],
)


class GraphRAGStore(Neo4jPropertyGraphStore):
    community_summary = {}
    entity_info = None
    max_cluster_size = 5
    
    def __init__(self):
        super().__init__(
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
            url=settings.NEO4J_URI,
        )
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
        self.embed_model = OpenAIEmbedding(model_name="text-embedding-3-small")
        self.llm = OpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-4o-mini")

    def generate_community_summary(self, text):
        """Generate summary for a given text using an LLM."""
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are provided with a set of relationships from a knowledge graph, each represented as "
                    "entity1->entity2->relation->relationship_description. Your task is to create a summary of these "
                    "relationships. The summary should include the names of the entities involved and a concise synthesis "
                    "of the relationship descriptions. The goal is to capture the most critical and relevant details that "
                    "highlight the nature and significance of each relationship. Ensure that the summary is coherent and "
                    "integrates the information in a way that emphasizes the key aspects of the relationships."
                ),
            ),
            ChatMessage(role="user", content=text),
        ]

        response =self.llm.chat(messages)

        clean_response = re.sub(r"^assistant:\s*", "", str(response)).strip()
        return clean_response

    def build_communities(self):
        """Builds communities from the graph and summarizes them."""
        nx_graph = self._create_nx_graph()
        community_hierarchical_clusters = hierarchical_leiden(
            nx_graph, max_cluster_size=self.max_cluster_size
        )
        self.entity_info, community_info = self._collect_community_info(
            nx_graph, community_hierarchical_clusters
        )
        self._summarize_communities(community_info)

    def _create_nx_graph(self):
        """Converts internal graph representation to NetworkX graph."""
        nx_graph = nx.Graph()
        triplets = self.get_triplets()
        logging.error(f"Triplets: {triplets}")
        for entity1, relation, entity2 in triplets:
            nx_graph.add_node(entity1.name)
            nx_graph.add_node(entity2.name)
            nx_graph.add_edge(
                relation.source_id,
                relation.target_id,
                relationship=relation.label,
                description=relation.properties["relationship_description"],
            )
        return nx_graph

    def _collect_community_info(self, nx_graph, clusters):
        """
        Collect information for each node based on their community,
        allowing entities to belong to multiple clusters.
        """
        entity_info = defaultdict(set)
        community_info = defaultdict(list)

        for item in clusters:
            node = item.node
            cluster_id = item.cluster

            # Update entity_info
            entity_info[node].add(cluster_id)

            for neighbor in nx_graph.neighbors(node):
                edge_data = nx_graph.get_edge_data(node, neighbor)
                if edge_data:
                    detail = f"{node} -> {neighbor} -> {edge_data['relationship']} -> {edge_data['description']}"
                    community_info[cluster_id].append(detail)

        # Convert sets to lists for easier serialization if needed
        entity_info = {k: list(v) for k, v in entity_info.items()}

        return dict(entity_info), dict(community_info)

    def _summarize_communities(self, community_info):
        """Generate and store summaries for each community."""
        for community_id, details in community_info.items():
            details_text = "\n".join(details) + "."  # Ensure it ends with a period
            self.community_summary[community_id] = self.generate_community_summary(
                details_text
            )

    def get_community_summaries(self):
        """Returns the community summaries, building them if not already done."""
        if not self.community_summary:
            self.build_communities()
        return self.community_summary
