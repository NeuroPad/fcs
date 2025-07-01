from typing import Optional, List, Any
from pydantic import BaseModel
from datetime import datetime
from fastapi import UploadFile


class ReasoningNode(BaseModel):
    """Represents a node used during reasoning process"""
    uuid: str
    name: str
    salience: Optional[float] = None
    confidence: Optional[float] = None
    summary: Optional[str] = None
    node_type: Optional[str] = None
    used_in_context: Optional[str] = None  # How this node was used in the reasoning


class QuestionRequest(BaseModel):
    text: str


class ChatMessageBase(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    image_path: Optional[str] = None
    nodes_referenced: Optional[List[Any]] = None


class ChatMessageCreate(ChatMessageBase):
    session_id: int


class ChatMessageInDBBase(ChatMessageBase):
    id: int
    session_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessage(ChatMessageInDBBase):
    pass


class ChatSessionBase(BaseModel):
    title: Optional[str] = None


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None


class ChatSessionInDBBase(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatSession(ChatSessionInDBBase):
    messages: List[ChatMessage] = []


class ChatSessionWithMessages(ChatSession):
    pass


class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str] = None
    created_at: datetime
    messages: List[dict] = []

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}