"""
Example usage of the graphiti_extend module.

This script demonstrates how to use the ExtendedGraphiti class
to detect contradictions between user statements.
"""

import asyncio
import logging
from datetime import datetime

from graphiti_extend import ExtendedGraphiti

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """
    Demonstrate contradiction detection with ice cream preferences.
    """
    # Initialize extended Graphiti with contradiction detection enabled
    graphiti = ExtendedGraphiti(
        uri="bolt://localhost:7687",
        user="neo4j", 
        password="password",
        enable_contradiction_detection=True,
        contradiction_threshold=0.7  # Adjust sensitivity
    )
    
    try:
        # Build indices and constraints (run once)
        await graphiti.build_indices_and_constraints()
        
        user_id = "user123"
        
        # Episode 1: User likes vanilla
        logger.info("Adding first episode: User likes vanilla ice cream")
        result1 = await graphiti.add_episode_with_contradictions(
            name="Ice Cream Preference 1",
            episode_body="I absolutely love vanilla ice cream. It's my favorite flavor and I eat it every day.",
            source_description="User preference statement",
            reference_time=datetime.now(),
            group_id=user_id
        )
        
        logger.info(f"Episode 1 processed. Found {len(result1.nodes)} nodes and {len(result1.edges)} edges")
        if result1.contradiction_result.contradictions_found:
            logger.info(f"Contradictions in episode 1: {result1.contradiction_result.contradiction_message}")
        else:
            logger.info("No contradictions found in episode 1")
        
        # Episode 2: User dislikes vanilla (contradiction!)
        logger.info("\nAdding second episode: User dislikes vanilla ice cream")
        result2 = await graphiti.add_episode_with_contradictions(
            name="Ice Cream Preference 2",
            episode_body="I hate vanilla ice cream. It's so boring and tasteless. Chocolate is much better.",
            source_description="User preference statement",
            reference_time=datetime.now(),
            group_id=user_id
        )
        
        logger.info(f"Episode 2 processed. Found {len(result2.nodes)} nodes and {len(result2.edges)} edges")
        
        # Check for contradictions
        if result2.contradiction_result.contradictions_found:
            logger.info("🚨 CONTRADICTION DETECTED! 🚨")
            logger.info(f"Message: {result2.contradiction_result.contradiction_message}")
            logger.info(f"Number of contradiction edges: {len(result2.contradiction_result.contradiction_edges)}")
            logger.info(f"Contradicting nodes: {[n.name for n in result2.contradiction_result.contradicting_nodes]}")
            logger.info(f"Contradicted nodes: {[n.name for n in result2.contradiction_result.contradicted_nodes]}")
            
            # This is where the FCS system would present options:
            # "Yes", "No", "I now believe this..."
            logger.info("\nFCS System would now ask:")
            logger.info("'You said vanilla ice cream before. This feels different. Want to look at it?'")
            logger.info("Options: [Yes] [No] [I now believe this...]")
            
        else:
            logger.info("No contradictions found in episode 2")
        
        # Episode 3: User clarifies preference
        logger.info("\nAdding third episode: User clarifies preference")
        result3 = await graphiti.add_episode_with_contradictions(
            name="Ice Cream Clarification",
            episode_body="Actually, I used to like vanilla but my taste has changed. Now I prefer chocolate.",
            source_description="User clarification",
            reference_time=datetime.now(),
            group_id=user_id
        )
        
        logger.info(f"Episode 3 processed. Found {len(result3.nodes)} nodes and {len(result3.edges)} edges")
        if result3.contradiction_result.contradictions_found:
            logger.info(f"Contradictions in episode 3: {result3.contradiction_result.contradiction_message}")
        
        # Demonstrate contradiction-aware search
        logger.info("\n" + "="*50)
        logger.info("DEMONSTRATION: Contradiction-Aware Search")
        logger.info("="*50)
        
        search_results = await graphiti.contradiction_aware_search(
            query="ice cream preferences",
            group_ids=[user_id],
            include_contradictions=True
        )
        
        logger.info(f"Search found {len(search_results.edges)} total edges")
        
        # Count different types of edges
        contradiction_edges = [e for e in search_results.edges if e.name == 'CONTRADICTS']
        regular_edges = [e for e in search_results.edges if e.name != 'CONTRADICTS']
        
        logger.info(f"- Regular edges: {len(regular_edges)}")
        logger.info(f"- Contradiction edges: {len(contradiction_edges)}")
        
        # Show nodes with contradiction metadata
        logger.info(f"\nNodes found: {len(search_results.nodes)}")
        for node in search_results.nodes:
            if node.attributes and node.attributes.get('has_contradictions'):
                logger.info(f"- {node.name} (HAS CONTRADICTIONS)")
                contradicted = node.attributes.get('contradicted_nodes', [])
                contradicting = node.attributes.get('contradicting_nodes', [])
                if contradicted:
                    logger.info(f"  Contradicts: {contradicted}")
                if contradicting:
                    logger.info(f"  Contradicted by: {contradicting}")
            else:
                logger.info(f"- {node.name}")
        
        # Get contradiction summary
        logger.info("\n" + "="*50)
        logger.info("CONTRADICTION SUMMARY")
        logger.info("="*50)
        
        summary = await graphiti.get_contradiction_summary(group_ids=[user_id])
        logger.info(f"Total contradictions in graph: {summary['total_contradictions']}")
        logger.info(f"Nodes with contradictions: {summary['nodes_with_contradictions']}")
        
        if summary['recent_contradictions']:
            logger.info("\nRecent contradictions:")
            for edge in summary['recent_contradictions'][:3]:  # Show first 3
                logger.info(f"- {edge.fact}")
        
        # Demonstrate enhanced search
        logger.info("\n" + "="*50)
        logger.info("ENHANCED CONTRADICTION SEARCH")
        logger.info("="*50)
        
        enhanced_results = await graphiti.enhanced_contradiction_search(
            query="ice cream",
            group_ids=[user_id]
        )
        
        logger.info(f"Enhanced search found:")
        logger.info(f"- {len(enhanced_results.edges)} edges")
        logger.info(f"- {len(enhanced_results.nodes)} nodes")
        logger.info(f"- {len(enhanced_results.contradiction_edges)} contradiction edges")
        logger.info(f"- {len(enhanced_results.contradicted_nodes_map)} nodes with contradicted mappings")
        logger.info(f"- {len(enhanced_results.contradicting_nodes_map)} nodes with contradicting mappings")
        
    except Exception as e:
        logger.error(f"Error during demonstration: {str(e)}")
        raise
    
    finally:
        # Clean up
        await graphiti.close()
        logger.info("\nDemonstration completed!")


if __name__ == "__main__":
    asyncio.run(main()) 