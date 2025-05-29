"""
Copyright 2024, Zep Software, Inc.

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
            content='You are an AI assistant that determines which nodes contradict each other based on their attributes and summaries. You specialize in detecting contradictions between ideas, preferences, beliefs, and factual claims.',
        ),
        Message(
            role='user',
            content=f"""
               Based on the provided EXISTING NODES and a NEW NODE, determine which existing nodes the new node contradicts.
               Return a list containing all ids of the nodes that are contradicted by the NEW NODE.
               If there are no contradicted nodes, return an empty list.

               Two nodes contradict each other if:
               1. They represent conflicting preferences, opinions, or beliefs about the same subject
               2. They make mutually exclusive claims about the same topic
               3. They contain factual information that cannot both be true simultaneously
               4. They express opposite sentiments or attitudes toward the same entity or concept
               5. They represent contradictory behavioral patterns or habits

               EXAMPLES OF CONTRADICTIONS:
               - "I love vanilla ice cream" vs "I hate vanilla ice cream"
               - "I prefer chocolate" vs "I prefer vanilla" (when stated as exclusive preferences)
               - "The user loves vanilla ice cream" vs "The user now prefers chocolate ice cream over vanilla"
               - "The user initially loved vanilla" vs "The user now prefers chocolate"
               - "I exercise daily" vs "I never exercise"
               - "I am vegetarian" vs "I eat meat regularly"
               - "I work at Company A" vs "I work at Company B" (if stated as current employment)
               - "The meeting is at 3 PM" vs "The meeting is at 5 PM" (same meeting)

               PREFERENCE CONTRADICTIONS - PAY SPECIAL ATTENTION:
               When someone expresses a preference for one thing over another, it contradicts previous statements about loving or preferring the alternative:
               - "loves vanilla ice cream" CONTRADICTS "prefers chocolate ice cream over vanilla"
               - "favorite flavor is vanilla" CONTRADICTS "now prefers chocolate"
               - "enjoys vanilla" CONTRADICTS "prefers chocolate instead"

               Do NOT consider nodes as contradictory if:
               1. They represent different entities with similar names (e.g., "John Smith the teacher" vs "John Smith the doctor")
               2. They contain complementary or additional information about the same entity
               3. They represent different time periods where both could be true sequentially (unless explicitly contradictory)
               4. They are about different subjects or contexts
               5. One is a person and the other is an object/concept they relate to (unless expressing contradictory relationships)
               6. They represent evolving preferences that acknowledge the change (e.g., "used to like X, now likes Y")

               EXAMPLES OF NON-CONTRADICTIONS:
               - "Jane Doe" vs "vanilla ice cream" (person vs food item - unless expressing contradictory relationships)
               - "I used to like vanilla but now prefer chocolate" (acknowledges temporal change)
               - "I work hard" vs "I am lazy sometimes" (different contexts/aspects)
               - "I live in New York" vs "I visited Paris" (different locations, different contexts)

               FOCUS ON CONCEPTUAL CONTRADICTIONS:
               Look for contradictions between IDEAS, PREFERENCES, BELIEFS, and CLAIMS rather than between entities and the concepts they relate to.
               
               CRITICAL: If a node summary contains preference language like "loves", "prefers", "likes", "enjoys" about one thing, and another node contains preference language favoring a different thing, they likely contradict each other.

               For example:
               - If someone says "I love vanilla" and later "I hate vanilla" → CONTRADICTION
               - If someone says "I love vanilla" and later "I prefer chocolate" → CONTRADICTION (exclusive preference)
               - If someone says "loves vanilla ice cream" and later "prefers chocolate ice cream over vanilla" → CONTRADICTION
               - But "Jane Doe" and "vanilla" are NOT contradictory (person vs concept) unless expressing contradictory relationships

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