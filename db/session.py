from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///fcs.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    # Import models here to avoid circular imports
    from db.models import ChatSession, ChatMessage
    Base.metadata.create_all(bind=engine)
    
    # Run migrations to add new columns
    # from db.migrations import run_migrations
    # run_migrations()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()