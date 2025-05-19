"""
Example script demonstrating the usage of graphiti_extend and fcs_core modules.
"""

import asyncio
import os
from datetime import datetime

# Import from graphiti_extend
from graphiti_extend.enhanced_graphiti import EnhancedGraphiti, CustomEntityAttributes
from graphiti_extend.custom_edges import REINFORCES, CONTRADICTS, EXTENDS, SUPPORTS, ELABORATES
from graphiti_extend.contradiction_handler import detect_and_connect_contradictions

# Import from fcs_core
from fcs_core.fcs import FCS, ContradictionResult
from fcs_core.cognitive_objects import COType, COSource, COFlags

# Neo4j connection parameters
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

async def demonstrate_graphiti_extend():
    """
    Demonstrate the usage of the graphiti_extend module.
    """
    print("\n=== Demonstrating graphiti_extend ===\n")
    
    # Initialize EnhancedGraphiti with custom default attributes
    graphiti = EnhancedGraphiti(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD,
        default_entity_attributes=CustomEntityAttributes(
            salience=0.7,
            confidence=0.9,
            flags=["tracked"]
        )
    )
    
    try:
        # Add an episode with default values
        print("Adding an episode with default values...")
        result = await graphiti.add_episode_with_defaults(
            name="Example Episode 1",
            episode_body="The sky is blue and the grass is green.",
            source_description="Example",
            reference_time=datetime.now(),
            group_id="example_group"
        )
        
        print(f"Added episode with {len(result.nodes)} nodes and {len(result.edges)} edges.")
        
        # Add a contradicting episode to demonstrate contradiction detection
        print("\nAdding a contradicting episode...")
        result2, contradiction_results = await graphiti.add_episode_with_contradiction_detection(
            name="Example Episode 2",
            episode_body="The sky is actually purple and the grass is brown.",
            source_description="Example",
            reference_time=datetime.now(),
            group_id="example_group"
        )
        
        print(f"Added episode with {len(result2.nodes)} nodes and {len(result2.edges)} edges.")
        
        # Display detected contradictions
        if contradiction_results:
            print("\nDetected contradictions:")
            for edge, contradiction_edges, invalidated_edges in contradiction_results:
                if contradiction_edges:
                    print(f"  Created {len(contradiction_edges)} contradiction edges")
                    for contra_edge in contradiction_edges:
                        print(f"    {contra_edge.fact}")
                
                if invalidated_edges:
                    print(f"  Invalidated {len(invalidated_edges)} edges")
                    for invalid_edge in invalidated_edges:
                        print(f"    {invalid_edge.fact}")
        else:
            print("\nNo contradictions detected.")
        
        # Add a custom edge between entities
        if len(result.nodes) >= 2:
            print("\nAdding a custom REINFORCES edge between two nodes...")
            edge = await graphiti.add_custom_edge(
                source_node=result.nodes[0],
                edge_type=REINFORCES,
                target_node=result.nodes[1],
                fact=f"{result.nodes[0].name} reinforces {result.nodes[1].name}",
                group_id="example_group"
            )
            
            print(f"Added custom edge: {edge.source_node_uuid} -> {edge.name} -> {edge.target_node_uuid}")
    
    finally:
        # Close the connection
        await graphiti.close()

async def demonstrate_fcs_core():
    """
    Demonstrate the usage of the fcs_core module.
    """
    print("\n=== Demonstrating fcs_core ===\n")
    
    # Initialize FCS
    fcs = FCS(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD
    )
    
    try:
        # Add user input
        print("Adding user input...")
        cos, contradictions = await fcs.add_user_input(
            content="I believe exercise is beneficial for mental health.",
            group_id="fcs_example"
        )
        
        print(f"Added {len(cos)} cognitive objects.")
        print(f"Detected {len(contradictions)} contradictions.")
        
        # Add another input that could potentially contradict
        print("\nAdding potentially contradicting input...")
        cos2, contradictions2 = await fcs.add_user_input(
            content="I find that exercise makes me feel more anxious and stressed.",
            group_id="fcs_example"
        )
        
        print(f"Added {len(cos2)} cognitive objects.")
        print(f"Detected {len(contradictions2)} contradictions.")
        
        # Print details about any contradictions
        if contradictions2:
            print("\nContradiction details:")
            for contradiction in contradictions2:
                print(f"  Original CO: {contradiction.original_co.content}")
                print(f"  Contradicted CO: {contradiction.contradicted_co.content}")
                print(f"  Confidence: {contradiction.confidence}")
                print(f"  Edge fact: {contradiction.contradiction_edge.fact}")
                print()
        
        # Add an external reference
        print("\nAdding an external reference...")
        ext_cos, ext_contradictions = await fcs.add_external_reference(
            content="Research indicates that regular physical activity can reduce anxiety and depression.",
            source_url="https://example.com/research",
            title="Effects of Exercise on Mental Health",
            authors=["Dr. Smith", "Dr. Johnson"],
            abstract="This study examines the relationship between physical activity and mental health.",
            group_id="fcs_example"
        )
        
        print(f"Added {len(ext_cos)} cognitive objects from external reference.")
        print(f"Detected {len(ext_contradictions)} contradictions with external reference.")
        
        # Print session state information
        print("\nSession state summary:")
        print(f"  Active graph size: {len(fcs.session_state.active_graph)} cognitive objects")
        print(f"  Tracked COs: {len(fcs.session_state.tracked_cos)}")
        print(f"  Active contradictions: {len(fcs.session_state.active_contradictions)}")
        print(f"  External matches: {len(fcs.session_state.external_matches)}")
    
    finally:
        # Close the connection
        await fcs.close()

async def main():
    """
    Main function to run the demonstrations.
    """
    # Demonstrate graphiti_extend
    await demonstrate_graphiti_extend()
    
    # Demonstrate fcs_core
    await demonstrate_fcs_core()

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 