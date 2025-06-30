# FCS System Documentation

## Overview

The FCS is a sophisticated cognitive AI system that implements brain-like memory management, contradiction detection, and adaptive learning. The system is designed to grow with users, detect inconsistencies in their beliefs, and provide a personalized cognitive companion experience.

## System Architecture

### Core Philosophy

The FCS system operates on the principle of **Design Your Own Intelligence** - it doesn't come with pre-trained knowledge but learns entirely from user interactions. It maintains a belief graph where every piece of information is timestamped, source-traceable, and tied directly to user input.

### Key Principles

1. **No Pre-trained Knowledge**: The system only knows what users provide
2. **Contradiction Detection**: Automatically identifies conflicting beliefs
3. **Memory Reinforcement**: Brain-like salience management for concepts
4. **Confidence Tracking**: Dynamic confidence scoring for all beliefs
5. **Privacy-First**: All data remains private and user-controlled
6. **Adaptive Learning**: System evolves based on user interactions

## System Components

### 1. Backend Architecture (FastAPI)

#### Main Application (`main.py`)
- **Entry Point**: FastAPI application with CORS middleware
- **Startup Events**: Initializes database, FCSMemoryService, and DocumentService workers
- **Shutdown Events**: Graceful cleanup of background workers
- **Static File Serving**: Serves processed files and uploads

#### Configuration (`core/config.py`)
- **Environment Management**: Pydantic settings for all configuration
- **Database Connections**: Neo4j, Pinecone, and ChromaDB settings
- **API Keys**: OpenAI, Pinecone, and other service credentials
- **Directory Paths**: File storage and processing directories

### 2. Memory Management System

#### FCS Core (`fcs_core/`)
The heart of the cognitive system with three main components:

**FCSMemoryService** (`fcs_core/fcs_memory_service.py`)
- **Purpose**: Enhanced memory service with contradiction detection
- **Key Features**:
  - Automatic contradiction detection between new and existing nodes
  - Real-time contradiction alerts
  - Enhanced search with contradiction awareness
  - Background processing with retry logic
- **API Compatibility**: Maintains full compatibility with original GraphitiMemoryService

**Async Worker** (`fcs_core/async_worker.py`)
- **Purpose**: Background processing for memory operations
- **Features**:
  - Retry logic with exponential backoff
  - Graceful shutdown with queue cleanup
  - Error isolation to prevent crashes
  - Queue management for episode processing

**Data Models** (`fcs_core/models.py`)
- **CognitiveObject**: Represents user beliefs and concepts
- **Message**: Chat messages with metadata
- **ContradictionAlert**: Structured alerts for detected contradictions
- **FCSResponse**: Standardized response format

### 3. Graph Management System

#### Graphiti Core (`graphiti_core/`)
The underlying graph database management system:

**Extended Graphiti** (`graphiti_extend/extended_graphiti.py`)
- **Purpose**: Extends base Graphiti with advanced cognitive features
- **Key Features**:
  - `add_episode_with_contradictions()`: Main processing method
  - Automatic contradiction detection
  - Salience management for brain-like memory
  - Confidence scoring and updates
  - Network reinforcement for connected concepts

**Salience System** (`graphiti_extend/salience/`)
- **Purpose**: Brain-like memory reinforcement
- **Features**:
  - Automatic salience updates during episode processing
  - Network reinforcement for connected concepts
  - Temporal decay for unused concepts
  - Scheduled forgetting and cleanup
  - Structural importance boosts

**Confidence System** (`graphiti_extend/confidence/`)
- **Purpose**: Dynamic confidence scoring for beliefs
- **Features**:
  - Initial confidence assignment based on origin type
  - Confidence updates from various triggers
  - Contradiction penalties and boosts
  - Network reinforcement effects
  - Dormancy decay for unused beliefs

**Contradiction Detection** (`graphiti_extend/contradictions/`)
- **Purpose**: Identify conflicting beliefs
- **Features**:
  - LLM-powered contradiction detection
  - Human-readable contradiction messages
  - Contradiction edge creation in graph
  - Severity assessment and alerting

### 4. RAG (Retrieval-Augmented Generation) System

#### RAG Service (`services/rag_service.py`)
- **Purpose**: Document retrieval and response generation
- **Features**:
  - Multi-tenant document storage (Pinecone/ChromaDB)
  - User-specific context retrieval
  - Memory facts integration
  - Chat history context
  - Structured response generation
  - Automatic memory storage for meaningful interactions

**Key Capabilities**:
- **Multi-modal Support**: Text and document processing
- **Memory Integration**: Combines document knowledge with user memory
- **Context Awareness**: Uses chat history and user memory facts
- **Source Attribution**: Tracks document sources used in responses
- **Selective Storage**: Only saves meaningful interactions to memory

### 5. API Layer

#### REST API Endpoints (`api/`)

**Chat API** (`api/chat.py`)
- **Session Management**: Create, retrieve, and delete chat sessions
- **Message Handling**: Add messages and get responses
- **Query Processing**: Route queries to appropriate services
- **User Authentication**: JWT-based user verification

**Memory API** (`api/memory.py`)
- **Memory Operations**: Add, search, and manage user memory
- **Contradiction Alerts**: Retrieve and manage contradiction alerts
- **Cognitive Objects**: Manage user beliefs and concepts
- **Search Functionality**: Advanced memory search with filters

**Document API** (`api/documents.py`)
- **Document Upload**: File upload and processing
- **Document Management**: List, delete, and manage documents
- **Processing Status**: Track document processing status
- **Multi-format Support**: Various document formats

**Authentication API** (`api/auth_routes.py`)
- **User Registration**: New user account creation
- **User Login**: JWT token generation
- **Password Management**: Reset and change functionality
- **Session Management**: Token validation and refresh

### 6. Frontend (React/Ionic)

#### Chat Interface (`frontend/src/pages/Chat/`)
- **Real-time Chat**: Live message exchange
- **Message Rendering**: Markdown and LaTeX support
- **File Display**: Image and source document display
- **Session Management**: Chat session persistence
- **Responsive Design**: Mobile-first interface

#### State Management (`frontend/src/features/`)
- **Redux Store**: Centralized state management
- **Chat Slice**: Chat session and message state
- **User Slice**: User authentication and profile
- **Document Slice**: Document management state

## Data Flow

### 1. User Input Processing

```
User Message → Chat API → RAG Service → Memory Service → Extended Graphiti
     ↓
Response Generation ← Memory Facts ← Contradiction Detection ← Episode Processing
```

### 2. Memory Storage Flow

```
User Input → FCSMemoryService → ExtendedGraphiti.add_episode_with_contradictions()
     ↓
Node Extraction → Contradiction Detection → Salience Updates → Confidence Assignment
     ↓
Graph Storage ← Network Reinforcement ← Structural Boosts ← Background Processing
```

### 3. Contradiction Detection Flow

```
New Episode → Similarity Search → LLM Contradiction Analysis → Alert Generation
     ↓
Contradiction Edges ← User Notification ← FCS System Integration ← Response Options
```

## Key Features

### 1. Contradiction Detection
- **Automatic Detection**: Identifies conflicting beliefs during processing
- **Human-readable Messages**: Generates conversational contradiction alerts
- **Severity Assessment**: Categorizes contradictions by importance
- **User Response Handling**: Provides options for contradiction resolution

### 2. Brain-like Memory
- **Salience Management**: Concepts strengthen with usage and connections
- **Temporal Decay**: Unused concepts naturally fade over time
- **Network Reinforcement**: Connected concepts reinforce each other
- **Structural Importance**: Well-connected concepts receive boosts

### 3. Confidence Scoring
- **Dynamic Confidence**: Beliefs have confidence scores that change over time
- **Origin Tracking**: Different sources of information have different initial confidence
- **Contradiction Effects**: Contradictions affect confidence levels
- **Network Support**: Connected beliefs provide confidence reinforcement

### 4. Multi-modal RAG
- **Document Processing**: Supports various document formats
- **Memory Integration**: Combines document knowledge with user memory
- **Source Attribution**: Tracks which documents inform responses
- **Selective Storage**: Only meaningful interactions are stored in memory

## System Integration Points

### 1. Database Layer
- **Neo4j**: Primary graph database for cognitive objects and relationships
- **SQLITE**: User management and session data
- **Pinecone/ChromaDB**: Vector storage for document embeddings

### 2. External Services
- **OpenAI**: LLM for contradiction detection and response generation
- **Embedding Models**: Text embedding for similarity search
- **File Processing**: Document parsing and text extraction

### 3. Background Processing
- **Async Workers**: Background processing for memory operations
- **Document Processing**: Asynchronous document indexing
- **Decay Scheduling**: Periodic memory decay and cleanup

## Configuration and Deployment

### Environment Variables
```bash
# Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# AI Services
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=gcp-starter

# Security
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200
```

### Docker Deployment
- **Backend**: FastAPI application with Neo4j and PostgreSQL
- **Frontend**: React/Ionic application with static file serving
- **Database**: Neo4j and PostgreSQL containers
- **Vector Store**: Pinecone or ChromaDB integration

## Monitoring and Analytics

### Key Metrics
- **Contradiction Detection Rate**: Frequency of detected contradictions
- **Memory Growth**: Rate of new cognitive objects and relationships
- **Salience Distribution**: Distribution of concept salience scores
- **Confidence Trends**: Average confidence levels over time
- **User Engagement**: Interaction patterns and session data

### Logging
- **Structured Logging**: JSON-formatted logs for analysis
- **Error Tracking**: Comprehensive error logging and monitoring
- **Performance Metrics**: Response times and resource usage
- **User Activity**: Anonymized user interaction patterns

## Security and Privacy

### Data Protection
- **User Isolation**: Complete data separation between users
- **Encryption**: All sensitive data encrypted at rest and in transit
- **Access Control**: JWT-based authentication and authorization
- **Audit Logging**: Comprehensive audit trails for all operations

### Privacy Features
- **Local Processing**: Minimal external data transmission
- **User Control**: Users can delete all their data
- **No External Sharing**: No data shared with third parties
- **Transparent Operations**: Clear visibility into data usage

## Future Development

### Planned Features
1. **Advanced Agent Flow**: Proactive cognitive interactions
2. **Enhanced Contradiction Resolution**: More sophisticated contradiction handling
3. **Multi-modal Learning**: Image and audio processing capabilities
4. **Advanced Analytics**: Deep insights into cognitive patterns

### Architecture Evolution
1. **Microservices**: Breaking down into smaller, focused services
2. **Event-Driven Architecture**: Real-time event processing
3. **Advanced Caching**: Intelligent caching for performance
4. **Scalability Improvements**: Horizontal scaling capabilities

## Conclusion

The FCS system represents a sophisticated approach to AI that prioritizes user agency, privacy, and cognitive growth. By implementing brain-like memory management, automatic contradiction detection, and adaptive learning, it provides a unique platform for personal cognitive development while maintaining complete user control over their data and beliefs.

The system's modular architecture allows for continuous improvement and expansion while maintaining the core principles of transparency, privacy, and user-driven intelligence design.