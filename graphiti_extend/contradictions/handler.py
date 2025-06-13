"""
Copyright 2025, FCS Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
from typing import Any, Optional, Tuple
from datetime import datetime

from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.edges import EntityEdge
from graphiti_core.llm_client import LLMClient
from graphiti_core.utils.datetime_utils import utc_now

from .models import ContradictionContext, ContradictionDetectionResult, ContradictionType
from .prompts import get_contradiction_prompt

# --- Legacy-style async contradiction helpers for compatibility ---
from graphiti_extend.prompts.invalidate_nodes import ContradictedNodes

logger = logging.getLogger(__name__)


class ContradictionHandler:
    """Handles detection and processing of contradictions between nodes."""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize the contradiction handler.
        
        Parameters
        ----------
        llm_client : LLMClient
            The LLM client for analyzing contradictions
        """
        self.llm_client = llm_client

    async def detect_contradictions(
        self,
        new_node: EntityNode,
        existing_nodes: list[EntityNode],
        episode: EpisodicNode,
        previous_episodes: Optional[list[EpisodicNode]] = None,
    ) -> ContradictionDetectionResult:
        """
        Detect contradictions between a new node and existing nodes.
        
        Parameters
        ----------
        new_node : EntityNode
            The new node to check for contradictions
        existing_nodes : list[EntityNode]
            List of existing nodes to compare against
        episode : EpisodicNode
            The current episode
        previous_episodes : Optional[list[EpisodicNode]]
            Previous episodes for context
            
        Returns
        -------
        ContradictionDetectionResult
            Result containing detected contradictions
        """
        if not existing_nodes:
            return ContradictionDetectionResult(
                contradictions_found=False,
                contradiction_edges=[],
                contradicted_nodes=[],
                contradicting_nodes=[],
            )

        # Prepare context for contradiction detection
        context = {
            'new_node': {
                'name': new_node.name,
                'summary': new_node.summary,
                'labels': new_node.labels,
                'attributes': new_node.attributes,
            },
            'existing_nodes': [
                {
                    'id': i,
                    'name': node.name,
                    'summary': node.summary,
                    'labels': node.labels,
                    'attributes': node.attributes,
                }
                for i, node in enumerate(existing_nodes)
            ],
            'episode_content': episode.content if episode else '',
            'previous_episodes': [ep.content for ep in previous_episodes] if previous_episodes else [],
        }

        # Get contradiction analysis from LLM
        contradiction_analysis = await self.llm_client.generate_response(
            get_contradiction_prompt(context),
            response_model=dict[str, Any],
        )

        # Process the contradiction analysis
        contradicted_node_ids = contradiction_analysis.get('contradicted_nodes', [])
        contradiction_type = contradiction_analysis.get('contradiction_type')
        alternative_provided = contradiction_analysis.get('alternative_provided', False)

        if not contradicted_node_ids:
            return ContradictionDetectionResult(
                contradictions_found=False,
                contradiction_edges=[],
                contradicted_nodes=[],
                contradicting_nodes=[],
            )

        # Get contradicted nodes
        contradicted_nodes = [existing_nodes[i] for i in contradicted_node_ids]

        # Create contradiction edges
        contradiction_edges = []
        contradicting_nodes = []

        for contradicted_node in contradicted_nodes:
            # Create contradiction context
            contradiction_context = ContradictionContext(
                original_node=contradicted_node,
                new_node=new_node,
                contradiction_type=ContradictionType(
                    type=contradiction_type,
                    description=contradiction_analysis.get('contradiction_description', ''),
                    requires_alternative=contradiction_analysis.get('requires_alternative', False),
                ),
                alternative_provided=alternative_provided,
                metadata=contradiction_analysis.get('metadata', {}),
            )

            # Create contradiction edge
            edge = await self._create_contradiction_edge(
                contradiction_context,
                episode,
            )
            contradiction_edges.append(edge)
            contradicting_nodes.append(new_node)

        # Generate contradiction message
        contradiction_message = self._generate_contradiction_message(
            contradicting_nodes,
            contradicted_nodes,
            contradiction_type,
        )

        return ContradictionDetectionResult(
            contradictions_found=True,
            contradiction_edges=contradiction_edges,
            contradicted_nodes=contradicted_nodes,
            contradicting_nodes=contradicting_nodes,
            contradiction_message=contradiction_message,
        )

    async def _create_contradiction_edge(
        self,
        context: ContradictionContext,
        episode: EpisodicNode,
    ) -> EntityEdge:
        """
        Create a CONTRADICTS edge between nodes.
        
        Parameters
        ----------
        context : ContradictionContext
            Context for the contradiction
        episode : EpisodicNode
            The current episode
            
        Returns
        -------
        EntityEdge
            The created contradiction edge
        """
        now = utc_now()
        
        # Create the edge
        edge = EntityEdge(
            source_node_uuid=context.new_node.uuid,
            target_node_uuid=context.original_node.uuid,
            name='CONTRADICTS',
            fact=self._generate_contradiction_fact(context),
            episodes=[episode.uuid],
            created_at=now,
            valid_at=episode.valid_at,
            group_id=episode.group_id,
            attributes={
                'contradiction_type': context.contradiction_type.type,
                'contradiction_description': context.contradiction_type.description,
                'alternative_provided': context.alternative_provided,
                **context.metadata,
            },
        )
        
        return edge

    def _generate_contradiction_fact(self, context: ContradictionContext) -> str:
        """
        Generate a human-readable fact for the contradiction edge.
        
        Parameters
        ----------
        context : ContradictionContext
            Context for the contradiction
            
        Returns
        -------
        str
            Human-readable fact
        """
        if context.contradiction_type.type == 'preference_change':
            return f"{context.new_node.name} contradicts previous preference: {context.original_node.name}"
        elif context.contradiction_type.type == 'factual_contradiction':
            return f"{context.new_node.name} contradicts previous fact: {context.original_node.name}"
        else:
            return f"{context.new_node.name} contradicts {context.original_node.name}"

    def _generate_contradiction_message(
        self,
        contradicting_nodes: list[EntityNode],
        contradicted_nodes: list[EntityNode],
        contradiction_type: str,
    ) -> str:
        """
        Generate a human-readable message about detected contradictions.
        
        Parameters
        ----------
        contradicting_nodes : list[EntityNode]
            Nodes that are contradicting others
        contradicted_nodes : list[EntityNode]
            Nodes that are being contradicted
        contradiction_type : str
            Type of contradiction detected
            
        Returns
        -------
        str
            Human-readable contradiction message
        """
        if not contradicting_nodes or not contradicted_nodes:
            return ""

        def get_node_description(node: EntityNode) -> str:
            if node.summary and len(node.summary.strip()) > 10:
                return node.summary.strip()
            return node.name

        if len(contradicting_nodes) == 1 and len(contradicted_nodes) == 1:
            contradicting_desc = get_node_description(contradicting_nodes[0])
            contradicted_desc = get_node_description(contradicted_nodes[0])
            
            if contradiction_type == 'preference_change':
                return (
                    f"I notice your preference has changed. "
                    f"Earlier you said: '{contradicted_desc}' "
                    f"But now: '{contradicting_desc}' "
                    f"Would you like to explore this change?"
                )
            else:
                return (
                    f"I found conflicting information. "
                    f"Previously: '{contradicted_desc}' "
                    f"Currently: '{contradicting_desc}' "
                    f"Want to look at this?"
                )
        else:
            contradicting_descriptions = [get_node_description(node) for node in contradicting_nodes]
            contradicted_descriptions = [get_node_description(node) for node in contradicted_nodes]
            contradicting_text = "', '".join(contradicting_descriptions)
            contradicted_text = "', '".join(contradicted_descriptions)
            
            return (
                f"I found multiple conflicting pieces of information. "
                f"Previously: '{contradicted_text}' "
                f"Currently: '{contradicting_text}' "
                f"Would you like to review these differences?"
            )

async def get_node_contradictions(
    llm_client: LLMClient,
    new_node: EntityNode,
    existing_nodes: list[EntityNode],
    episode: EpisodicNode | None = None,
    previous_episodes: list[EpisodicNode] | None = None,
) -> list[EntityNode]:
    """
    Detect contradictions between a new node and existing nodes (legacy interface).
    """
    if len(existing_nodes) == 0:
        return []

    new_node_context = {
        'name': new_node.name,
        'summary': new_node.summary,
        'labels': new_node.labels,
        'attributes': new_node.attributes,
    }
    existing_nodes_context = [
        {
            'id': i,
            'name': node.name,
            'summary': node.summary,
            'labels': node.labels,
            'attributes': node.attributes,
        }
        for i, node in enumerate(existing_nodes)
    ]
    context = {
        'new_node': new_node_context,
        'existing_nodes': existing_nodes_context,
        'episode_content': episode.content if episode is not None else '',
        'previous_episodes': [ep.content for ep in previous_episodes] if previous_episodes is not None else [],
    }
    llm_response = await llm_client.generate_response(
        get_contradiction_prompt(context),
        response_model=ContradictedNodes,
    )
    contradicted_node_ids: list[int] = llm_response.get('contradicted_nodes', [])
    contradicted_nodes: list[EntityNode] = [existing_nodes[i] for i in contradicted_node_ids]
    return contradicted_nodes

async def create_contradiction_edges(
    new_node: EntityNode,
    contradicted_nodes: list[EntityNode],
    episode: EpisodicNode,
) -> list[EntityEdge]:
    """
    Create CONTRADICTS edges between a new node and nodes it contradicts (legacy interface).
    """
    contradiction_edges: list[EntityEdge] = []
    now = utc_now()
    for contradicted_node in contradicted_nodes:
        contradiction_edge = EntityEdge(
            source_node_uuid=new_node.uuid,
            target_node_uuid=contradicted_node.uuid,
            name='CONTRADICTS',
            group_id=new_node.group_id,
            fact=f'{new_node.name} contradicts {contradicted_node.name}',
            episodes=[episode.uuid],
            created_at=now,
            valid_at=episode.valid_at,
        )
        contradiction_edges.append(contradiction_edge)
    return contradiction_edges

async def detect_and_create_node_contradictions(
    llm_client: LLMClient,
    new_node: EntityNode,
    existing_nodes: list[EntityNode],
    episode: EpisodicNode,
    previous_episodes: list[EpisodicNode] | None = None,
) -> list[EntityEdge]:
    """
    Detect contradictions and create CONTRADICTS edges in one operation (legacy interface).
    """
    contradicted_nodes = await get_node_contradictions(
        llm_client, new_node, existing_nodes, episode, previous_episodes
    )
    if not contradicted_nodes:
        return []
    contradiction_edges = await create_contradiction_edges(
        new_node, contradicted_nodes, episode
    )
    return contradiction_edges 