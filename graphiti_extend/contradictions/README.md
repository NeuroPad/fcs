# Contradiction Detection in Graphiti

This document explains how contradiction detection works in the Graphiti system, including the logic, implementation, and usage.

## Overview

Contradiction detection is a key feature that helps maintain consistency in the knowledge graph by identifying and tracking conflicting information. The system can detect various types of contradictions, including:

1. Preference changes (e.g., "I love vanilla" → "I hate vanilla")
2. Factual contradictions (e.g., "I work at Company A" → "I work at Company B")
3. Behavioral contradictions (e.g., "I exercise daily" → "I never exercise")

## How It Works

### 1. Contradiction Detection Process

When a new node is added to the graph, the system:

1. Identifies potentially contradictory existing nodes using semantic similarity
2. Analyzes the relationship between the new node and existing nodes
3. Determines if there is a genuine contradiction
4. Creates appropriate contradiction edges if needed

### 2. Types of Contradictions

The system recognizes several types of contradictions:

#### Preference Changes
- Changes in likes/dislikes
- Changes in preferences between options
- Changes in opinions or beliefs

#### Factual Contradictions
- Mutually exclusive factual claims
- Changes in factual information
- Inconsistent statements about the same subject

#### Behavioral Contradictions
- Changes in habits or routines
- Inconsistent behavioral patterns
- Changes in lifestyle choices

### 3. Contradiction Edges

When a contradiction is detected, the system creates a `CONTRADICTS` edge between the nodes. These edges contain:

- Source node (the new/contradicting node)
- Target node (the existing/contradicted node)
- Contradiction type
- Human-readable description
- Metadata about the contradiction

### 4. Contradiction Resolution

The system handles contradictions in several ways:

1. **Direct Contradictions**: When a new node directly contradicts an existing node
   ```
   Node A: "I love football"
   Node B: "I hate football"
   Edge: A --CONTRADICTS--> B
   ```

2. **Preference Changes**: When a preference changes without specifying an alternative
   ```
   Node A: "I love football"
   Node B: "I hate football"
   Edge: A --CONTRADICTS--> B
   ```

3. **Alternative Preferences**: When a preference changes with a specified alternative
   ```
   Node A: "I love football"
   Node B: "I prefer basketball over football"
   Edge: A --CONTRADICTS--> B
   ```

## Implementation Details

### Key Components

1. **ContradictionHandler**: Main class for detecting and processing contradictions
   - Handles contradiction detection logic
   - Creates contradiction edges
   - Generates human-readable messages

2. **Contradiction Models**:
   - `ContradictionDetectionResult`: Results of contradiction detection
   - `ContradictionType`: Types of contradictions
   - `ContradictionContext`: Context for contradiction processing

3. **Prompts**:
   - System prompt for contradiction detection
   - Examples and rules for identifying contradictions
   - Guidelines for handling different types of contradictions

### Code Structure

```
contradictions/
├── __init__.py
├── handler.py          # Main contradiction handling logic
├── models.py          # Contradiction-related models
├── prompts.py         # LLM prompts for contradiction detection
└── README.md          # This documentation
```

## Usage

### Basic Usage

```python
from graphiti_extend.contradictions import ContradictionHandler

# Initialize the handler
handler = ContradictionHandler(llm_client)

# Detect contradictions
result = await handler.detect_contradictions(
    new_node=new_node,
    existing_nodes=existing_nodes,
    episode=current_episode,
    previous_episodes=previous_episodes
)

# Process results
if result.contradictions_found:
    # Handle contradictions
    for edge in result.contradiction_edges:
        # Process contradiction edge
        pass
```

### Contradiction Types

The system recognizes these main contradiction types:

1. `preference_change`: Changes in preferences or opinions
2. `factual_contradiction`: Contradictory factual claims
3. `behavioral_contradiction`: Changes in behavior or habits

## Best Practices

1. **Contradiction Detection**:
   - Use semantic similarity to find potential contradictions
   - Consider context when analyzing contradictions
   - Handle both direct and indirect contradictions

2. **Edge Creation**:
   - Create clear, descriptive contradiction edges
   - Include relevant metadata
   - Maintain proper directionality (new → old)

3. **User Interaction**:
   - Generate clear, human-readable messages
   - Provide context for contradictions
   - Allow for exploration of contradictions

## Limitations

1. The system may not detect all types of contradictions
2. Some contradictions may require human judgment
3. Context-dependent contradictions may be challenging to detect
4. Temporal aspects of contradictions may need additional handling

## Future Improvements

1. Enhanced contradiction detection using more sophisticated models
2. Better handling of temporal contradictions
3. Improved context awareness
4. More sophisticated contradiction resolution strategies
5. Better integration with the salience system 