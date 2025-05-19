# Fluid Cognitive Scaffolding (FCS) Core

This module implements the core functionality of the Fluid Cognitive Scaffolding (FCS) system using `graphiti_core` and `graphiti_extend`. FCS is a persistent, voice-based cognitive system that remembers what the user says and uses that memory to help them think better.

## Features

### Cognitive Objects (COs)

Cognitive Objects are the basic units of idea representation in FCS:

- Each CO includes properties like id, content, type, confidence, salience, flags, etc.
- CO types include: idea, contradiction, reference, system_note
- Sources include: user, external, system
- Flags include: tracked, contradiction, external, unverified, dismissed

### Contradiction Detection

The module includes a contradiction detector that:

- Identifies contradictions between cognitive objects
- Only considers tracked or flagged COs with sufficient confidence
- Creates contradiction COs when conflicts are found
- Adds CONTRADICTS edges to the knowledge graph

### FCS Core System

The main `FCS` class integrates all components:

- Uses `EnhancedGraphiti` from the `graphiti_extend` module
- Tracks user inputs and external references
- Maintains a session state with active COs, tracked ideas, etc.
- Detects contradictions between new and existing COs
- Creates appropriate edges in the knowledge graph

## Usage

```python
from fcs_core.fcs import FCS

# Initialize FCS
fcs = FCS(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)

# Add user input
cos, contradictions = await fcs.add_user_input(
    content="I believe exercise is beneficial for mental health.",
    group_id="fcs_example"
)

# Add another potentially contradicting input
cos2, contradictions2 = await fcs.add_user_input(
    content="I find that exercise makes me feel more anxious and stressed.",
    group_id="fcs_example"
)

# Add an external reference
ext_cos, ext_contradictions = await fcs.add_external_reference(
    content="Research indicates that regular physical activity can reduce anxiety and depression.",
    source_url="https://example.com/research",
    title="Effects of Exercise on Mental Health",
    authors=["Dr. Smith", "Dr. Johnson"],
    abstract="This study examines the relationship between physical activity and mental health.",
    group_id="fcs_example"
)

# Reset the session state when done
fcs.reset()

# Close the connection
await fcs.close()
```

See the `example_usage.py` script for a complete demonstration. 