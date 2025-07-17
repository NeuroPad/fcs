from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class DocumentBase(BaseModel):
    filename: str
    content_type: str
    file_path: str
    markdown_path: Optional[str] = None
    file_size: int
    status: str
    is_indexed: bool = False
    error_message: Optional[str] = None


class DocumentCreate(DocumentBase):
    user_id: int


class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    created_at: datetime
    processed_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class DocumentList(BaseModel):
    documents: List[DocumentResponse]
    count: int
    total_size: int


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