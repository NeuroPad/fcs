from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Union, List
from datetime import datetime


class PageRange(BaseModel):
    start: Optional[int] = None
    end: Optional[int] = None
    all_pages: bool = False


class FileUpload(BaseModel):
    page_range: PageRange = Field(default=PageRange(all_pages=True))


class DocumentBase(BaseModel):
    filename: str
    content_type: str
    file_size: int
    status: str


class DocumentCreate(DocumentBase):
    user_id: int
    file_path: str


class DocumentResponse(DocumentBase):
    id: int
    user_id: int
    file_path: str
    markdown_path: Optional[str] = None
    is_indexed: bool = False
    error_message: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class DocumentList(BaseModel):
    documents: List[DocumentResponse]
    
    model_config = ConfigDict(from_attributes=True)
