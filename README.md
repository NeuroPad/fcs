
# FCS: Fischman-Gardener Cognitive System (GraphRAG-Based)

A FastAPI-powered system implementing **Graph-based Retrieval-Augmented Generation (GRAPH RAG)** with an architecture inspired by the **Fischman-Gardener Model** of continuous human-AI co-evolution. This project combines **Neo4j**, **LangChain**, and **LlamaIndex** to deliver adaptive intelligence through dynamic graph reasoning.

## 🔍 Features

- **Multimodal Document Understanding**  
  - PDF and TXT file ingestion  
  - Image extraction & semantic linking  
  - Markdown & structured text conversion  

- **FGM-Inspired GRAPH RAG Architecture**  
  - Integration with LangChain for contextual reasoning  
  - LlamaIndex for document embeddings  
  - Neo4j as the fluid knowledge graph backend  

- **Interactive Co-Adaptive API**  
  - File upload & session-based document memory  
  - Real-time chat for co-evolving knowledge interactions  
  - Confidence-preserving querying using graph insights  

- **User Interface for Exploration**  
  - Conversational frontend mimicking bidirectional adaptation  
  - Semantic file exploration  
  - Live graph session support

## ⚙️ Prerequisites

- Python 3.9 or higher  
- [Poetry](https://python-poetry.org/) for dependency management  
- Running Neo4j instance (AuraDB or self-hosted)  
- OpenAI API key  
- Node.js 14+  
- npm or yarn

## 🚀 Installation & Setup

### Backend Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/fischmanb/fcs.git
   cd fcs
   ```

2. **Install Poetry:**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install backend dependencies:**
   ```bash
   poetry install
   ```

4. **Configure your environment:**
   Create a `.env` file with your credentials:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   NEO4J_URI=your_neo4j_uri
   NEO4J_USERNAME=your_neo4j_username
   NEO4J_PASSWORD=your_neo4j_password
   ```

### Frontend Setup

1. **Navigate to the frontend:**
   ```bash
   cd frontend
   ```

2. **Install frontend dependencies:**
   ```bash
   npm install  # or yarn install
   ```

## 🧠 Running FCS Locally

### Start the Backend (Graph & AI Brain)

1. **Activate Poetry environment:**
   ```bash
   poetry shell
   ```

2. **Launch FastAPI server:**
   ```bash
   uvicorn main:app --reload --loop=asyncio
   ```

3. **Access backend at:**
   - API Root: [http://localhost:8000](http://localhost:8000)
   - Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Start the Frontend (Human-AI Interaction Surface)

1. **If not already in frontend directory:**
   ```bash
   cd frontend
   ```

2. **Run the development server:**
   ```bash
   npm start  # or yarn start
   ```

3. **Access the interface at:**  
   - [http://localhost:3000](http://localhost:3000)

## 🛠 API Overview

All endpoints for document ingestion, processing, and chat interaction are documented at `/docs`. These are designed to support:

- Real-time file and node management  
- Adaptive conversation with memory context  
- Retrieval-augmented answers from graph-based knowledge

