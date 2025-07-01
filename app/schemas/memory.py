from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class CognitiveObjectCreate(BaseModel):
    """Request model for creating a cognitive object"""
    content: str = Field(..., description="Natural language text expressed or inferred")
    type: str = Field(..., description="Enum: idea, contradiction, reference, system_note")
    confidence: float = Field(..., description="Float [0.0 – 1.0] — how sure the system is this idea is currently valid")
    salience: float = Field(..., description="Float — how central or reinforced this idea is within the session")
    source: str = Field(..., description="One of user, external, or system")
    flags: List[str] = Field(default_factory=list, description="Optional list, e.g. tracked, contradiction, external, unverified, dismissed")
    parent_ids: List[str] = Field(default_factory=list, description="List of UUIDs — COs this idea directly builds on")
    linked_refs: List[str] = Field(default_factory=list, description="Optional list of CO.id or source string, e.g., reference DOI or URL")
    external_metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional dict with source_url, title, authors, abstract")


class CognitiveObjectResponse(BaseModel):
    """Response model for a cognitive object"""
    id: str = Field(..., description="Unique identifier (UUID)")
    content: str = Field(..., description="Natural language text expressed or inferred")
    type: str = Field(..., description="Enum: idea, contradiction, reference, system_note")
    confidence: float = Field(..., description="Float [0.0 – 1.0] — how sure the system is this idea is currently valid")
    salience: float = Field(..., description="Float — how central or reinforced this idea is within the session")
    timestamp: datetime = Field(..., description="Time of creation or most recent reinforcement")
    last_updated: datetime = Field(..., description="Timestamp — when the CO was last referenced, matched, or affected")
    source: str = Field(..., description="One of user, external, or system")
    flags: List[str] = Field(..., description="Optional list, e.g. tracked, contradiction, external, unverified, dismissed")
    parent_ids: List[str] = Field(..., description="List of UUIDs — COs this idea directly builds on")
    child_ids: List[str] = Field(..., description="List of UUIDs — COs derived from this idea")


class MessageCreate(BaseModel):
    """Request model for creating a message"""
    uuid: str | None = Field(default=None, description='The uuid of the message (optional)')
    content: str = Field(..., description="The content of the message")
    role_type: str = Field(..., description="The role type of the message (user, assistant or system)")
    role: Optional[str] = Field(None, description="The custom role of the message")
    name: Optional[str] = Field(None, description="The name of the episodic node for the message")
    source_description: Optional[str] = Field(None, description="The description of the source of the message")


class MessageResponse(BaseModel):
    """Response model for a message"""
    uuid: str = Field(..., description="The uuid of the message")
    content: str = Field(..., description="The content of the message")
    role_type: str = Field(..., description="The role type of the message (user, assistant or system)")
    role: Optional[str] = Field(None, description="The custom role of the message")
    timestamp: datetime = Field(..., description="The timestamp of the message")
    name: str = Field(..., description="The name of the episodic node for the message")
    source_description: str = Field(..., description="The description of the source of the message")


class TextDocumentCreate(BaseModel):
    """Request model for creating a text document"""
    content: str = Field(..., description="The text content to add")
    source_name: str = Field(..., description="Name of the source document")
    source_description: Optional[str] = Field(None, description="Description of the source")


class SearchQuery(BaseModel):
    """Request model for searching memory"""
    group_ids: list[str] | None = Field(
        None, description='The group ids for the memories to search'
    )
    query: str
    max_facts: int = Field(default=10, description='The maximum number of facts to retrieve')


class FactResult(BaseModel):
    """Response model for a search result (can be edge, node, or episode)"""
    uuid: str = Field(..., description="The uuid of the result")
    type: str = Field(..., description="The type of result: edge, node, or episode")
    
    # Edge-specific fields (optional)
    name: Optional[str] = Field(None, description="The name of the edge/fact")
    fact: Optional[str] = Field(None, description="The fact content (for edges)")
    source_node_uuid: Optional[str] = Field(None, description="Source node UUID (for edges)")
    target_node_uuid: Optional[str] = Field(None, description="Target node UUID (for edges)")
    is_contradiction: Optional[bool] = Field(None, description="Whether this is a contradiction edge")
    
    # Node-specific fields (optional)
    summary: Optional[str] = Field(None, description="The summary of the node")
    labels: Optional[List[str]] = Field(None, description="Labels of the node")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Attributes of the node")
    
    # Episode-specific fields (optional)
    content: Optional[str] = Field(None, description="The content of the episode")
    source_description: Optional[str] = Field(None, description="Description of the episode source")
    source: Optional[str] = Field(None, description="Source type of the episode")
    
    # Common fields
    valid_at: Optional[datetime] = Field(None, description="When the result became valid")
    invalid_at: Optional[datetime] = Field(None, description="When the result became invalid")
    created_at: Optional[datetime] = Field(None, description="When the result was created")
    expired_at: Optional[datetime] = Field(None, description="When the result expired")


class SearchResults(BaseModel):
    """Response model for search results"""
    status: str = Field(..., description="Status of the search")
    results: List[FactResult] = Field(..., description="The search results")
    count: int = Field(..., description="Number of results")
    contradiction_count: Optional[int] = Field(None, description="Number of contradiction edges found")
    has_contradictions: Optional[bool] = Field(None, description="Whether any contradictions were found")
    summary: Optional[Dict[str, int]] = Field(None, description="Summary of result types (edges, nodes, episodes, communities)")


class OperationResponse(BaseModel):
    """Response model for operations"""
    status: str = Field(..., description="Status of the operation (success, error, partial)")
    message: str = Field(..., description="Message describing the operation result")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional data about the operation")


class TopNode(BaseModel):
    """Response model for a top node result"""
    uuid: str = Field(..., description="The UUID of the node")
    name: str = Field(..., description="The name of the node")
    summary: Optional[str] = Field(None, description="The summary of the node")
    connections: int = Field(..., description="Number of connections to this node")


class TopFact(BaseModel):
    """Response model for a top fact result"""
    fact: str = Field(..., description="The fact content")
    occurrences: int = Field(..., description="Number of occurrences of this fact")


class TopConnectionsResponse(BaseModel):
    """Response model for top connections"""
    status: str = Field(..., description="Status of the operation")
    connections: List[TopNode] = Field(..., description="List of top nodes by connection count")
    count: int = Field(..., description="Number of connections returned") 