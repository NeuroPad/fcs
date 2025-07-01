"""
Enhanced Graphiti Search Service with Node Tracking

This service extends the graphiti search functionality to track nodes used during reasoning
and return them with salience and confidence information for chat responses.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from graphiti_core.graphiti_types import GraphitiClients
from graphiti_core.search.search_config import SearchConfig, SearchResults
from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
from graphiti_core.search.search_filters import SearchFilters
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge

from graphiti_extend.search.handler import enhanced_contradiction_search
from app.schemas.chat import ReasoningNode
from app.schemas.graph_rag import ExtendedGraphRAGResponse

logger = logging.getLogger(__name__)


class GraphitiEnhancedSearchService:
    """Enhanced search service that tracks nodes used during reasoning."""
    
    def __init__(self, graphiti_clients: GraphitiClients):
        self.clients = graphiti_clients
        
    async def search_with_node_tracking(
        self,
        query: str,
        group_ids: List[str] | None = None,
        config: SearchConfig = COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
        search_filter: SearchFilters | None = None,
        include_contradictions: bool = True,
        max_nodes: int = 10,
    ) -> Dict[str, Any]:
        """
        Perform search with detailed node tracking.
        
        Parameters
        ----------
        query : str
            The search query
        group_ids : List[str] | None
            Group IDs to filter by (user IDs)
        config : SearchConfig
            Search configuration
        search_filter : SearchFilters | None
            Additional search filters
        include_contradictions : bool
            Whether to include contradiction information
        max_nodes : int
            Maximum number of nodes to track
            
        Returns
        -------
        Dict[str, Any]
            Dictionary containing search results and tracked nodes
        """
        try:
            # Perform enhanced contradiction search
            search_results = await enhanced_contradiction_search(
                self.clients,
                query,
                config=config,
                group_ids=group_ids,
                search_filter=search_filter,
            )
            
            # Extract and format reasoning nodes
            reasoning_nodes = await self._extract_reasoning_nodes(
                search_results.nodes[:max_nodes],
                search_results.edges,
                query
            )
            
            # Get contradiction information
            contradictions_info = self._extract_contradiction_info(search_results)
            
            return {
                "search_results": search_results,
                "reasoning_nodes": reasoning_nodes,
                "contradictions": contradictions_info,
                "query": query,
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error in search_with_node_tracking: {str(e)}")
            return {
                "search_results": None,
                "reasoning_nodes": [],
                "contradictions": {},
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat(),
            }
    
    async def _extract_reasoning_nodes(
        self,
        nodes: List[EntityNode],
        edges: List[EntityEdge],
        query: str
    ) -> List[ReasoningNode]:
        """Extract and format reasoning nodes with salience and confidence."""
        reasoning_nodes = []
        
        for node in nodes:
            try:
                # Extract salience and confidence from node attributes
                attributes = node.attributes or {}
                salience = self._extract_salience(node, attributes)
                confidence = self._extract_confidence(node, attributes)
                
                # Determine how this node was used in context
                context_usage = self._determine_context_usage(node, edges, query)
                
                reasoning_node = ReasoningNode(
                    uuid=node.uuid,
                    name=node.name,
                    salience=salience,
                    confidence=confidence,
                    summary=node.summary,
                    node_type=self._determine_node_type(node),
                    used_in_context=context_usage,
                )
                
                reasoning_nodes.append(reasoning_node)
                
            except Exception as e:
                logger.warning(f"Error processing node {node.uuid}: {str(e)}")
                continue
        
        return reasoning_nodes
    
    def _extract_salience(self, node: EntityNode, attributes: Dict[str, Any]) -> Optional[float]:
        """Extract salience from node attributes."""
        # Try various ways to extract salience
        salience_candidates = [
            attributes.get("salience"),
            attributes.get("importance"),
            attributes.get("relevance"),
            attributes.get("centrality"),
        ]
        
        for candidate in salience_candidates:
            if candidate is not None:
                try:
                    return float(candidate)
                except (ValueError, TypeError):
                    continue
        
        # Default salience based on connections
        return self._calculate_default_salience(node)
    
    def _extract_confidence(self, node: EntityNode, attributes: Dict[str, Any]) -> Optional[float]:
        """Extract confidence from node attributes."""
        # Try various ways to extract confidence
        confidence_candidates = [
            attributes.get("confidence"),
            attributes.get("certainty"),
            attributes.get("reliability"),
            attributes.get("validity"),
        ]
        
        for candidate in confidence_candidates:
            if candidate is not None:
                try:
                    return float(candidate)
                except (ValueError, TypeError):
                    continue
        
        # Default confidence
        return self._calculate_default_confidence(node)
    
    def _calculate_default_salience(self, node: EntityNode) -> float:
        """Calculate default salience based on node properties."""
        # Simple heuristic: more recent nodes have higher salience
        try:
            if node.created_at:
                # Calculate days since creation
                days_since_creation = (datetime.now() - node.created_at).days
                # Higher salience for more recent nodes (decay function)
                salience = max(0.1, 1.0 - (days_since_creation / 365.0))
                return min(1.0, salience)
        except:
            pass
        
        return 0.5  # Default neutral salience
    
    def _calculate_default_confidence(self, node: EntityNode) -> float:
        """Calculate default confidence based on node properties."""
        # Simple heuristic: nodes with more content have higher confidence
        try:
            if node.summary:
                # Longer summaries might indicate more detailed/confident information
                length_factor = min(1.0, len(node.summary) / 500.0)
                return max(0.3, 0.5 + length_factor * 0.3)
        except:
            pass
        
        return 0.7  # Default moderate confidence
    
    def _determine_node_type(self, node: EntityNode) -> str:
        """Determine the type of node based on its properties."""
        attributes = node.attributes or {}
        
        # Check for explicit type in attributes
        if "type" in attributes:
            return str(attributes["type"])
        
        # Check for contradiction flags
        if attributes.get("has_contradictions"):
            return "contradictory"
        
        # Check node labels
        labels = getattr(node, "labels", [])
        if "Entity" in labels:
            return "entity"
        elif "Concept" in labels:
            return "concept"
        
        return "knowledge"
    
    def _determine_context_usage(
        self,
        node: EntityNode,
        edges: List[EntityEdge],
        query: str
    ) -> str:
        """Determine how this node was used in the reasoning context."""
        contexts = []
        
        # Check if node is directly related to query terms
        query_lower = query.lower()
        if any(term in node.name.lower() for term in query_lower.split()):
            contexts.append("direct_match")
        
        # Check for contradictions
        node_uuid = node.uuid
        contradiction_edges = [
            edge for edge in edges
            if edge.name == "CONTRADICTS" and (
                edge.source_node_uuid == node_uuid or 
                edge.target_node_uuid == node_uuid
            )
        ]
        
        if contradiction_edges:
            contexts.append("contradiction_analysis")
        
        # Check for semantic similarity (if available in attributes)
        attributes = node.attributes or {}
        if attributes.get("similarity_score"):
            contexts.append("semantic_similarity")
        
        # Default context
        if not contexts:
            contexts.append("contextual_relevance")
        
        return ", ".join(contexts)
    
    def _extract_contradiction_info(self, search_results) -> Dict[str, Any]:
        """Extract contradiction information from search results."""
        if not hasattr(search_results, "contradiction_edges"):
            return {}
        
        contradiction_info = {
            "total_contradictions": len(search_results.contradiction_edges),
            "contradicted_nodes": len(search_results.contradicted_nodes_map),
            "contradicting_nodes": len(search_results.contradicting_nodes_map),
        }
        
        return contradiction_info
    
    async def generate_reasoning_summary(
        self,
        reasoning_nodes: List[ReasoningNode],
        query: str
    ) -> str:
        """Generate a summary of the reasoning process."""
        if not reasoning_nodes:
            return "No reasoning nodes were used in this response."
        
        # Sort nodes by salience (highest first)
        sorted_nodes = sorted(
            reasoning_nodes,
            key=lambda x: x.salience or 0.0,
            reverse=True
        )
        
        summary_parts = [
            f"Reasoning involved {len(reasoning_nodes)} knowledge nodes:"
        ]
        
        for i, node in enumerate(sorted_nodes[:5], 1):  # Top 5 nodes
            confidence_str = f"{node.confidence:.2f}" if node.confidence else "unknown"
            salience_str = f"{node.salience:.2f}" if node.salience else "unknown"
            
            summary_parts.append(
                f"{i}. {node.name} (confidence: {confidence_str}, salience: {salience_str})"
            )
        
        if len(reasoning_nodes) > 5:
            summary_parts.append(f"... and {len(reasoning_nodes) - 5} more nodes")
        
        return "\n".join(summary_parts) 