"""
Demo script to show salience logging in action for client demonstration.

This script creates some sample CognitiveObject nodes and demonstrates
the detailed logging that shows salience changes.
"""

import asyncio
from datetime import datetime
from graphiti_core.nodes import EntityNode
from graphiti_core.utils.datetime_utils import utc_now
from .salience_manager import SalienceManager


def create_demo_cognitive_object(name: str, summary: str, salience: float = 0.5, confidence: float = 0.7) -> EntityNode:
    """Create a demo CognitiveObject node."""
    
    node = EntityNode(
        uuid=f"demo-{name.lower().replace(' ', '-')}-{id(name)}",
        name=name,
        labels=["Entity", "CognitiveObject"],
        summary=summary,
        group_id="demo_group",
        created_at=utc_now(),
        attributes={
            "entity_type": "CognitiveObject",
            "salience": salience,
            "confidence": confidence
        }
    )
    
    return node


async def demo_salience_logging():
    """
    Demonstrate the salience logging system.
    
    This shows how the system logs detailed information about:
    1. Direct salience updates
    2. Structural boosts
    3. Network reinforcement
    """
    
    print("\n" + "="*100)
    print("🎯 SALIENCE SYSTEM LOGGING DEMONSTRATION")
    print("This demo shows detailed logging of CognitiveObject salience changes")
    print("="*100)
    
    # Create demo nodes
    nodes = [
        create_demo_cognitive_object(
            "User loves chocolate ice cream",
            "The user has expressed a strong preference for chocolate flavored ice cream",
            salience=0.4,
            confidence=0.8
        ),
        create_demo_cognitive_object(
            "User prefers vanilla ice cream", 
            "The user now indicates they prefer vanilla ice cream over chocolate",
            salience=0.6,
            confidence=0.7
        ),
        create_demo_cognitive_object(
            "User enjoys coffee",
            "The user regularly drinks coffee and enjoys it",
            salience=0.3,
            confidence=0.9
        ),
        create_demo_cognitive_object(
            "User works at Tech Company",
            "The user is employed at a technology company",
            salience=0.7,
            confidence=0.85
        )
    ]
    
    # Create a mock salience manager (without database connection for demo)
    class MockSalienceManager(SalienceManager):
        def __init__(self):
            # Initialize without database driver for demo
            from .salience_manager import SalienceConfig
            self.config = SalienceConfig()
            
        async def _calculate_reinforcement_weight(self, node, base_increment, current_time):
            # Simple calculation for demo
            confidence = node.attributes.get('confidence', 0.7)
            return base_increment * (0.7 + confidence * 0.3)
            
        async def _count_high_confidence_connections(self, node_uuid):
            # Mock high connection count for some nodes
            return 4 if "chocolate" in node_uuid or "vanilla" in node_uuid else 1
            
        def _is_cognitive_object(self, node):
            return "CognitiveObject" in node.labels
    
    salience_manager = MockSalienceManager()
    
    print(f"\n📊 INITIAL NODE STATES:")
    for node in nodes:
        print(f"   - {node.name}: salience={node.attributes['salience']:.3f}, confidence={node.attributes['confidence']:.3f}")
    
    # Demo 1: Direct Salience Update (Duplicate Found)
    print(f"\n\n🎬 DEMO 1: Direct Salience Update - Duplicate Detection")
    print("Scenario: User mentions chocolate ice cream again, triggering duplicate detection")
    
    duplicate_nodes = [nodes[0]]  # chocolate ice cream node
    await salience_manager.update_direct_salience(
        duplicate_nodes, 
        'duplicate_found',
        utc_now()
    )
    
    # Demo 2: Direct Salience Update (Reasoning Usage)
    print(f"\n\n🎬 DEMO 2: Direct Salience Update - Reasoning Usage")
    print("Scenario: System uses vanilla preference in contradiction detection reasoning")
    
    reasoning_nodes = [nodes[1]]  # vanilla ice cream node
    await salience_manager.update_direct_salience(
        reasoning_nodes,
        'reasoning_usage', 
        utc_now()
    )
    
    # Demo 3: Structural Boost
    print(f"\n\n🎬 DEMO 3: Structural Importance Boost")
    print("Scenario: Well-connected nodes get structural importance boosts")
    
    await salience_manager.apply_structural_boosts(nodes[:2])  # chocolate and vanilla nodes
    
    # Demo 4: Conversation Mention
    print(f"\n\n🎬 DEMO 4: Direct Salience Update - Conversation Mention")
    print("Scenario: User explicitly mentions their work in conversation")
    
    work_nodes = [nodes[3]]  # work node
    await salience_manager.update_direct_salience(
        work_nodes,
        'conversation_mention',
        utc_now()
    )
    
    print(f"\n\n📈 FINAL NODE STATES:")
    for node in nodes:
        print(f"   - {node.name}: salience={node.attributes['salience']:.3f}")
    
    print(f"\n" + "="*100)
    print("🎯 DEMONSTRATION COMPLETE")
    print("All salience updates have been logged with detailed before/after states")
    print("Your client can see exactly how the brain-like reinforcement system works!")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(demo_salience_logging())