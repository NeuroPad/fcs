"""
Example usage of the confidence system in ExtendedGraphiti.

This example demonstrates:
1. Initial confidence assignment
2. Confidence updates from various triggers
3. Contradiction penalties and boosts
4. Network reinforcement
5. Dormancy decay
6. Confidence queries and summaries
"""

import asyncio
from datetime import datetime, timedelta
from graphiti_extend.extended_graphiti import ExtendedGraphiti
from graphiti_extend.confidence.models import ConfidenceTrigger, OriginType
from graphiti_core.llm_client import OpenAIClient
from graphiti_core.embedder import OpenAIEmbedder


async def confidence_example():
    """Demonstrate confidence system functionality."""
    
    # Initialize ExtendedGraphiti with confidence enabled
    graphiti = ExtendedGraphiti(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
        llm_client=OpenAIClient(),
        embedder=OpenAIEmbedder(),
        enable_contradiction_detection=True,
        contradiction_threshold=0.7
    )
    
    try:
        print("=== Confidence System Example ===\n")
        
        # 1. Add episodes to create nodes with initial confidence
        print("1. Adding episodes to create nodes with initial confidence...")
        
        # Episode 1: User-given information
        result1 = await graphiti.add_episode_with_contradictions(
            name="User Preferences",
            episode_body="I love pizza and I work as a software engineer. My favorite color is blue.",
            source_description="Direct user input",
            reference_time=datetime.now(),
            group_id="user_data"
        )
        
        print(f"   Created {len(result1.nodes)} nodes from episode 1")
        
        # Episode 2: More user information (some duplicates, some new)
        result2 = await graphiti.add_episode_with_contradictions(
            name="More User Info",
            episode_body="I love pizza and I also enjoy hiking. My name is Alice.",
            source_description="Direct user input",
            reference_time=datetime.now(),
            group_id="user_data"
        )
        
        print(f"   Created {len(result2.nodes)} nodes from episode 2")
        
        # 2. Check confidence of some nodes
        print("\n2. Checking confidence of nodes...")
        
        for node in result1.nodes + result2.nodes:
            confidence = await graphiti.get_confidence(node.uuid)
            metadata = await graphiti.get_confidence_metadata(node.uuid)
            
            if confidence is not None:
                origin_type = metadata.origin_type if metadata else "unknown"
                print(f"   Node '{node.name}': confidence={confidence:.3f}, origin={origin_type}")
        
        # 3. Manual confidence updates
        print("\n3. Applying manual confidence updates...")
        
        if result1.nodes:
            # Boost confidence for user reference
            await graphiti.update_node_confidence(
                result1.nodes[0].uuid,
                ConfidenceTrigger.USER_REFERENCE,
                "User referenced this information in conversation",
                {"context": "manual_test"}
            )
            
            # Check updated confidence
            new_confidence = await graphiti.get_confidence(result1.nodes[0].uuid)
            print(f"   Updated confidence for '{result1.nodes[0].name}': {new_confidence:.3f}")
        
        # 4. Get confidence summary
        print("\n4. Getting confidence summary...")
        
        summary = await graphiti.get_confidence_summary(group_ids=["user_data"])
        print(f"   Total nodes: {summary.get('total_nodes', 0)}")
        print(f"   Average confidence: {summary.get('average_confidence', 0):.3f}")
        print(f"   Unstable nodes (<0.4): {summary.get('unstable_nodes', 0)}")
        print(f"   Low confidence nodes (<0.2): {summary.get('low_confidence_nodes', 0)}")
        
        # 5. Get low confidence nodes
        print("\n5. Getting low confidence nodes...")
        
        low_confidence = await graphiti.get_low_confidence_nodes(
            threshold=0.4,
            group_ids=["user_data"],
            limit=10
        )
        
        print(f"   Found {len(low_confidence)} nodes with confidence < 0.4:")
        for node_uuid, confidence in low_confidence:
            print(f"     {node_uuid}: {confidence:.3f}")
        
        # 6. Simulate contradiction (if we have multiple nodes)
        if len(result1.nodes) > 1 and len(result2.nodes) > 1:
            print("\n6. Simulating contradiction...")
            
            # Create a contradiction by updating one node to contradict another
            await graphiti.update_node_confidence(
                result1.nodes[0].uuid,
                ConfidenceTrigger.CONTRADICTION_DETECTED,
                "Contradicted by another high-confidence entity",
                {"contradicting_node_uuid": result2.nodes[0].uuid}
            )
            
            # Check confidence after contradiction
            contradicted_confidence = await graphiti.get_confidence(result1.nodes[0].uuid)
            print(f"   Confidence after contradiction: {contradicted_confidence:.3f}")
        
        # 7. Test confidence scheduler (manual run)
        print("\n7. Testing confidence decay (manual)...")
        
        from graphiti_extend.confidence.scheduler import ConfidenceScheduler
        
        scheduler = ConfidenceScheduler(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            group_ids=["user_data"]
        )
        
        await scheduler.initialize()
        decay_stats = await scheduler.run_manual_decay()
        print(f"   Decay stats: {decay_stats}")
        await scheduler.cleanup()
        
        print("\n=== Confidence Example Complete ===")
        
    except Exception as e:
        print(f"Error in confidence example: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await graphiti.close()


async def confidence_integration_test():
    """Test confidence integration with contradiction detection."""
    
    graphiti = ExtendedGraphiti(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
        llm_client=OpenAIClient(),
        embedder=OpenAIEmbedder(),
        enable_contradiction_detection=True,
        contradiction_threshold=0.7
    )
    
    try:
        print("=== Confidence Integration Test ===\n")
        
        # Add conflicting information
        result1 = await graphiti.add_episode_with_contradictions(
            name="Initial Information",
            episode_body="I am 25 years old and I live in New York.",
            source_description="User input",
            reference_time=datetime.now(),
            group_id="test_data"
        )
        
        result2 = await graphiti.add_episode_with_contradictions(
            name="Contradicting Information",
            episode_body="I am 30 years old and I live in California.",
            source_description="User input",
            reference_time=datetime.now(),
            group_id="test_data"
        )
        
        print(f"Episode 1 nodes: {len(result1.nodes)}")
        print(f"Episode 2 nodes: {len(result2.nodes)}")
        print(f"Contradictions found: {result2.contradiction_result.contradictions_found}")
        
        if result2.contradiction_result.contradictions_found:
            print(f"Contradiction edges: {len(result2.contradiction_result.contradiction_edges)}")
            print(f"Contradicted nodes: {len(result2.contradiction_result.contradicted_nodes)}")
            print(f"Contradicting nodes: {len(result2.contradiction_result.contradicting_nodes)}")
            
            # Check confidence of contradicted nodes
            for node in result2.contradiction_result.contradicted_nodes:
                confidence = await graphiti.get_confidence(node.uuid)
                print(f"Contradicted node '{node.name}': confidence={confidence:.3f}")
        
        print("\n=== Integration Test Complete ===")
        
    except Exception as e:
        print(f"Error in integration test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await graphiti.close()


if __name__ == "__main__":
    # Run the examples
    asyncio.run(confidence_example())
    print("\n" + "="*50 + "\n")
    asyncio.run(confidence_integration_test()) 