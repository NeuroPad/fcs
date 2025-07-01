from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class DocumentBase(BaseModel):
    filename: str
    content_type: str
    file_size: int


class DocumentCreate(DocumentBase):
    file_path: str


class DocumentUpdate(BaseModel):
    filename: Optional[str] = None
    status: Optional[str] = None
    is_indexed: Optional[bool] = None
    error_message: Optional[str] = None
    markdown_path: Optional[str] = None
    processed_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None


class DocumentInDBBase(DocumentBase):
    id: int
    user_id: int
    file_path: str
    markdown_path: Optional[str] = None
    status: str
    is_indexed: bool
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Document(DocumentInDBBase):
    pass 