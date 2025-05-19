"""
Custom edge types for extending graphiti_core functionality
without modifying the original codebase.
"""

# Define the custom edge types as constants
REINFORCES = "REINFORCES"
CONTRADICTS = "CONTRADICTS"
EXTENDS = "EXTENDS"
SUPPORTS = "SUPPORTS"
ELABORATES = "ELABORATES"
MENTIONS = "MENTIONS"  # Already exists in graphiti_core, included for completeness

# Dictionary mapping edge types to their descriptions
EDGE_TYPE_DESCRIPTIONS = {
    REINFORCES: "Indicates that the source node strengthens or provides additional evidence for the target node",
    CONTRADICTS: "Indicates that the source node contradicts or conflicts with the target node",
    EXTENDS: "Indicates that the source node extends or builds upon the target node",
    SUPPORTS: "Indicates that the source node provides support for the target node",
    ELABORATES: "Indicates that the source node provides additional details about the target node",
    MENTIONS: "Indicates that the source node mentions the target node (default in graphiti_core)",
}

# Define a list of custom edge types (excluding MENTIONS which is already in graphiti_core)
CUSTOM_EDGE_TYPES = [REINFORCES, CONTRADICTS, EXTENDS, SUPPORTS, ELABORATES]

# All edge types (including MENTIONS from graphiti_core)
ALL_EDGE_TYPES = CUSTOM_EDGE_TYPES + [MENTIONS]

# Neo4j Cypher query to create custom edge types
CUSTOM_EDGE_TYPE_CREATION_QUERY = """
MATCH (source:Entity {uuid: $source_node_uuid})
MATCH (target:Entity {uuid: $target_node_uuid})
CREATE (source)-[e:RELATES_TO {
    uuid: $uuid,
    group_id: $group_id,
    name: $edge_type,
    fact: $fact,
    episodes: $episodes,
    created_at: $created_at,
    valid_at: $valid_at,
    invalid_at: $invalid_at
}]->(target)
RETURN e.uuid as uuid
""" 