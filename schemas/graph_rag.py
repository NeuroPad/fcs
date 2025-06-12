from pydantic import BaseModel, Field
from typing import Optional, Union, List


class Question(BaseModel):
    text: str


class GraphRAGResponse(BaseModel):
    response: str


class ExtendedGraphRAGResponse(BaseModel):
    answer: str
    images: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    memory_facts: Optional[str] = None