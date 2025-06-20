#!/usr/bin/env python3
"""
Debug script to test search functionality
"""

import asyncio
import logging
from datetime import datetime

from graphiti_core.llm_client import OpenAIClient
from graphiti_core.embedder import OpenAIEmbedder
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

from graphiti_extend.extended_graphiti import ExtendedGraphiti

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_search():
    """Test the search functionality"""
    
    # Initialize ExtendedGraphiti
    graphiti = ExtendedGraphiti(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
        llm_client=OpenAIClient(),
        embedder=OpenAIEmbedder(),
        cross_encoder=OpenAIRerankerClient(),
        enable_contradiction_detection=True
    )
    
    try:
        # Test 1: Basic search without contradictions
        print("=== Testing basic search ===")
        results = await graphiti.contradiction_aware_search(
            query="tao",
            group_ids=["1"],
            include_contradictions=False
        )
        
        print(f"Basic search results:")
        print(f"  Edges: {len(results.edges)}")
        print(f"  Nodes: {len(results.nodes)}")
        print(f"  Episodes: {len(results.episodes)}")
        print(f"  Communities: {len(results.communities)}")
        
        if results.edges:
            print("  Sample edges:")
            for edge in results.edges[:3]:
                print(f"    - {edge.name}: {edge.fact}")
        
        if results.nodes:
            print("  Sample nodes:")
            for node in results.nodes[:3]:
                print(f"    - {node.name}: {node.summary}")
        
        # Test 2: Search with contradictions
        print("\n=== Testing search with contradictions ===")
        results_with_contradictions = await graphiti.contradiction_aware_search(
            query="tao",
            group_ids=["1"],
            include_contradictions=True
        )
        
        print(f"Search with contradictions results:")
        print(f"  Edges: {len(results_with_contradictions.edges)}")
        print(f"  Nodes: {len(results_with_contradictions.nodes)}")
        print(f"  Episodes: {len(results_with_contradictions.episodes)}")
        print(f"  Communities: {len(results_with_contradictions.communities)}")
        
        # Test 3: Direct core search
        print("\n=== Testing direct core search ===")
        from graphiti_core.search.search_config_recipes import COMBINED_HYBRID_SEARCH_CROSS_ENCODER
        from graphiti_core.search.search_filters import SearchFilters
        
        core_results = await graphiti.search_(
            query="tao",
            group_ids=["1"],
            config=COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
            search_filter=SearchFilters()
        )
        
        print(f"Direct core search results:")
        print(f"  Edges: {len(core_results.edges)}")
        print(f"  Nodes: {len(core_results.nodes)}")
        print(f"  Episodes: {len(core_results.episodes)}")
        print(f"  Communities: {len(core_results.communities)}")
        
        # Test 4: Check if there's data in the database
        print("\n=== Checking database content ===")
        
        # Check what groups exist
        groups_query = """
        MATCH (n:Entity)
        RETURN DISTINCT n.group_id as group_id
        ORDER BY group_id
        """
        
        group_records, _, _ = await graphiti.driver.execute_query(
            groups_query,
            database_="neo4j",
            routing_="r"
        )
        
        print("Available groups:")
        for record in group_records:
            group_id = record["group_id"] or "NULL"
            print(f"  - {group_id}")
        
        # Check total entities
        total_query = """
        MATCH (n:Entity)
        RETURN count(n) as total_entities
        """
        
        total_records, _, _ = await graphiti.driver.execute_query(
            total_query,
            database_="neo4j",
            routing_="r"
        )
        
        if total_records:
            total_entities = total_records[0]["total_entities"]
            print(f"Total entities: {total_entities}")
        
        # Check entities by group
        if group_records:
            for record in group_records:
                group_id = record["group_id"]
                if group_id:
                    count_query = """
                    MATCH (n:Entity)
                    WHERE n.group_id = $group_id
                    RETURN count(n) as count
                    """
                    
                    count_records, _, _ = await graphiti.driver.execute_query(
                        count_query,
                        group_id=group_id,
                        database_="neo4j",
                        routing_="r"
                    )
                    
                    if count_records:
                        count = count_records[0]["count"]
                        print(f"  Entities in '{group_id}': {count}")
        
        # Check for any entities with "tao" in the name
        tao_query = """
        MATCH (n:Entity)
        WHERE toLower(n.name) CONTAINS toLower('tao')
        RETURN n.name as name, n.group_id as group_id
        LIMIT 10
        """
        
        tao_records, _, _ = await graphiti.driver.execute_query(
            tao_query,
            database_="neo4j",
            routing_="r"
        )
        
        print(f"\nEntities containing 'tao': {len(tao_records)}")
        for record in tao_records:
            print(f"  - {record['name']} (group: {record['group_id']})")
        
        # Check for any entities at all
        sample_query = """
        MATCH (n:Entity)
        RETURN n.name as name, n.group_id as group_id
        LIMIT 5
        """
        
        sample_records, _, _ = await graphiti.driver.execute_query(
            sample_query,
            database_="neo4j",
            routing_="r"
        )
        
        print(f"\nSample entities:")
        for record in sample_records:
            print(f"  - {record['name']} (group: {record['group_id']})")
        
        # Test search with the first available group
        if group_records and group_records[0]["group_id"]:
            first_group = group_records[0]["group_id"]
            print(f"\n=== Testing search with group '{first_group}' ===")
            
            results = await graphiti.contradiction_aware_search(
                query="tao",
                group_ids=[first_group],
                include_contradictions=False
            )
            
            print(f"Search results for group '{first_group}':")
            print(f"  Edges: {len(results.edges)}")
            print(f"  Nodes: {len(results.nodes)}")
            print(f"  Episodes: {len(results.episodes)}")
            print(f"  Communities: {len(results.communities)}")
        
    except Exception as e:
        logger.error(f"Error during search test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await graphiti.close()

if __name__ == "__main__":
    asyncio.run(test_search()) 