# FCS Salience System Implementation Guide

## Overview

The FCS Salience System implements brain-like memory reinforcement for CognitiveObject nodes in the knowledge graph. It automatically manages the strength (salience) of beliefs and concepts based on usage patterns, connections, and time, mimicking how human memory works.

## Key Features

✅ **Automatic Salience Updates**: Salience is updated during episode processing  
✅ **Network Reinforcement**: Connected concepts reinforce each other  
✅ **Temporal Decay**: Unused concepts naturally fade over time  
✅ **Scheduled Forgetting**: Background processes clean up forgotten concepts  
✅ **Brain-like Behavior**: Mimics human memory patterns  
✅ **Configurable Parameters**: Customizable reinforcement and decay rates  

## Architecture

### Core Components

1. **SalienceManager**: Handles all salience calculations and updates
2. **SalienceScheduler**: Manages periodic decay cycles
3. **ExtendedGraphiti**: Integrates salience updates into episode processing
4. **SalienceConfig**: Configuration for all salience parameters

### Integration Points

The salience system is integrated at these points in the episode processing pipeline:

1. **After Node Resolution**: Duplicate detection triggers salience boosts
2. **After Hydration**: Network reinforcement propagates through connections
3. **During Contradiction Detection**: Reasoning usage and contradiction involvement boost salience
4. **Background Decay**: Scheduled processes handle temporal decay and cleanup

## Quick Start

### Basic Setup

```python
from graphiti_extend import ExtendedGraphiti, SalienceConfig
from fcs_core.models import CognitiveObject

# Initialize ExtendedGraphiti (salience is automatically enabled)
graphiti = ExtendedGraphiti(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password",
    enable_contradiction_detection=True
)

# Define entity types
entity_types = {
    'CognitiveObject': CognitiveObject
}

# Process episodes - salience updates happen automatically
result = await graphiti.add_episode_with_contradictions(
    name="Learning Session",
    episode_body="I love Python programming. It's great for data science.",
    source_description="User preference",
    reference_time=datetime.now(),
    group_id="user_123",
    entity_types=entity_types
)

# Check salience values
for node in result.nodes:
    if 'CognitiveObject' in node.labels:
        salience = node.attributes.get('salience', 0.5)
        print(f"{node.name}: salience={salience:.3f}")
```

### FastAPI with Scheduled Decay

```python
from fastapi import FastAPI
from graphiti_extend.salience.scheduler import setup_salience_scheduler

app = FastAPI()

# Set up automatic decay every 4 hours
scheduler = setup_salience_scheduler(
    app=app,
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password",
    cron_schedule="0 */4 * * *"  # Every 4 hours
)

# Run with: uvicorn your_app:app --reload
```

## Salience Update Triggers

### Direct Activation

| Trigger | Salience Increase | When It Happens |
|---------|------------------|-----------------|
| **Conversation Mention** | +0.3 | Node explicitly mentioned in episode |
| **Duplicate Found** | +0.25 | Node resolved as duplicate during processing |
| **Reasoning Usage** | +0.2 | Node used in contradiction detection |
| **Contradiction Involvement** | +0.1 | Node directly involved in contradiction |

### Network Reinforcement

When a CognitiveObject is activated, reinforcement propagates to connected nodes:

```
reinforcement = base_network_reinforcement × pathway_strength
pathway_strength = (1 / hop_distance) × edge_confidence × activated_node_salience
```

### Structural Boosts

Nodes with 3+ high-confidence connections receive a +0.15 structural importance boost.

## Decay and Forgetting

### Decay Rates

| Condition | Decay Rate | Applied When |
|-----------|------------|--------------|
| **Base Decay** | -0.02/week | All nodes |
| **No Reference** | -0.1/week | No activity for 14+ days |
| **Orphaned** | -0.2/week | No connections |
| **Low Confidence** | -0.15/week | Confidence < 0.3 |

### Deletion Criteria

Nodes are deleted when:
- Salience < 0.1 AND no connections for 30+ days
- Salience < 0.05 AND confidence < 0.3 AND no activity for 60+ days
- Explicitly dismissed with salience < 0.2

### Connection-Based Resistance

Well-connected nodes resist decay:
```
decay_resistance = min(0.8, connection_count × 0.1)
final_decay = base_decay × (1 - decay_resistance)
```

## Configuration

### Default Configuration

```python
from graphiti_extend import SalienceConfig

config = SalienceConfig()

# Direct activation values
config.CONVERSATION_MENTION = 0.3
config.DUPLICATE_FOUND = 0.25
config.REASONING_USAGE = 0.2
config.STRUCTURAL_BOOST = 0.15
config.NETWORK_PROXIMITY = 0.1
config.CONTRADICTION_INVOLVEMENT = 0.1

# Network reinforcement
config.BASE_NETWORK_REINFORCEMENT = 0.05
config.MAX_HOP_DISTANCE = 2

# Decay rates
config.BASE_DECAY_RATE = 0.02
config.NO_REFERENCE_DECAY = 0.1
config.ORPHANED_DECAY = 0.2
config.LOW_CONFIDENCE_DECAY = 0.15

# Deletion thresholds
config.MIN_SALIENCE_THRESHOLD = 0.1
config.DELETION_SALIENCE_THRESHOLD = 0.05
```

### Custom Configuration

```python
# Create custom configuration
custom_config = SalienceConfig()
custom_config.CONVERSATION_MENTION = 0.4  # Higher boost for mentions
custom_config.BASE_DECAY_RATE = 0.01      # Slower decay

# Use with custom salience manager
salience_manager = SalienceManager(driver, custom_config)
```

## Manual Operations

### Manual Decay Cycle

```python
from graphiti_extend.salience.manager import SalienceManager
from neo4j import AsyncGraphDatabase

driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
salience_manager = SalienceManager(driver)

# Run decay cycle
stats = await salience_manager.run_decay_cycle(
    group_ids=["user_123"],
    batch_size=100
)

print(f"Processed: {stats['processed']}")
print(f"Decayed: {stats['decayed']}")
print(f"Deleted: {stats['deleted']}")
```

### Direct Salience Updates

```python
# Update salience for specific nodes
updated_nodes = await salience_manager.update_direct_salience(
    nodes=cognitive_nodes,
    trigger_type='conversation_mention',
    episode_timestamp=datetime.now()
)

# Apply network reinforcement
reinforced_count = await salience_manager.propagate_network_reinforcement(
    activated_nodes=cognitive_nodes,
    group_ids=["user_123"]
)

# Apply structural boosts
boosted_nodes = await salience_manager.apply_structural_boosts(cognitive_nodes)
```

## Monitoring and Analytics

### Salience Distribution Query

```cypher
MATCH (n:Entity)
WHERE 'CognitiveObject' IN n.labels
RETURN 
  count(n) as total_nodes,
  avg(n.salience) as avg_salience,
  min(n.salience) as min_salience,
  max(n.salience) as max_salience,
  percentileCont(n.salience, 0.5) as median_salience
```

### High Salience Concepts

```cypher
MATCH (n:Entity)
WHERE 'CognitiveObject' IN n.labels AND n.salience > 0.8
RETURN n.name, n.salience, n.confidence
ORDER BY n.salience DESC
LIMIT 10
```

### Decay Candidates

```cypher
MATCH (n:Entity)
WHERE 'CognitiveObject' IN n.labels 
  AND n.salience < 0.2
  AND duration.between(n.last_salience_update, datetime()).days > 30
RETURN n.name, n.salience, n.last_salience_update
ORDER BY n.salience ASC
```

## Best Practices

### 1. Regular Monitoring

- Monitor salience distribution regularly
- Check for orphaned nodes
- Review deletion statistics

### 2. Configuration Tuning

- Start with default configuration
- Adjust based on your use case
- Monitor the effects of changes

### 3. Scheduled Maintenance

- Run decay cycles every 4-6 hours
- Use smaller batch sizes for large datasets
- Monitor performance impact

### 4. Group Management

- Use group_ids to isolate different users/contexts
- Apply different configurations per group if needed
- Monitor cross-group interactions

## Troubleshooting

### Common Issues

**High Memory Usage**
- Reduce batch size in decay cycles
- Increase decay frequency
- Check for orphaned nodes

**Slow Performance**
- Optimize Neo4j indexes
- Reduce network reinforcement hop distance
- Use smaller batch sizes

**Unexpected Deletions**
- Review deletion thresholds
- Check decay rates
- Monitor connection patterns

### Debug Queries

**Check Salience Updates**
```cypher
MATCH (n:Entity)
WHERE 'CognitiveObject' IN n.labels
  AND n.last_salience_update > datetime() - duration('PT1H')
RETURN n.name, n.salience, n.last_salience_update
ORDER BY n.last_salience_update DESC
```

**Find Disconnected Nodes**
```cypher
MATCH (n:Entity)
WHERE 'CognitiveObject' IN n.labels
  AND NOT (n)--()
RETURN n.name, n.salience, n.created_at
```

## Advanced Usage

### Custom Trigger Types

```python
# Add custom trigger types
await salience_manager.update_direct_salience(
    nodes=nodes,
    trigger_type='custom_importance',  # Custom trigger
    episode_timestamp=datetime.now()
)
```

### Batch Operations

```python
# Process multiple groups
for group_id in user_groups:
    stats = await salience_manager.run_decay_cycle(
        group_ids=[group_id],
        batch_size=50
    )
    print(f"Group {group_id}: {stats}")
```

### Integration with Other Systems

```python
# Integrate with external analytics
class AnalyticsSalienceManager(SalienceManager):
    async def run_decay_cycle(self, **kwargs):
        stats = await super().run_decay_cycle(**kwargs)
        # Send stats to analytics system
        await self.send_to_analytics(stats)
        return stats
```

## Performance Considerations

- **Batch Size**: Start with 100, adjust based on performance
- **Frequency**: Every 4 hours is recommended for most use cases
- **Indexing**: Ensure proper Neo4j indexes on salience and timestamps
- **Monitoring**: Track decay cycle duration and resource usage

## Migration Guide

If you're adding salience to an existing system:

1. **Backup your data**
2. **Add default salience values** to existing CognitiveObjects
3. **Start with conservative decay rates**
4. **Monitor the system** for a few cycles
5. **Adjust configuration** based on observations

```cypher
// Add default salience to existing nodes
MATCH (n:Entity)
WHERE 'CognitiveObject' IN n.labels AND n.salience IS NULL
SET n.salience = 0.5, n.last_salience_update = datetime()
```

This completes the comprehensive salience system implementation following the FCS Saliency Final specification!

# Brain-like Memory Characteristics

This system mimics human memory by:

1. **Strengthening frequently used concepts** (direct activation)
2. **Reinforcing related ideas** when nearby concepts are activated (network effects)
3. **Preserving well-connected knowledge** (structural importance)
4. **Gradually forgetting unused information** (temporal decay)
5. **Completely losing orphaned thoughts** (deletion mechanism)
6. **Prioritizing confident beliefs** for retention (confidence weighting)

The result is a dynamic memory system where important, well-connected, frequently-referenced concepts become more salient over time, while irrelevant or contradicted ideas naturally fade from memory.

## Testing the Salience System

### Running the Test Suite

The salience system includes a comprehensive test suite that covers all major functionality:

```bash
# Run all salience tests
cd /path/to/memduo-remake
python -m pytest graphiti_extend/tests/test_salience_system.py -v

# Run specific test
python -m pytest graphiti_extend/tests/test_salience_system.py::TestSalienceManager::test_direct_salience_update_duplicate_found -v

# Run with detailed output
python -m pytest graphiti_extend/tests/test_salience_system.py -v -s
```

### Test Coverage

The test suite covers:

#### **Direct Salience Updates**
- `test_direct_salience_update_duplicate_found` - Tests +0.25 salience for duplicates
- `test_direct_salience_update_conversation_mention` - Tests +0.3 salience for mentions
- `test_salience_cap_at_max` - Ensures salience caps at 1.0
- `test_non_cognitive_object_unchanged` - Regular entities unchanged

#### **Network Reinforcement**
- `test_network_reinforcement` - Tests pathway reinforcement calculations
- Tests 1-hop and 2-hop propagation with edge confidence weighting
- Verifies connected nodes receive appropriate boosts

#### **Structural Importance**
- `test_structural_boost` - Tests +0.15 boost for well-connected nodes (3+ high-confidence connections)
- `test_no_structural_boost_insufficient_connections` - No boost for poorly connected nodes

#### **Decay and Cleanup**
- `test_decay_calculation` - Tests normal decay with connection resistance
- `test_decay_calculation_orphaned` - Tests accelerated decay for orphaned nodes
- `test_should_delete_orphaned_node` - Tests deletion criteria
- `test_should_not_delete_well_connected_node` - Protects important nodes

#### **Reinforcement Weight Calculation**
- `test_reinforcement_weight_calculation` - Tests multiplier calculations
- Verifies connectivity, recency, and confidence multipliers

#### **System Integration**
- `test_run_decay_cycle` - Tests complete decay processing
- `test_multiple_triggers_same_node` - Tests cumulative salience updates
- `test_empty_node_list_handling` - Edge case handling

### Manual Testing Examples

#### Test Salience Updates
```python
from graphiti_extend.salience.manager import SalienceManager, SalienceConfig
from graphiti_core.nodes import EntityNode

# Create test node
node = EntityNode(
    uuid="test-uuid",
    name="Test Concept",
    labels=["Entity", "CognitiveObject"],
    attributes={"confidence": 0.7, "salience": 0.5}
)

# Apply duplicate detection update
manager = SalienceManager(driver)
updated_nodes = await manager.update_direct_salience([node], 'duplicate_found')
print(f"Salience after duplicate: {updated_nodes[0].attributes['salience']}")
```

#### Test Network Reinforcement
```python
# Test network propagation
count = await manager.propagate_network_reinforcement([node])
print(f"Reinforced {count} connected nodes")
```

#### Test Decay Calculation
```python
# Test decay amount
decay = await manager._calculate_decay_amount(
    current_salience=0.8,
    confidence=0.7,
    days_since_update=14,
    connection_count=3
)
print(f"Decay amount: {decay}")
```

### Expected Test Results

When tests pass, you should see:
- Direct salience updates working correctly with proper multiplier calculations
- Network reinforcement propagating to connected nodes
- Structural boosts applied to well-connected nodes
- Decay calculations respecting connection resistance
- Proper deletion criteria protecting important nodes
- Salience values capped at 1.0 maximum

### Debugging Failed Tests

If tests fail:

1. **Check Mock Dependencies**: Ensure Neo4j driver mocks are properly configured
2. **Verify Calculations**: Check multiplier calculations match expected formulas
3. **Database State**: For integration tests, ensure clean database state
4. **Async Handling**: Verify all async operations are properly awaited

### Performance Testing

For performance testing with real database:

```python
import asyncio
from neo4j import AsyncGraphDatabase

async def test_salience_performance():
    driver = AsyncGraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    manager = SalienceManager(driver)
    
    # Create test nodes
    nodes = [create_test_cognitive_object(i) for i in range(100)]
    
    # Time salience updates
    start = time.time()
    await manager.update_direct_salience(nodes, 'duplicate_found')
    duration = time.time() - start
    
    print(f"Updated {len(nodes)} nodes in {duration:.3f}s")
    await driver.close()
```

This testing framework ensures the salience system works correctly across all scenarios and provides confidence in brain-like memory behavior. 