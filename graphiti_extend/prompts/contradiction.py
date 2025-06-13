"""
Copyright 2025, FCS Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
... (license continues) ...
"""
from typing import Any
from pydantic import BaseModel, Field
from graphiti_core.prompts.models import Message
# If you need shared prompt logic, import from .lib
# from .lib import ...

class ContradictedNodes(BaseModel):
    contradicted_nodes: list[int] = Field(
        ...,
        description='List of ids of nodes that contradict the new node. If no nodes contradict, the list should be empty.',
    )

def get_contradiction_prompt(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are an AI assistant that determines which nodes contradict each other based on their attributes and summaries. You specialize in detecting contradictions between ideas, preferences, beliefs, and factual claims. IMPORTANT: A node cannot contradict itself - only return nodes that are genuinely contradictory. If no contradictions exist, return an empty list.',
        ),
        Message(
            role='user',
            content=f"""
               Based on the provided EXISTING NODES and a NEW NODE, determine which existing nodes the new node contradicts.
               Return a list containing all ids of the nodes that are contradicted by the NEW NODE.
               ... (rest of prompt unchanged) ...
                <EXISTING NODES>
                {context['existing_nodes']}
                </EXISTING NODES>

                <NEW NODE>
                {context['new_node']}
                </NEW NODE>

                <EPISODE CONTENT>
                {context['episode_content']}
                </EPISODE CONTENT>

                <PREVIOUS EPISODES>
                {context['previous_episodes']}
                </PREVIOUS EPISODES>
            """,
        ),
    ]

versions = {'v1': get_contradiction_prompt} 