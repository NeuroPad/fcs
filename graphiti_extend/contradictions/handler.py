"""
Copyright 2025, FCS Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
... (license continues) ...
"""

import logging
from time import time
from graphiti_core.edges import EntityEdge
from graphiti_core.llm_client import LLMClient
from graphiti_core.llm_client.config import ModelSize
from graphiti_core.nodes import EntityNode, EpisodicNode
from graphiti_core.utils.datetime_utils import utc_now
from graphiti_extend.prompts.contradiction import ContradictedNodes, get_contradiction_prompt

logger = logging.getLogger(__name__)

async def get_node_contradictions(
    llm_client: LLMClient,
    new_node: EntityNode,
    existing_nodes: list[EntityNode],
    episode: EpisodicNode | None = None,
    previous_episodes: list[EpisodicNode] | None = None,
) -> list[EntityNode]:
    start = time()
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
        model_size=ModelSize.small,
    )
    contradicted_node_ids: list[int] = llm_response.get('contradicted_nodes', [])
    contradicted_nodes: list[EntityNode] = [existing_nodes[i] for i in contradicted_node_ids]
    end = time()
    logger.debug(
        f'Found {len(contradicted_nodes)} contradicted nodes for {new_node.name}, in {(end - start) * 1000} ms'
    )
    return contradicted_nodes

async def create_contradiction_edges(
    new_node: EntityNode,
    contradicted_nodes: list[EntityNode],
    episode: EpisodicNode,
) -> list[EntityEdge]:
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
        logger.debug(
            f'Created CONTRADICTS edge: {new_node.name} -> {contradicted_node.name}'
        )
    return contradiction_edges

async def detect_and_create_node_contradictions(
    llm_client: LLMClient,
    new_node: EntityNode,
    existing_nodes: list[EntityNode],
    episode: EpisodicNode,
    previous_episodes: list[EpisodicNode] | None = None,
) -> list[EntityEdge]:
    contradicted_nodes = await get_node_contradictions(
        llm_client, new_node, existing_nodes, episode, previous_episodes
    )
    if not contradicted_nodes:
        return []
    contradiction_edges = await create_contradiction_edges(
        new_node, contradicted_nodes, episode
    )
    return contradiction_edges
