from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=False)  # Path to the original file
    markdown_path = Column(String(500), nullable=True)  # Path to markdown version (for scanned PDFs)
    file_size = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    is_indexed = Column(Boolean, default=False)  # Whether the document has been indexed in RAG
    error_message = Column(Text, nullable=True)  # Error message if processing failed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)  # When processing completed
    indexed_at = Column(DateTime(timezone=True), nullable=True)  # When document was indexed in RAG
    
    # Relationships
    user = relationship("User", back_populates="documents") 