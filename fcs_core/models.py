"""
Copyright 2025, FCS Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from graphiti_core.utils.datetime_utils import utc_now


# Custom Edge Types for FCS System
class Reinforces(BaseModel):
    """Edge representing one cognitive object reinforcing another."""
    strength: Optional[float] = Field(None, description="Strength of reinforcement (0.0-1.0)")
    evidence_type: Optional[str] = Field(None, description="Type of evidence supporting reinforcement")
    confidence_boost: Optional[float] = Field(None, description="Confidence boost provided by this reinforcement")


class Elaborates(BaseModel):
    """Edge representing one cognitive object elaborating on another."""
    elaboration_type: Optional[str] = Field(None, description="Type of elaboration: detail, example, clarification")
    depth_level: Optional[int] = Field(None, description="Level of elaboration depth (1-5)")
    added_context: Optional[str] = Field(None, description="Summary of additional context provided")


class Extends(BaseModel):
    """Edge representing one cognitive object extending another."""
    extension_type: Optional[str] = Field(None, description="Type of extension: logical, temporal, conceptual")
    scope_expansion: Optional[str] = Field(None, description="How the scope is expanded")
    new_dimensions: Optional[List[str]] = Field(default_factory=list, description="New dimensions or aspects added")


class CausedBy(BaseModel):
    """Edge representing causal relationship between cognitive objects."""
    causality_type: Optional[str] = Field(None, description="Type of causality: direct, indirect, contributory")
    temporal_relation: Optional[str] = Field(None, description="Temporal relationship: immediate, delayed, ongoing")
    certainty_level: Optional[float] = Field(None, description="Certainty of causal relationship (0.0-1.0)")
    evidence_strength: Optional[str] = Field(None, description="Strength of evidence: weak, moderate, strong")


class Supports(BaseModel):
    """Edge representing one cognitive object supporting another."""
    support_type: Optional[str] = Field(None, description="Type of support: evidence, logical, empirical, anecdotal")
    weight: Optional[float] = Field(None, description="Weight of support (0.0-1.0)")
    reliability: Optional[str] = Field(None, description="Reliability of support: low, medium, high")
    source_credibility: Optional[float] = Field(None, description="Credibility of the supporting source (0.0-1.0)")


class CognitiveObject(BaseModel):
    """Structured representation of user-expressed or system-derived ideas."""
    id: str = Field(..., description="Unique identifier (UUID)")
    content: str = Field(..., description="Natural language text expressed or inferred")
    type: str = Field(..., description="Enum: idea, contradiction, reference, system_note")
    confidence: float = Field(default=0.7, description="Float [0.0 – 1.0] — how sure the system is this idea is currently valid")
    salience: float = Field(default=0.5, description="Float — how central or reinforced this idea is within the session")
    source: str = Field(..., description="One of user, external, or system where user is the user query, external is the user's external sources, and system is the system or ai assistant generated content")
    flags: List[str] = Field(default_factory=list, description="Optional list, e.g. tracked, contradiction, external, unverified, dismissed")
    parent_ids: List[str] = Field(default_factory=list, description="List of UUIDs — COs this idea directly builds on")
    child_ids: List[str] = Field(default_factory=list, description="List of UUIDs — COs derived from this idea")
    match_history: List[str] = Field(default_factory=list, description="Optional list of CO IDs that have semantically reinforced this CO")
    arbitration_score: Optional[float] = Field(None, description="Optional — last known score from arbitration pass")
    linked_refs: List[str] = Field(default_factory=list, description="Optional list of CO.id or source string, e.g., reference DOI or URL")
    generated_from: List[str] = Field(default_factory=list, description="Optional list of CO IDs used to construct this one (for LLM output tracking)")


class Message(BaseModel):
    """Message model for chat interactions"""
    content: str = Field(..., description="The content of the message")
    uuid: str | None = Field(default=None, description='The uuid of the message (optional)')
    name: str = Field(default="", description="The name of the episodic node for the message (optional)")
    role_type: str = Field(..., description="The role type of the message (user, assistant or system)")
    role: Optional[str] = Field(None, description="The custom role of the message")
    timestamp: datetime = Field(default_factory=utc_now, description="The timestamp of the message")
    source_description: str = Field(default="", description="The description of the source of the message")


class ContradictionAlert(BaseModel):
    """Model for contradiction alerts generated by the FCS system."""
    user_id: str = Field(..., description="The user ID associated with the contradiction")
    message: str = Field(..., description="Human-readable contradiction message")
    contradicting_nodes: List[str] = Field(..., description="UUIDs of nodes that are contradicting")
    contradicted_nodes: List[str] = Field(..., description="UUIDs of nodes that are being contradicted")
    contradiction_edges: List[str] = Field(..., description="UUIDs of CONTRADICTS edges created")
    timestamp: datetime = Field(default_factory=utc_now, description="When the contradiction was detected")
    severity: str = Field(default="medium", description="Severity level: low, medium, high")
    status: str = Field(default="pending", description="Status: pending, acknowledged, resolved, ignored")
    user_response: Optional[str] = Field(None, description="User's response to the contradiction")
    resolution_action: Optional[str] = Field(None, description="Action taken to resolve the contradiction")


class FCSResponse(BaseModel):
    """Model for FCS system responses."""
    status: str = Field(..., description="Response status: success, error, contradiction_detected")
    message: str = Field(..., description="Response message")
    contradiction_alert: Optional[ContradictionAlert] = Field(None, description="Contradiction alert if detected")
    queue_size: Optional[int] = Field(None, description="Current queue size for background processing")
    additional_data: Optional[dict] = Field(None, description="Additional response data") 