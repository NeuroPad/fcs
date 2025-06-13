# Graphiti Extend

This module extends the core Graphiti functionality with advanced contradiction detection and enhanced search capabilities.

## Features

### 1. Node Contradiction Detection

The module automatically detects contradictions between new nodes and existing nodes in the knowledge graph. When contradictions are found, it creates `CONTRADICTS` edges between the conflicting nodes.

### 2. Enhanced Episode Processing

The `ExtendedGraphiti` class provides an enhanced version of `add_episode` that includes automatic contradiction detection:

```python
from graphiti_extend import ExtendedGraphiti

# Initialize with contradiction detection enabled
extended_graphiti = ExtendedGraphiti(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password",
    enable_contradiction_detection=True,
    contradiction_threshold=0.7
)

# Add episode with contradiction detection
result = await extended_graphiti.add_episode_with_contradictions(
    name="User Statement",
    episode_body="I love chocolate ice cream",
    source_description="User preference",
    reference_time=datetime.now(),
    group_id="user123"
)

# Check for contradictions
if result.contradiction_result.contradictions_found:
    print(f"Contradiction detected: {result.contradiction_result.contradiction_message}")
    # This might output: "You said vanilla ice cream before. This feels different with chocolate ice cream. Want to look at it?"
```

### 3. Contradiction-Aware Search

Enhanced search functionality that takes into account `CONTRADICTS` relationships:

```python
# Basic contradiction-aware search
results = await extended_graphiti.contradiction_aware_search(
    query="ice cream preferences",
    group_ids=["user123"],
    include_contradictions=True
)

# Enhanced search with detailed contradiction mappings
detailed_results = await extended_graphiti.enhanced_contradiction_search(
    query="ice cream preferences",
    group_ids=["user123"]
)

# Access contradiction information
for node in detailed_results.nodes:
    if node.attributes.get('has_contradictions'):
        contradicted_nodes = node.attributes.get('contradicted_nodes', [])
        contradicting_nodes = node.attributes.get('contradicting_nodes', [])
        print(f"Node {node.name} has contradictions")
```

### 4. FCS System Integration

The module generates human-readable contradiction messages that can be used with the FCS (Feedback and Clarification System):

```python
# When contradictions are detected, the system generates messages like:
# "You said X before. This feels different. Want to look at it?"

# The FCS system can then present options:
# - "Yes" (explore the contradiction)
# - "No" (ignore the contradiction)  
# - "I now believe this..." (update belief)
```

## API Reference

### ExtendedGraphiti Class

#### Constructor Parameters

- `uri`: Neo4j database URI
- `user`: Database username
- `password`: Database password
- `llm_client`: Optional LLM client (defaults to OpenAI)
- `embedder`: Optional embedder client (defaults to OpenAI)
- `cross_encoder`: Optional cross-encoder client (defaults to OpenAI)
- `store_raw_episode_content`: Whether to store raw episode content
- `enable_contradiction_detection`: Enable/disable contradiction detection
- `contradiction_threshold`: Similarity threshold for finding contradictions (0.0-1.0)

#### Key Methods

##### `add_episode_with_contradictions()`

Enhanced episode processing with contradiction detection.

**Parameters:**
- `name`: Episode name
- `episode_body`: Episode content
- `source_description`: Description of the episode source
- `reference_time`: Timestamp for the episode
- `source`: Episode type (message, text, json)
- `group_id`: Graph partition identifier
- `uuid`: Optional episode UUID
- `update_communities`: Whether to update communities
- `entity_types`: Optional entity type definitions
- `previous_episode_uuids`: Optional previous episode UUIDs
- `edge_types`: Optional edge type definitions
- `edge_type_map`: Optional edge type mapping

**Returns:**
`ExtendedAddEpisodeResults` containing:
- `episode`: The created episode
- `nodes`: Extracted/resolved nodes
- `edges`: Created edges (including contradiction edges)
- `contradiction_result`: Contradiction detection results

##### `contradiction_aware_search()`

Search with contradiction awareness.

**Parameters:**
- `query`: Search query string
- `config`: Search configuration
- `group_ids`: Optional group ID filter
- `center_node_uuid`: Optional center node for distance-based ranking
- `bfs_origin_node_uuids`: Optional BFS origin nodes
- `search_filter`: Optional search filters
- `include_contradictions`: Whether to include contradiction info

**Returns:**
`SearchResults` with enhanced contradiction metadata.

##### `enhanced_contradiction_search()`

Detailed contradiction-aware search.

**Returns:**
`ContradictionSearchResults` with detailed contradiction mappings.

##### `get_contradiction_summary()`

Get a summary of all contradictions in the graph.

**Returns:**
Dictionary containing:
- `total_contradictions`: Total number of contradiction edges
- `nodes_with_contradictions`: Number of nodes involved in contradictions
- `contradictions_by_source`: Contradictions grouped by source node
- `recent_contradictions`: Most recent contradiction edges

### Standalone Functions

#### `get_node_contradictions()`

Detect contradictions between a new node and existing nodes.

```python
from graphiti_extend.node_operations import get_node_contradictions

contradicted_nodes = await get_node_contradictions(
    llm_client=llm_client,
    new_node=new_node,
    existing_nodes=existing_nodes,
    episode=episode,
    previous_episodes=previous_episodes
)
```

#### `create_contradiction_edges()`

Create CONTRADICTS edges between nodes.

```python
from graphiti_extend.node_operations import create_contradiction_edges

contradiction_edges = await create_contradiction_edges(
    new_node=new_node,
    contradicted_nodes=contradicted_nodes,
    episode=episode
)
```

#### `contradiction_aware_search()`

Standalone contradiction-aware search function.

```python
from graphiti_extend.search import contradiction_aware_search

results = await contradiction_aware_search(
    clients=graphiti_clients,
    query="search query",
    group_ids=["group1"],
    include_contradictions=True
)
```

## Data Models

### ContradictionDetectionResult

```python
class ContradictionDetectionResult(BaseModel):
    contradictions_found: bool
    contradiction_edges: list[EntityEdge]
    contradicted_nodes: list[EntityNode]
    contradicting_nodes: list[EntityNode]
    contradiction_message: str | None = None
```

### ExtendedAddEpisodeResults

```python
class ExtendedAddEpisodeResults(AddEpisodeResults):
    contradiction_result: ContradictionDetectionResult
```

### ContradictionSearchResults

```python
class ContradictionSearchResults(SearchResults):
    contradiction_edges: list[EntityEdge]
    contradicted_nodes_map: dict[str, list[EntityNode]]
    contradicting_nodes_map: dict[str, list[EntityNode]]
```

## Integration with FCS System

The module is designed to work seamlessly with the FCS (Feedback and Clarification System). When contradictions are detected:

1. **Detection**: The system identifies conflicting information between new and existing nodes
2. **Notification**: A human-readable message is generated (e.g., "You said X before. This feels different. Want to look at it?")
3. **User Response**: The FCS system can present options:
   - "Yes": Explore the contradiction in detail
   - "No": Acknowledge but ignore the contradiction
   - "I now believe this...": Update the user's belief system

## Example Usage

```python
import asyncio
from datetime import datetime
from graphiti_extend import ExtendedGraphiti

async def main():
    # Initialize extended Graphiti
    graphiti = ExtendedGraphiti(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password",
        enable_contradiction_detection=True
    )
    
    # Add first episode
    result1 = await graphiti.add_episode_with_contradictions(
        name="Preference 1",
        episode_body="I really enjoy vanilla ice cream",
        source_description="User preference",
        reference_time=datetime.now(),
        group_id="user123"
    )
    
    # Add contradicting episode
    result2 = await graphiti.add_episode_with_contradictions(
        name="Preference 2", 
        episode_body="I hate vanilla ice cream, chocolate is much better",
        source_description="User preference",
        reference_time=datetime.now(),
        group_id="user123"
    )
    
    # Check for contradictions
    if result2.contradiction_result.contradictions_found:
        print("Contradiction detected!")
        print(result2.contradiction_result.contradiction_message)
        
        # Get contradiction summary
        summary = await graphiti.get_contradiction_summary(group_ids=["user123"])
        print(f"Total contradictions: {summary['total_contradictions']}")
    
    # Search with contradiction awareness
    search_results = await graphiti.contradiction_aware_search(
        query="ice cream preferences",
        group_ids=["user123"]
    )
    
    print(f"Found {len(search_results.edges)} edges")
    print(f"Found {len([e for e in search_results.edges if e.name == 'CONTRADICTS'])} contradiction edges")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

### Contradiction Detection Settings

- `enable_contradiction_detection`: Boolean to enable/disable the feature
- `contradiction_threshold`: Float (0.0-1.0) similarity threshold for finding potential contradictions
  - Higher values = more strict contradiction detection
  - Lower values = more lenient contradiction detection

### Search Settings

- `include_contradictions`: Whether to include contradiction information in search results
- `contradiction_weight`: Weight applied to contradicted nodes in search scoring

## Performance Considerations

1. **Contradiction Detection**: Adds computational overhead during episode processing
2. **Search Enhancement**: Minimal impact on search performance
3. **Database Storage**: Additional `CONTRADICTS` edges are stored in the graph
4. **Memory Usage**: Contradiction metadata is included in search results

## Troubleshooting

### Common Issues

1. **No contradictions detected**: Check the `contradiction_threshold` setting
2. **Too many false positives**: Increase the `contradiction_threshold`
3. **Performance issues**: Consider disabling contradiction detection for bulk operations
4. **Missing contradiction edges**: Ensure `enable_contradiction_detection=True`

### Debugging

Enable debug logging to see contradiction detection in action:

```python
import logging
logging.getLogger('graphiti_extend').setLevel(logging.DEBUG)
```

## How to Run Tests

You can now run the tests in several ways:

### 1. Direct pytest command:
```bash
python -m pytest graphiti_extend/tests/test_node_operations.py -v
```

### 2. All graphiti_extend tests:
```bash
python -m pytest graphiti_extend/tests/ -v
```

### 3. Using the test runner script:
```bash
python graphiti_extend/run_tests.py
```

The test suite includes comprehensive tests for:
- Node contradiction detection
- Contradiction edge creation
- Full contradiction detection workflow
- Edge properties validation
- LLM context structure verification

All tests use async/await patterns and mock LLM clients for reliable testing without external dependencies.

## License

This module follows the same Apache 2.0 license as the core Graphiti project. 