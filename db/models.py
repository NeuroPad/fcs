from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db.session import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Owner of the chat session
    title = Column(String, nullable=True, default=None)  # Session title, can be blank
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship("ChatMessage", back_populates="session")
    user = relationship("User")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)  # Text content
    image_path = Column(String, nullable=True)  # Path to the image (if any)
    nodes_referenced = Column(JSON, nullable=True)  # JSON array of nodes used during reasoning
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # 'admin' or 'user'
    machine_name = Column(String, nullable=True)  # Name given to the AI by the user
    contradiction_tolerance = Column(Integer, nullable=True)  # User's tolerance for contradictory information
    belief_sensitivity = Column(String, nullable=True)  # User's sensitivity to belief challenges (high, moderate, low)
    salience_decay_speed = Column(String, default="default", nullable=True)  # Controls how quickly belief salience decays
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Path to the original file
    markdown_path = Column(String, nullable=True)  # Path to markdown version (for scanned PDFs)
    file_size = Column(Integer, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    is_indexed = Column(Boolean, default=False)  # Whether the document has been indexed in RAG
    error_message = Column(Text, nullable=True)  # Error message if processing failed
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)  # When processing completed
    indexed_at = Column(DateTime, nullable=True)  # When document was indexed in RAG
    
    user = relationship("User")
