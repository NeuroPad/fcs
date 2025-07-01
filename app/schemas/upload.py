from typing import List, Optional
from pydantic import BaseModel


class FileUpload(BaseModel):
    """File upload model"""
    filename: str
    content_type: str
    size: int


class DocumentResponse(BaseModel):
    """Document response model"""
    id: int
    filename: str
    content_type: str
    file_size: int
    status: str
    created_at: str
    user_id: int


class DocumentList(BaseModel):
    """List of documents response"""
    documents: List[DocumentResponse]
    count: int
    total_size: int 