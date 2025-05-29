from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path

ROOT_DIR = Path().absolute()

# Define models directory relative to project root
MODELS_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "models"

class Settings(BaseSettings):
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    OPENAI_API_KEY: str = ""
    SECRET_KEY: str = "your-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    
    # Pinecone settings for RAG
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "gcp-starter"
    
    # Directory paths
    UPLOAD_DIR: Path = ROOT_DIR / "uploads"
    CHAT_IMAGES_DIR: Path = ROOT_DIR / "chat_images"
    CHROMA_DB_DIR: Path = ROOT_DIR / "chroma_db"
    MODELS_DIR: Path = MODELS_DIR  
    
    # For backward compatibility
    PROCESSED_FILES_DIR: Path = ROOT_DIR / "uploads"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
