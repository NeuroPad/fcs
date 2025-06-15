# FCS Salience Mechanism: Brain-like Reinforcement System

## Overview

Salience represents the **mental activation strength** of a cognitive object (belief/idea) within the system. It mimics how human memory reinforces frequently accessed, well-connected concepts while allowing unused ideas to fade over time.

**Salience Range**: 0.0 to 1.0  
**Initial Value**: 0.5 (neutral activation)  
**Purpose**: Prioritize beliefs during recall, contradiction detection, summarization, and arbitration

## Core Salience Principles

### 1. **Direct Activation** (Primary Reinforcement)
When a CognitiveObject is explicitly mentioned, referenced, or found as a duplicate during episode processing.

### 2. **Network Pathway Reinforcement** (Secondary Reinforcement) 
When connected CognitiveObjects are activated, reinforcement propagates through the network, strengthening related concepts.

### 3. **Structural Importance** (Passive Reinforcement)
Well-connected nodes in the belief graph gain passive salience boosts due to their structural significance.

### 4. **Temporal Decay** (Forgetting Mechanism)
Unused concepts naturally fade over time, with orphaned and low-confidence nodes decaying faster.

## Salience Update Algorithm

### Direct Activation Triggers & Values

| Trigger Event | Salience Increase | Context |
|---------------|------------------|---------|
| **Mentioned in conversation** | +0.3 | Explicit reference in episode content |
| **Found as duplicate** | +0.25 | Node resolved to existing entity |
| **Used in reasoning/inference** | +0.2 | Part of contradiction detection or arbitration |
| **Connected to high-confidence cluster** | +0.15 | 3+ connections with confidence > 0.75 |
| **Network proximity activation** | +0.1 | Within 1-2 hops of activated nodes |
| **Contradiction involvement** | +0.1 | Direct contradiction detected |

**Cap**: All increases are additive but capped at 1.0

### Network Pathway Reinforcement Algorithm

```
For each activated CognitiveObject:
  1. Find all connected CognitiveObjects within 2 hops
  2. For each connected node at distance D:
     pathway_strength = (1 / D) × edge_confidence × activated_node_salience
     reinforcement = base_network_reinforcement × pathway_strength
     connected_node.salience += reinforcement
  3. Apply connectivity multiplier:
     if connected_node has 3+ high-confidence connections:
       additional_boost = +0.15
```

### Reinforcement Weight Calculation

```
reinforcement_weight = base_increment × connectivity_multiplier × recency_multiplier × confidence_multiplier

Where:
- base_increment = values from trigger table above
- connectivity_multiplier = 1 + (connection_count × 0.05)
- recency_multiplier = 1.5 if last_active < 1_day, 1.0 if < 1_week, 0.8 if > 1_week
- confidence_multiplier = 0.7 + (node_confidence × 0.3)
```

## Implementation Locations (graphiti_extend only)

### Primary Location: Episode Processing Pipeline
**File**: `graphiti_extend/extended_graphiti.py`  
**Function**: `add_episode_with_contradictions()`

#### Implementation Points:

1. **After Node Resolution** (Direct Activation):
```
# After: (nodes, uuid_map), extracted_edges = await semaphore_gather(...)
# Identify nodes that were found as duplicates
# Apply direct activation reinforcement (+0.25 or +0.3)
```

2. **After Hydration** (Network Reinforcement):
```
# After: hydrated_nodes = await extract_attributes_from_nodes(...)
# Apply network pathway reinforcement to connected CognitiveObjects
# Update structural importance for well-connected nodes
```

3. **During Contradiction Detection** (Reasoning Activation):
```
# When contradictions are detected
# Apply +0.2 for reasoning/inference usage
# Apply +0.1 for contradiction involvement
```

### Secondary Location: New Salience Manager Module
**File**: `graphiti_extend/salience/manager.py` (new module)

Functions:
- `update_direct_salience()` - Handle direct activation
- `propagate_network_reinforcement()` - Handle pathway reinforcement  
- `apply_structural_boosts()` - Handle connectivity-based increases
- `run_decay_cycle()` - Handle temporal decay and cleanup

## Temporal Decay & Forgetting Algorithm

### Decay Triggers & Rates

| Condition | Decay Rate | Frequency |
|-----------|------------|-----------|
| **No reference in 14 days** | -0.1 | Weekly check |
| **No high-salience connections** | -0.05 | Weekly check |
| **Orphaned node (0 connections)** | -0.2 | Weekly check |
| **Low confidence + low activity** | -0.15 | Weekly check |
| **Base temporal decay** | -0.02 | Weekly check |

### Connection-Based Decay Resistance

```
decay_resistance = min(0.8, connection_count × 0.1)
final_decay = base_decay × (1 - decay_resistance)

# Well-connected nodes decay slower
# Orphaned nodes decay at full rate
```

### Forgetting & Deletion Algorithm

```
Weekly Decay Cycle:
1. Query all CognitiveObjects in batches
2. For each node:
   a. Calculate time since last_updated
   b. Check connection count and types
   c. Apply appropriate decay rates
   d. Mark for deletion if criteria met
3. Delete nodes that meet deletion criteria
4. Update remaining nodes in batch

Deletion Criteria:
- salience < 0.1 AND no connections for 30+ days
- salience < 0.05 AND confidence < 0.3 AND no activity for 60+ days  
- Explicitly marked as "dismissed" with salience < 0.2
```

### Decay Implementation Strategy

#### Phase 1: Real-time Decay (During Episode Processing)
```
# In add_episode_with_contradictions()
# Apply decay to nodes based on time since last update
# Quick decay check for recently accessed nodes
```

#### Phase 2: Batch Decay (Background Process)
```
# Weekly/daily background job
# Process all CognitiveObjects for systematic decay
# Handle deletion of forgotten concepts
```

#### Phase 3: Smart Cleanup
```
# Identify and clean up:
# - Orphaned nodes with no connections
# - Low-confidence, low-salience clusters
# - Contradicted nodes that were never resolved
```

## Configuration Parameters

```python
salience_config = {
    # Direct activation values
    "conversation_mention": 0.3,
    "duplicate_found": 0.25, 
    "reasoning_usage": 0.2,
    "structural_boost": 0.15,
    "network_proximity": 0.1,
    "contradiction_involvement": 0.1,
    
    # Network reinforcement
    "base_network_reinforcement": 0.05,
    "max_hop_distance": 2,
    "connectivity_boost_factor": 0.05,
    
    # Temporal factors
    "recency_boost_recent": 1.5,    # < 1 day
    "recency_boost_normal": 1.0,    # < 1 week
    "recency_boost_old": 0.8,       # > 1 week
    
    # Decay rates
    "base_decay_rate": 0.02,        # per week
    "no_reference_decay": 0.1,      # 14+ days
    "orphaned_decay": 0.2,          # no connections
    "low_confidence_decay": 0.15,   # confidence < 0.3
    
    # Deletion thresholds
    "min_salience_threshold": 0.1,
    "deletion_salience_threshold": 0.05,
    "orphan_deletion_days": 30,
    "low_confidence_deletion_days": 60,
    
    # Limits
    "max_salience": 1.0,
    "min_salience": 0.0,
    "structural_connection_threshold": 3,
    "high_confidence_threshold": 0.75
}
```

## Brain-like Memory Characteristics

This system mimics human memory by:

1. **Strengthening frequently used concepts** (direct activation)
2. **Reinforcing related ideas** when nearby concepts are activated (network effects)
3. **Preserving well-connected knowledge** (structural importance)
4. **Gradually forgetting unused information** (temporal decay)
5. **Completely losing orphaned thoughts** (deletion mechanism)
6. **Prioritizing confident beliefs** for retention (confidence weighting)

The result is a dynamic memory system where important, well-connected, frequently-referenced concepts become more salient over time, while irrelevant or contradicted ideas naturally fade from memory.
