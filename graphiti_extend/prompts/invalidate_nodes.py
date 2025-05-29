"""
Copyright 2025, FCS Software, Inc

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

from typing import Any, Protocol, TypedDict

from pydantic import BaseModel, Field

from graphiti_core.prompts.models import Message, PromptFunction, PromptVersion


class ContradictedNodes(BaseModel):
    contradicted_nodes: list[int] = Field(
        ...,
        description='List of ids of nodes that contradict the new node. If no nodes contradict, the list should be empty.',
    )


class Prompt(Protocol):
    v1: PromptVersion


class Versions(TypedDict):
    v1: PromptFunction


def v1(context: dict[str, Any]) -> list[Message]:
    return [
        Message(
            role='system',
            content='You are an AI assistant that determines which nodes contradict each other based on their attributes and summaries.',
        ),
        Message(
            role='user',
            content=f"""
               Based on the provided EXISTING NODES and a NEW NODE, determine which existing nodes the new node contradicts.
               Return a list containing all ids of the nodes that are contradicted by the NEW NODE.
               If there are no contradicted nodes, return an empty list.

               Two nodes contradict each other if:
               1. They represent the same entity but have conflicting information in their summaries or attributes
               2. They make mutually exclusive claims about the same subject
               3. They contain factual information that cannot both be true simultaneously

               Do NOT consider nodes as contradictory if:
               1. They simply represent different entities with similar names
               2. They contain complementary or additional information about the same entity
               3. They represent different time periods or contexts where both could be true

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


versions: Versions = {'v1': v1} 