# Graphiti Extensions

This module extends the functionality of `graphiti_core` without modifying its code. It adds features such as custom edge types and enhanced entity creation.

## Features

### Custom Edge Types

The `custom_edges.py` module defines several additional edge types not available in the core implementation:

- `REINFORCES`: Indicates that the source node strengthens or provides additional evidence for the target node
- `CONTRADICTS`: Indicates that the source node contradicts or conflicts with the target node
- `EXTENDS`: Indicates that the source node extends or builds upon the target node
- `SUPPORTS`: Indicates that the source node provides support for the target node
- `ELABORATES`: Indicates that the source node provides additional details about the target node

### Enhanced Graphiti Class

The `EnhancedGraphiti` class in `enhanced_graphiti.py` extends the core `Graphiti` class with:

- `add_episode_with_defaults`: Adds an episode with custom default values for entity attributes (salience, confidence, flags)
- `add_custom_edge`: Creates custom edge types between entity nodes
- `add_custom_triplet`: Alias for `add_custom_edge`

### Custom Triplets

The `custom_triplet.py` module adds functionality for creating custom triplets with different edge types:

- `add_custom_triplet`: Creates a triplet with a custom edge type

## Usage

```python
from graphiti_extend.enhanced_graphiti import EnhancedGraphiti, CustomEntityAttributes
from graphiti_extend.custom_edges import REINFORCES, CONTRADICTS, EXTENDS

# Initialize with custom defaults
graphiti = EnhancedGraphiti(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password",
    default_entity_attributes=CustomEntityAttributes(
        salience=0.7,
        confidence=0.9,
        flags=["tracked"]
    )
)

# Add an episode with default values
result = await graphiti.add_episode_with_defaults(
    name="Example Episode",
    episode_body="The sky is blue and the grass is green.",
    source_description="Example",
    reference_time=datetime.now(),
    group_id="example_group"
)

# Add a custom edge between nodes
edge = await graphiti.add_custom_edge(
    source_node=result.nodes[0],
    edge_type=REINFORCES,
    target_node=result.nodes[1],
    fact=f"{result.nodes[0].name} reinforces {result.nodes[1].name}",
    group_id="example_group"
)
```

See the `example_usage.py` script for a complete demonstration. 