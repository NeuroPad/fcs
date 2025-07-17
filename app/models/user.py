from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # AI personalization settings
    machine_name = Column(String(100), nullable=True)  # Name given to the AI by the user
    contradiction_tolerance = Column(Float, nullable=True)  # User's tolerance for contradictory information
    belief_sensitivity = Column(String(50), nullable=True)  # User's sensitivity to belief challenges (high, moderate, low)
    salience_decay_speed = Column(String(50), default="default", nullable=True)  # Controls how quickly belief salience decays
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user_roles = relationship("UserRole", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")
    documents = relationship("Document", back_populates="user")