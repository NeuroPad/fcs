from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from .chat import ReasoningNode


class GraphRAGResponse(BaseModel):
    """Basic GraphRAG response model"""
    answer: str
    sources: Optional[List[str]] = None


class Question(BaseModel):
    """Question model for API requests"""
    text: str


class ExtendedGraphRAGResponse(BaseModel):
    """Extended GraphRAG response with additional fields"""
    answer: str
    sources: Optional[List[str]] = None
    images: Optional[List[str]] = None
    memory_facts: Optional[str] = None
    reasoning_nodes: Optional[List[ReasoningNode]] = None
    should_save: bool = True


class PageRange(BaseModel):
    """Page range for document processing"""
    start: Optional[int] = None
    end: Optional[int] = None
    all_pages: bool = True 