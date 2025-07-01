# MemDuo - Memory-Enhanced Document Understanding

A sophisticated FastAPI application that combines document processing, RAG (Retrieval-Augmented Generation), and memory systems for intelligent document understanding and chat interactions.

## 🏗️ Project Structure

```
memduo-remake/
├── app/                          # Main application package
│   ├── api/                      # API layer
│   │   └── v1/                   # API version 1
│   │       ├── endpoints/        # API endpoints
│   │       │   ├── auth.py       # Authentication endpoints
│   │       │   ├── roles.py      # Role management
│   │       │   ├── chat.py       # Chat functionality
│   │       │   ├── documents.py  # Document management
│   │       │   ├── files.py      # File operations
│   │       │   ├── memory.py     # Memory system
│   │       │   └── rag.py        # RAG endpoints
│   │       └── api.py            # Main API router
│   ├── core/                     # Core functionality
│   │   ├── config.py             # Configuration
│   │   └── logging.py            # Logging setup
│   ├── db/                       # Database layer
│   │   ├── base.py               # Base imports
│   │   ├── session.py            # Database session
│   │   └── init_db.py            # Database initialization
│   ├── models/                   # SQLAlchemy models
│   │   ├── user.py               # User model
│   │   ├── role.py               # Role model
│   │   ├── user_role.py          # User-Role relationship
│   │   ├── chat.py               # Chat models
│   │   └── document.py           # Document model
│   ├── schemas/                  # Pydantic schemas
│   │   ├── auth.py               # Authentication schemas
│   │   ├── user.py               # User schemas
│   │   ├── role.py               # Role schemas
│   │   ├── chat.py               # Chat schemas
│   │   └── document.py           # Document schemas
│   ├── services/                 # Business logic (existing)
│   └── main.py                   # FastAPI application
├── alembic/                      # Database migrations
├── graphiti_core/                # Graph processing (unchanged)
├── graphiti_extend/              # Graph extensions (unchanged)
├── fcs_core/                     # FCS memory system (unchanged)
├── frontend/                     # React frontend (unchanged)
└── setup_db.py                   # Database setup script
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Poetry (for dependency management)
- Neo4j (for graph database)
- OpenAI API key (optional, for AI features)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd memduo-remake
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Set up environment variables**
   ```bash
   cp example.env .env
   # Edit .env with your configuration
   ```

4. **Initialize the database**
   ```bash
   python setup_db.py
   ```

5. **Start the application**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## 🗄️ Database Management

### Migrations

This project uses Alembic for database migrations.

#### Creating a New Migration

```bash
poetry run alembic revision --autogenerate -m "Description of changes"
```

#### Running Migrations

```bash
poetry run alembic upgrade head
```

#### Viewing Migration History

```bash
poetry run alembic history
```

#### Rolling Back

```bash
poetry run alembic downgrade -1  # Go back one migration
poetry run alembic downgrade <revision_id>  # Go to specific revision
```

### Database Configuration

The application supports both SQLite (default) and PostgreSQL:

**SQLite (Development):**
```env
DATABASE_URL=sqlite:///./memduo.db
```

**PostgreSQL (Production):**
```env
DATABASE_URL=postgresql://user:password@localhost/memduo
```

## 🔐 Authentication & Authorization

### Role-Based Access Control

The application includes a role-based access control system:

- **Admin Role**: Full system access
- **User Role**: Standard user access

### Default Credentials

After running `setup_db.py`, you can login with:
- **Email**: admin@memduo.com
- **Password**: admin123

⚠️ **Change these credentials in production!**

### API Authentication

All protected endpoints require JWT authentication:

```bash
# Login to get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@memduo.com", "password": "admin123"}'

# Use token in requests
curl -X GET "http://localhost:8000/api/v1/roles/" \
  -H "Authorization: Bearer <your-token>"
```

## 📚 API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | User login |
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/roles/` | GET | List all roles |
| `/api/v1/roles/` | POST | Create new role |
| `/api/v1/roles/{id}` | GET/PUT/DELETE | Role management |
| `/api/v1/chat/` | GET | Chat endpoints (to be implemented) |
| `/api/v1/documents/` | GET | Document endpoints (to be implemented) |
| `/api/v1/files/` | GET | File endpoints (to be implemented) |
| `/api/v1/memory/` | GET | Memory endpoints (to be implemented) |
| `/api/v1/rag/` | GET | RAG endpoints (to be implemented) |

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=sqlite:///./memduo.db

# Neo4j (for graph features)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200

# Pinecone (for RAG)
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=gcp-starter
```

## 🧪 Testing

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=app
```

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d
```

## 📝 Development Guidelines

### Code Structure

- **Models**: SQLAlchemy models in `app/models/`
- **Schemas**: Pydantic schemas in `app/schemas/`
- **Endpoints**: FastAPI routes in `app/api/v1/endpoints/`
- **Services**: Business logic in `app/services/` (existing)
- **Database**: Database utilities in `app/db/`

### Adding New Features

1. **Create Model**: Add SQLAlchemy model in `app/models/`
2. **Create Schema**: Add Pydantic schemas in `app/schemas/`
3. **Create Endpoints**: Add API routes in `app/api/v1/endpoints/`
4. **Create Migration**: Generate migration with Alembic
5. **Update Router**: Include new endpoints in `app/api/v1/api.py`

### Migration Workflow

1. **Make Model Changes**: Modify models in `app/models/`
2. **Generate Migration**:
   ```bash
   poetry run alembic revision --autogenerate -m "Add new feature"
   ```
3. **Review Migration**: Check the generated migration file
4. **Apply Migration**:
   ```bash
   poetry run alembic upgrade head
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes
4. Run tests: `poetry run pytest`
5. Create a pull request

## 📄 License

[Add your license information here]

## 🆘 Troubleshooting

### Common Issues

1. **Migration Issues**:
   ```bash
   # Reset migrations (development only)
   rm alembic/versions/*.py
   poetry run alembic revision --autogenerate -m "Initial migration"
   ```

2. **Database Connection Issues**:
   - Check DATABASE_URL in .env
   - Ensure database server is running (if using PostgreSQL)

3. **Import Errors**:
   - Make sure you're in the project root directory
   - Check that all dependencies are installed: `poetry install`

### Getting Help

- Check the API documentation at `/docs`
- Review the logs in the `logs/` directory
- Open an issue on the repository

---

**Happy coding! 🚀**

