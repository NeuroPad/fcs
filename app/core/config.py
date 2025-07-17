from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path
from typing import Optional

ROOT_DIR = Path().absolute()

# Define models directory relative to project root
MODELS_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent / "models"

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./memduo.db")
    
    # Neo4J settings
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
    
    # Pinecone settings for RAG
    PINECONE_API_KEY: Optional[str] = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
    
    # Directory paths
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "uploads"))
    CHAT_IMAGES_DIR: Path = ROOT_DIR / "chat_images"
    CHROMA_DB_DIR: Path = ROOT_DIR / "chroma_db"
    MODELS_DIR: Path = MODELS_DIR  
    
    # For backward compatibility
    PROCESSED_FILES_DIR: Path = ROOT_DIR / "uploads"

    # MinerU API
    MINERU_API_TOKEN: Optional[str] = os.getenv("MINERU_API_TOKEN")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()