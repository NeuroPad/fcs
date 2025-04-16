# GraphRAG FastAPI Project

A FastAPI-based implementation of Graph-based Retrieval Augmented Generation (GRAPH RAG) using Neo4j, LangChain, and LlamaIndex.

## Features

- **Multimodal Document Processing**  
  - PDF and TXT file support  
  - Image extraction and indexing  
  - Markdown conversion  
- **Advanced GRAPH RAG Implementation**  
  - LangChain integration  
  - LlamaIndex integration  
  - Neo4j Graph Database backend  
- **Comprehensive API Features**  
  - File management endpoints  
  - Document processing  
- **Interactive Frontend**  
  - Real-time chat interface  
  - File upload support  
  - Session management  

## Prerequisites

- Python 3.9 or higher
- Poetry for dependency management
- Neo4j database instance
- OpenAI API key
- Node.js 14 or higher
- npm or yarn

## Installation and Setup

### Backend Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AdebisiJoe/multimodal-graphrag-api.git
   cd multimodal-graphrag-api
   ```
2. **Install Poetry:**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```
3. **Install backend dependencies:**
   ```bash
   poetry install
   ```
4. **Create a `.env` file in the root directory:**
   ```env
   OPENAI_API_KEY=your_openai_api_key
   NEO4J_URI=your_neo4j_uri
   NEO4J_USERNAME=your_neo4j_username
   NEO4J_PASSWORD=your_neo4j_password
   ```

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```
2. **Install frontend dependencies:**
   ```bash
   npm install  # or using yarn: yarn install
   ```

## Running the Application

### Start the Backend

1. **Activate the Poetry environment:**
   ```bash
   poetry shell
   ```
2. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload --loop=asyncio
   ```
3. **The backend will be available at:**
   - API: [http://localhost:8000](http://localhost:8000)
   - Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
   - Alternative docs: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Start the Frontend

1. **Navigate to the frontend directory (if not already there):**
   ```bash
   cd frontend
   ```
2. **Start the development server:**
   ```bash
   npm run start  # or using yarn: yarn start
   ```
3. **The frontend will be available at:**  
   - [http://localhost:3000](http://localhost:3000)

## API Endpoints

More endpoints and their descriptions can be found in the API documentation.



