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
from typing import Any, List
from pydantic import BaseModel, Field
from graphiti_core.prompts.models import Message
# If you need shared prompt logic, import from .lib
# from .lib import ...

class ContradictionNode(BaseModel):
    name: str = Field(..., description='Name of the contradiction node')
    summary: str = Field(..., description='Summary describing what this node represents')
    entity_type: str = Field(default='Entity', description='Type of entity')

class ContradictionPair(BaseModel):
    node1: ContradictionNode = Field(..., description='First node in the contradiction pair')
    node2: ContradictionNode = Field(..., description='Second node in the contradiction pair')
    contradiction_reason: str = Field(..., description='Explanation of why these nodes contradict each other')

class ContradictionPairs(BaseModel):
    contradiction_pairs: List[ContradictionPair] = Field(
        default_factory=list,
        description='List of contradiction pairs found between cognitive objects'
    )

class ContradictedNodes(BaseModel):
    contradicted_nodes: list[int] = Field(
        ...,
        description='List of ids of nodes that contradict the new node. If no nodes contradict, the list should be empty.',
    )

def get_contradiction_pairs_prompt(context: dict[str, Any]) -> list[Message]:
    """
    New prompt for extracting contradiction pairs as cognitive objects.
    This prompt identifies contradictory concepts and creates new nodes when needed.
    """
    return [
        Message(
            role='system',
            content='''You are an AI assistant that identifies contradictions between cognitive objects (thoughts, preferences, beliefs, facts) and creates proper contradiction pairs.

Your task is to:
1. Analyze the current episode content and existing nodes
2. Identify contradictory concepts that should be represented as separate cognitive objects
3. Create new cognitive objects when needed to properly represent contradictions
4. Return pairs of cognitive objects that contradict each other

IMPORTANT RULES:
- Only create contradictions between CONCEPTS, PREFERENCES, BELIEFS, or FACTUAL CLAIMS
- DETECT FACTUAL CORRECTIONS: When someone corrects a specific fact (prices, numbers, dates, locations, etc.)
- Do NOT create contradictions between PEOPLE and CONCEPTS (e.g., "user" vs "football")
- Do NOT create contradictions between unrelated entities
- Create new nodes when needed to represent the contradictory concept properly
- Focus on semantic contradictions AND factual corrections about the same entity/event

CRITICAL FILTERING RULE:
- If BOTH nodes in a potential contradiction pair already exist in the EXISTING NODES list, DO NOT return that pair
- Only return pairs where at least ONE node needs to be created (i.e., at least one node is NEW)
- This prevents duplicate contradiction edges between existing nodes that may already be connected

EXAMPLES OF VALID CONTRADICTIONS:
1. If someone says "I hate football" and previously said "I love football":
   - Node1: "love football" (summary: "User loves football")
   - Node2: "hate football" (summary: "User hates football")

2. If someone says "I prefer chocolate" and previously said "I prefer vanilla":
   - Node1: "prefer vanilla" (summary: "User prefers vanilla")
   - Node2: "prefer chocolate" (summary: "User prefers chocolate")

3. If someone says "Exercise is harmful" and previously said "Exercise is beneficial":
   - Node1: "exercise is beneficial" (summary: "Exercise is beneficial for health")
   - Node2: "exercise is harmful" (summary: "Exercise is harmful")

4. FACTUAL CORRECTIONS - If someone corrects a specific fact about the same entity:
   - "I booked a hotel room for $450" then "I made a mistake it was $45"
   - Node1: "hotel room cost $450" (summary: "User booked hotel room for $450")
   - Node2: "hotel room cost $45" (summary: "User corrected hotel room cost to $45")

5. NUMERICAL/FACTUAL CONTRADICTIONS:
   - "The meeting is at 3 PM" vs "The meeting is at 5 PM" (same meeting)
   - "I have 3 cats" vs "I have 2 cats" (current pet count)
   - "I live at 123 Main St" vs "I live at 456 Oak Ave" (current address)
   - "I work at Google" vs "I work at Microsoft" (current job)

EXAMPLES OF INVALID CONTRADICTIONS (DO NOT CREATE):
- "user" vs "football" (person vs concept)
- "Tao" vs "assistant" (different people)
- "football" vs "tennis" (different sports, not contradictory unless about preference)
- "Joseph" vs "vanilla ice cream" (person vs food item)

CREATE NEW NODES when needed to represent the contradictory concept properly.
For example, if the episode says "I hate football" but no "hate football" node exists, create it.''',
        ),
        Message(
            role='user',
            content=f"""
Analyze the episode content and existing nodes to find contradiction pairs.

<EPISODE CONTENT>
{context['episode_content']}
</EPISODE CONTENT>

<EXISTING NODES>
{context.get('existing_nodes', [])}
</EXISTING NODES>

<PREVIOUS EPISODES>
{context.get('previous_episodes', [])}
</PREVIOUS EPISODES>

Instructions:
1. Look for contradictory concepts in the episode content
2. Check if existing nodes represent contradictory ideas
3. LOOK FOR FACTUAL CORRECTIONS: Check if the user is correcting specific facts, numbers, prices, dates, or other concrete information
4. Create new nodes when needed to represent contradictions properly
5. APPLY FILTERING: If both nodes in a potential pair already exist in EXISTING NODES, skip that pair
6. Return pairs of cognitive objects that genuinely contradict each other
7. Include both semantic contradictions AND factual corrections about the same entity/event

IMPORTANT: Only return pairs where at least ONE node needs to be created.
Return contradiction pairs as cognitive objects with proper names and summaries.
If no contradictions are found, return an empty list.
            """,
        ),
    ]

def get_contradiction_prompt(context: dict[str, Any]) -> list[Message]:
    """
    Original prompt for backward compatibility.
    """
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
               - "I booked a hotel room for $450" vs "I made a mistake it was $45" (factual correction)
               - "I have 3 cats" vs "I have 2 cats" (current count correction)
               - "I live at 123 Main St" vs "I live at 456 Oak Ave" (address correction)

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

versions = {
    'v1': get_contradiction_prompt,
    'pairs': get_contradiction_pairs_prompt
}