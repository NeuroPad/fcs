# Graphiti Extensions and FCS Implementation

This project extends the `graphiti_core` library with additional functionality and implements the Fluid Cognitive Scaffolding (FCS) system based on Graphiti.

## Project Structure

```
.
├── graphiti_core/         # Original graphiti_core library (not modified)
├── graphiti_extend/       # Extensions to graphiti_core
│   ├── __init__.py
│   ├── custom_edges.py    # Custom edge types
│   ├── custom_triplet.py  # Custom triplet implementation
│   ├── enhanced_graphiti.py # Enhanced Graphiti class
│   └── README.md
├── fcs_core/              # FCS implementation
│   ├── __init__.py
│   ├── cognitive_objects.py # CO implementation
│   ├── contradiction_detector.py # Contradiction detection
│   ├── fcs.py            # Main FCS class
│   └── README.md
└── example_usage.py       # Example script demonstrating usage
```

## Features

### Graphiti Extensions

The `graphiti_extend` module adds the following features to `graphiti_core`:

1. **Custom Edge Types**: Additional edge types like REINFORCES, CONTRADICTS, EXTENDS, SUPPORTS, ELABORATES
2. **Enhanced Episode Addition**: Ability to add episodes with default values for salience, confidence, and flags
3. **Custom Triplet Creation**: Functions to create custom edge types between entity nodes

### FCS Core

The `fcs_core` module implements the Fluid Cognitive Scaffolding system:

1. **Cognitive Objects**: Basic units of idea representation with properties like content, type, confidence, salience, etc.
2. **Session State**: Maintains the state of all active COs, tracked ideas, contradictions, etc.
3. **Contradiction Detection**: Identifies conflicts between cognitive objects
4. **External Reference Integration**: Adds and manages external references

## Key Principles

1. The implementation extends `graphiti_core` without modifying its original code
2. The FCS implementation follows the specifications in the FCS documentation
3. All extensions are modular and can be used independently

## Usage

See individual README files in each directory for specific usage details:

- [Graphiti Extensions README](graphiti_extend/README.md)
- [FCS Core README](fcs_core/README.md)

The `example_usage.py` script demonstrates how to use both modules together.

## Requirements

- Python 3.10 or higher
- Neo4j 5.21 or higher
- OpenAI API key or compatible alternative
- All dependencies from `graphiti_core`

## Example

```python
# Using EnhancedGraphiti
from graphiti_extend.enhanced_graphiti import EnhancedGraphiti

graphiti = EnhancedGraphiti(uri, user, password)
result = await graphiti.add_episode_with_defaults(
    name="Example",
    episode_body="Content",
    source_description="Source",
    reference_time=datetime.now()
)

# Using FCS
from fcs_core.fcs import FCS

fcs = FCS(uri, user, password)
cos, contradictions = await fcs.add_user_input(
    content="User input content"
)
```

Run the example script to see a complete demonstration:

```
python example_usage.py
``` 