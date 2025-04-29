from dotenv import load_dotenv
import os
from pathlib import Path

ROOT_DIR = Path().absolute()
load_dotenv()

# Define models directory relative to project root
MODELS_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "models"

class Settings:
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
    
    PROCESSED_FILES_DIR = ROOT_DIR / "processed_files"
    UPLOAD_DIR = ROOT_DIR / "uploads"
    CHAT_IMAGES_DIR = ROOT_DIR / "chat_images"
    CHROMA_DB_DIR = ROOT_DIR / "chroma_db"
    MODELS_DIR = MODELS_DIR  


settings = Settings()
