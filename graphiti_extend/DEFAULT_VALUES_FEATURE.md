# Default Values for Entity Types

## Overview

The `graphiti_extend` package now supports automatic application of default values to new entity nodes based on their entity type definitions. This feature ensures that new nodes are created with consistent default attributes while preserving the existing values of duplicate/existing nodes.

## Key Features

- ✅ **Automatic default application**: Default values are automatically applied to new nodes during episode processing
- ✅ **Selective application**: Only applies to NEW nodes, never overwrites existing node attributes
- ✅ **Type-based**: Default values are applied based on the entity type (e.g., CognitiveObject)
- ✅ **Pydantic integration**: Leverages Pydantic field defaults from your entity type models
- ✅ **Zero configuration**: Works out of the box with existing `ExtendedGraphiti` usage

## How It Works

### 1. Entity Type Definition

First, define your entity types with default values using Pydantic:

```python
from pydantic import BaseModel, Field
from typing import List

class CognitiveObject(BaseModel):
    """Cognitive object with default values."""
    confidence: float = Field(default=0.7, description="Confidence level")
    salience: float = Field(default=0.5, description="Salience level")
    type: str = Field(default="idea", description="Type of cognitive object")
    flags: List[str] = Field(default_factory=list, description="Flags")
    # ... other fields
```

### 2. Episode Processing

When processing episodes with `ExtendedGraphiti`, the system:

1. **Extracts entities** from episode content using LLM
2. **Resolves duplicates** by checking against existing entities  
3. **Applies default values** to NEW entities only
4. **Hydrates nodes** with full attributes
5. **Saves to database** with complete information

### 3. New vs Existing Node Detection

The system determines if a node is new or existing by comparing UUIDs:

- **New node**: `extracted_uuid == resolved_uuid` (no duplicate found)
- **Existing node**: `extracted_uuid != resolved_uuid` (duplicate found, merged with existing)

## Usage

### Basic Usage

```python
from graphiti_extend import ExtendedGraphiti
from fcs_core.models import CognitiveObject

# Initialize ExtendedGraphiti
graphiti = ExtendedGraphiti(
    uri="bolt://localhost:7687",
    user="neo4j", 
    password="password"
)

# Define entity types with defaults
entity_types = {"CognitiveObject": CognitiveObject}

# Process episode - defaults will be applied automatically
result = await graphiti.add_episode_with_contradictions(
    name="User Message",
    episode_body="I really love Python programming",
    source_description="Chat message",
    reference_time=datetime.now(),
    entity_types=entity_types,  # This enables default values
    group_id="user123"
)
```

### What Happens

For a message like "I really love Python programming":

1. **LLM extracts**: Entity "loves Python programming" with labels ["Entity", "CognitiveObject"]
2. **System checks**: Is this a duplicate of an existing entity?
3. **If NEW**: Applies defaults `confidence=0.7`, `salience=0.5`, `flags=[]`, etc.
4. **If EXISTING**: Preserves existing values like `confidence=0.9`, `salience=0.8`
5. **Saves to database**: With complete attribute set

## Current Default Values for CognitiveObject

Based on the updated `CognitiveObject` model, these defaults are automatically applied:

```python
{
    'confidence': 0.7,          # How sure the system is about this idea
    'salience': 0.5,            # How central/important this idea is
    'flags': [],                # Optional flags like ['verified', 'tracked']
    'parent_ids': [],           # UUIDs of parent cognitive objects
    'child_ids': [],            # UUIDs of child cognitive objects  
    'match_history': [],        # UUIDs of semantically similar objects
    'arbitration_score': None,  # Score from arbitration process
    'linked_refs': [],          # External references or URLs
    'generated_from': []        # UUIDs used to construct this object
}
```

## Example Scenarios

### Scenario 1: New User Preference

**Input**: "I love jazz music"

**Result**: 
- New CognitiveObject node created
- `confidence: 0.7`, `salience: 0.5` applied automatically
- Node saved with complete default attributes

### Scenario 2: Updating Existing Preference  

**Input**: "I love jazz music" (duplicate of existing preference)

**Result**:
- Existing node found (e.g., with `confidence: 0.9`, `salience: 0.8`)
- NO defaults applied - existing values preserved
- Node content may be updated, but confidence/salience remain at 0.9/0.8

### Scenario 3: Non-CognitiveObject Entity

**Input**: "The jazz festival" (extracted as generic Entity)

**Result**:
- New Entity node created
- NO defaults applied (not a CognitiveObject)
- Node saved with minimal attributes

## Integration Points

This feature integrates seamlessly with existing `ExtendedGraphiti` functionality:

- ✅ **Contradiction Detection**: Works with nodes that have default values
- ✅ **Search**: Default values are indexed and searchable
- ✅ **Edge Creation**: Nodes with defaults can participate in relationships
- ✅ **Memory Service**: FCS Memory Service automatically benefits from defaults

## Implementation Details

### Files Modified/Added

1. **`fcs_core/models.py`**: Updated `CognitiveObject` with default values
2. **`graphiti_extend/default_values_handler.py`**: New module for default value logic
3. **`graphiti_extend/extended_graphiti.py`**: Integrated default application into episode processing
4. **`graphiti_extend/__init__.py`**: Exported new functionality

### Key Functions

- `apply_default_values_to_new_nodes()`: Main function to apply defaults
- `_extract_default_values_from_model()`: Extracts defaults from Pydantic models  
- `_apply_default_values_to_node()`: Applies defaults to individual nodes

## Testing

Run the test suite to verify functionality:

```bash
# Unit tests
python graphiti_extend/test_default_values.py

# Comprehensive example
python graphiti_extend/example_default_values.py
```

## Benefits

1. **Consistency**: All new CognitiveObject nodes start with consistent defaults
2. **Data Quality**: No missing attributes for confidence/salience tracking
3. **Analytics**: Enables meaningful analysis of confidence/salience evolution
4. **Preservation**: Existing high-confidence nodes keep their values
5. **Flexibility**: Easy to add new entity types with their own defaults

## Future Enhancements

- [ ] **Dynamic defaults**: Defaults based on context or user patterns
- [ ] **Confidence evolution**: Automatic confidence updates based on reinforcement
- [ ] **Salience calculation**: Automatic salience updates based on mention frequency
- [ ] **Custom default providers**: User-defined functions for calculating defaults 