# Reasoning Nodes Feature

## Overview

The Reasoning Nodes feature tracks and displays the knowledge graph nodes that were accessed and used during the AI's reasoning process when responding to user queries. This provides transparency into how the AI arrived at its conclusions and which pieces of knowledge were most influential.

## Features

### Node Information Tracked
- **UUID**: Unique identifier of the knowledge node
- **Name**: Human-readable name of the node
- **Salience**: How important/central this node is (0.0 - 1.0)
- **Confidence**: How reliable/certain this node's information is (0.0 - 1.0)
- **Summary**: Brief description of the node's content
- **Node Type**: Category of knowledge (entity, concept, knowledge, etc.)
- **Usage Context**: How the node was used in reasoning (direct_match, semantic_similarity, etc.)

### Query Modes

#### Normal Mode (`mode=normal`)
- Uses traditional RAG (Retrieval-Augmented Generation)
- Does not track reasoning nodes
- Returns `reasoning_nodes: []`

#### Graph Mode (`mode=graph`)
- Uses knowledge graph search with node tracking
- Performs contradiction-aware search
- Returns detailed reasoning nodes information
- Stores reasoning process in memory

#### Combined Mode (`mode=combined`)
- Uses both RAG and graph search
- Combines responses from both approaches
- Returns reasoning nodes from graph search portion

## API Usage

### Chat Endpoint
```http
POST /chat/session/{session_id}/ask?mode=graph
Content-Type: application/json
Authorization: Bearer {token}

{
  "text": "What do you know about climate change?"
}
```

### Response Format
```json
{
  "answer": "Climate change refers to...",
  "sources": ["document1.pdf", "document2.pdf"],
  "memory_facts": "Retrieved 3 memory facts...",
  "reasoning_nodes": [
    {
      "uuid": "node-uuid-123",
      "name": "Climate Change Causes",
      "salience": 0.92,
      "confidence": 0.88,
      "summary": "Primary causes of climate change including greenhouse gases...",
      "node_type": "concept",
      "used_in_context": "direct_match, semantic_similarity"
    }
  ]
}
```

## Database Storage

Reasoning nodes are stored in the `chat_messages` table in the `nodes_referenced` JSON column:

```sql
-- Example stored data
{
  "nodes_referenced": [
    {
      "uuid": "node-uuid-123",
      "name": "Climate Change Causes",
      "salience": 0.92,
      "confidence": 0.88,
      "summary": "Primary causes of climate change...",
      "node_type": "concept",
      "used_in_context": "direct_match"
    }
  ]
}
```

## Frontend Display

### ReasoningNodes Component
- **Expandable Card**: Shows/hides detailed node information
- **Summary Statistics**: Average salience and confidence
- **Node Rankings**: Sorted by salience (most important first)
- **Interactive Details**: Click to expand individual node information
- **Visual Metrics**: Progress bars for salience and confidence
- **Responsive Design**: Works on desktop and mobile

### Features
- **Color Coding**: Different colors for confidence/salience levels
  - High (≥0.8): Green/Primary
  - Medium (≥0.6): Yellow/Warning  
  - Low (<0.6): Red/Danger
- **Progressive Disclosure**: Summary view with expandable details
- **Search Context**: Shows how each node was used in reasoning

## Implementation Details

### Backend Components

1. **GraphitiEnhancedSearchService** (`services/graphiti_enhanced_search.py`)
   - Wraps graphiti search with node tracking
   - Extracts salience and confidence from node attributes
   - Determines context usage for each node

2. **Updated RAG Service** (`services/rag_service.py`)
   - Added graph mode support
   - Integration with enhanced search service
   - Reasoning node extraction and formatting

3. **Database Changes** (`db/models.py`)
   - Added `nodes_referenced` JSON column to `chat_messages`
   - Migration script for column addition

4. **API Updates** (`api/chat.py`)
   - Support for `mode` parameter (normal/graph/combined)
   - Reasoning nodes storage and retrieval

### Frontend Components

1. **ReasoningNodes Component** (`frontend/src/components/AI/ReasoningNodes.tsx`)
   - Beautiful, expandable display of reasoning nodes
   - Interactive node details with metrics visualization
   - Responsive design with progressive disclosure

2. **Updated Chat Interface** (`frontend/src/pages/Chat/Chat.tsx`)
   - Integration of ReasoningNodes component
   - Display reasoning nodes when available

3. **Type Definitions** (`frontend/src/features/chatSlice.ts`)
   - Added reasoning_nodes to ChatMessage interface

## Setup Instructions

### 1. Run Database Migration
```bash
python run_migration.py
```

### 2. Ensure Dependencies
Make sure the following services are configured:
- Graphiti core system
- FCS Memory Service
- Neo4j database (for knowledge graph)

### 3. Use Graph Mode
Set the query mode to "graph" when making chat requests to enable reasoning node tracking.

## Configuration

### Salience Calculation
- Defaults to time-based decay (newer nodes have higher salience)
- Can be overridden with explicit salience values in node attributes
- Fallback to 0.5 if no salience information available

### Confidence Calculation  
- Defaults to content-length heuristic (longer content = higher confidence)
- Can be overridden with explicit confidence values in node attributes
- Fallback to 0.7 if no confidence information available

### Node Type Detection
- Checks node attributes for explicit type
- Identifies contradictory nodes
- Falls back to generic "knowledge" type

## Benefits

1. **Transparency**: Users can see which knowledge influenced the AI's response
2. **Trust**: Confidence and salience metrics help assess reliability
3. **Debugging**: Developers can understand reasoning processes
4. **Learning**: Users can explore the knowledge graph through reasoning traces
5. **Auditability**: All reasoning nodes are stored for later review

## Future Enhancements

- Node relationship visualization
- Reasoning path tracing
- Confidence scoring improvements
- Integration with contradiction detection
- Export functionality for reasoning traces
- Advanced filtering and search in reasoning history 