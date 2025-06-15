# Salience System Logging Demonstration

## Overview

The salience system now includes comprehensive logging that shows detailed before/after states of CognitiveObject nodes when their salience values are updated. This provides complete transparency into how the brain-like reinforcement learning system works.

## What Gets Logged

### 🧠 Direct Salience Updates
- **Trigger type**: Why the salience is being updated (duplicate_found, reasoning_usage, conversation_mention, contradiction_involvement)
- **Base increment**: The base amount for this trigger type
- **Reinforcement weight**: Calculated weight including connectivity, confidence, and recency factors
- **Before/after states**: Complete node information before and after the update
- **Net increase**: Exact amount the salience increased

### 🏗️ Structural Boosts
- **Connection analysis**: Shows high-confidence connection counts
- **Boost qualification**: Whether nodes meet the threshold for structural importance
- **Before/after states**: Complete node information for boosted nodes

### 🌐 Network Reinforcement
- **Propagation details**: Which nodes triggered the reinforcement and which nodes receive it
- **Pathway analysis**: Shows the network connections and reinforcement calculations
- **Batch updates**: Complete before/after states for all connected nodes that get reinforced

## Demo Script

Run the demonstration script:

```bash
python -m graphiti_extend.demo_salience_logging
```

This shows:

1. **Initial states** of sample CognitiveObject nodes
2. **Duplicate detection** salience update with full logging
3. **Reasoning usage** salience update with full logging  
4. **Structural boost** analysis and application
5. **Conversation mention** salience update with full logging
6. **Final states** showing the cumulative changes

## Sample Output

Each salience update shows:

```
🧠 SALIENCE UPDATE: Direct Activation Trigger = 'duplicate_found'
================================================================================

🔍 BEFORE UPDATE:
   Node Name: User loves chocolate ice cream
   Node UUID: demo-user-loves-chocolate-ice-cream-5329855200
   Current Salience: 0.400
   Node Type: CognitiveObject
   Summary: The user has expressed a strong preference for chocolate flavored ice cream
   Confidence: 0.800
   Full Attributes: {'entity_type': 'CognitiveObject', 'salience': 0.4, 'confidence': 0.8}

✅ AFTER UPDATE:
   Trigger Type: duplicate_found
   Base Increment: +0.250
   Reinforcement Weight: +0.235
   Salience Change: 0.400 → 0.635
   Net Increase: +0.235
   New Salience: 0.635
   Updated Attributes: {'entity_type': 'CognitiveObject', 'salience': 0.635, 'confidence': 0.8}
   Full Updated Node:
     - UUID: demo-user-loves-chocolate-ice-cream-5329855200
     - Name: User loves chocolate ice cream
     - Type: CognitiveObject
     - Summary: The user has expressed a strong preference for chocolate flavored ice cream
     - Labels: ['Entity', 'CognitiveObject']
     - Group ID: demo_group
     - All Attributes: {'entity_type': 'CognitiveObject', 'salience': 0.635, 'confidence': 0.8}
```

## Production Usage

In your actual system, these logs will appear during:

1. **Episode processing** - When adding new episodes that trigger salience updates
2. **Contradiction detection** - When nodes are used in reasoning
3. **Duplicate resolution** - When existing nodes are found and reinforced
4. **Network propagation** - When connected nodes receive reinforcement

## Client Benefits

This logging demonstrates:

- **Transparency**: Exact calculations and reasons for each salience change
- **Brain-like behavior**: How frequently mentioned concepts become more salient
- **Network effects**: How connected ideas reinforce each other
- **Complete audit trail**: Full before/after states for accountability
- **Real-time insight**: See the reinforcement learning in action

## Configuration

The logging is controlled by print statements in:
- `graphiti_extend/salience/manager.py` - Main salience update methods
- All updates show complete node states and calculation details

To copy the output for your client, simply run the demo and copy the console output. The formatting is designed to be readable and comprehensive. 