## Understanding Salience as Brain-like Reinforcement

**Salience = How strongly an idea is reinforced in memory through repeated activation and connected pathways**

In a human brain:
- Ideas get stronger when directly recalled
- Ideas ALSO get stronger when related concepts are activated (pathway reinforcement)
- Well-connected ideas become more salient because they have more "routes" to activation
- The strength of connections matters - stronger connections provide more reinforcement

## Revised Brain-like Salience Algorithm

### Core Reinforcement Mechanisms

#### 1. **Direct Activation Reinforcement**
```
When a CognitiveObject is found as a duplicate:
- This is direct activation of the concept
- Reinforcement depends on:
  - Current salience level (diminishing returns)
  - Time since last activation (recency effect)
  - Number of existing connections (well-connected ideas reinforce more)
```

#### 2. **Network Pathway Reinforcement** (The Missing Piece)
```
When ANY connected CognitiveObject is activated:
- Find all CognitiveObjects within N hops (e.g., 2-3 hops)
- For each connected node:
  - Calculate pathway strength = (1 / hop_distance) × edge_strength
  - Apply reinforcement = base_reinforcement × pathway_strength × connected_node_salience
- Well-connected concepts get reinforced more when their "neighborhood" is active
```

#### 3. **Temporal Decay with Connection Resistance**
```
Over time, salience decays, but:
- Highly connected nodes decay slower (they have more "support")
- Decay resistance = 1 - (connection_count / max_connections)
- Final decay = base_decay × decay_resistance
```

### What Should `reinforcement_weight` Be?

**`reinforcement_weight` = A dynamic value that represents the strength of reinforcement for a specific activation event**

#### Calculation:
```
reinforcement_weight = base_weight × connectivity_multiplier × recency_multiplier × salience_multiplier

Where:
- base_weight = 0.1 (baseline reinforcement)
- connectivity_multiplier = 1 + (connection_count × 0.05) [more connections = more reinforcement]
- recency_multiplier = 1.5 if last_active < 1_day, 1.0 if < 1_week, 0.7 if > 1_week
- salience_multiplier = 0.8 + (current_salience × 0.4) [higher salience ideas reinforce more]
```

### Where to Apply This (Only in `graphiti_extend`)

#### **Primary Location: Extended Episode Processing**
- **File**: `graphiti_extend/extended_graphiti.py`
- **Function**: `add_episode_with_contradictions()`
- **When**: After node resolution, during hydration phase
- **What**: 
  1. Identify which nodes were found as duplicates (direct activation)
  2. Find all connected CognitiveObjects within 2-3 hops
  3. Apply reinforcement to the network

#### **Implementation Points:**

1. **After Node Resolution** (in `extended_graphiti.py`):
```
# After this line in add_episode_with_contradictions():
(nodes, uuid_map), extracted_edges = await semaphore_gather(...)

# Apply salience updates based on which nodes were duplicates
# (extracted_uuid != resolved_uuid means it was a duplicate)
```

2. **After Hydration** (in `extended_graphiti.py`):
```
# After this line:
hydrated_nodes = await extract_attributes_from_nodes(...)

# Apply network reinforcement to connected CognitiveObjects
```

### Detailed Network Reinforcement Logic

#### **Step 1: Identify Activated Nodes**
```
activated_nodes = []
for extracted, resolved in zip(extracted_nodes, resolved_nodes):
    if extracted.uuid != resolved.uuid:  # Was a duplicate
        activated_nodes.append(resolved)
```

#### **Step 2: Find Connected Network**
```
For each activated_node:
    1. Query database for all edges connected to this node
    2. Follow edges to find CognitiveObjects within 2-3 hops
    3. Calculate pathway strength for each connected node
    4. Build reinforcement map: {node_uuid: reinforcement_amount}
```

#### **Step 3: Apply Network Reinforcement**
```
For each node in reinforcement_map:
    1. Calculate reinforcement_weight based on:
       - Connection strength to activated node
       - Current salience of the node
       - Number of connections the node has
    2. Update salience: new_salience = current + reinforcement_weight
    3. Track reinforcement event with timestamp
```

### Configuration Parameters
```
salience_config = {
    "base_reinforcement_weight": 0.1,
    "network_hop_limit": 2,
    "connectivity_boost_factor": 0.05,
    "recency_boost_recent": 1.5,  # < 1 day
    "recency_boost_normal": 1.0,  # < 1 week  
    "recency_boost_old": 0.7,     # > 1 week
    "max_salience": 1.0,
    "min_salience": 0.1,
    "decay_rate_base": 0.02,      # per week
    "connection_decay_resistance": 0.05
}
```

### Key Insight: Why This is Brain-like

In your brain:
- When you think about "Python programming", it strengthens that concept
- BUT it ALSO strengthens connected concepts: "coding", "software development", "machine learning"
- The more connections a concept has, the more it gets reinforced when related topics come up
- This creates a reinforcement network where popular, well-connected ideas become more salient over time

This algorithm captures that network effect by:
1. Directly reinforcing mentioned concepts
2. Propagating reinforcement through the connection network
3. Making well-connected concepts more resistant to decay
4. Creating a positive feedback loop for important concepts