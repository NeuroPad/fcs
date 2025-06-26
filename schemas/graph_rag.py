from pydantic import BaseModel, Field
from typing import Optional, Union, List
from schemas.chat import ReasoningNode


class Question(BaseModel):
    text: str


class GraphRAGResponse(BaseModel):
    response: str


class ExtendedGraphRAGResponse(BaseModel):
    answer: str
    images: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    memory_facts: Optional[str] = None
    reasoning_nodes: Optional[List[ReasoningNode]] = Field(None, description="Nodes used during reasoning process")