from fastapi import UploadFile
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ReasoningNode(BaseModel):
    """Represents a node used during reasoning process"""
    uuid: str
    name: str
    salience: Optional[float] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    node_type: Optional[str] = None
    used_in_context: Optional[str] = None  # How this node was used in the reasoning


class ChatMessageCreate(BaseModel):
    role: str
    content: Optional[str] = None
    image: Optional[UploadFile] = None  # For file uploads


class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    created_at: datetime
    messages: List[dict] = []

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

class QuestionRequest(BaseModel):
    text: str