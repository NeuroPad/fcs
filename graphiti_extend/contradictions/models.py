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
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge


class ContradictionMetadata(BaseModel):
    """Metadata for contradiction detection and tracking."""
    
    contradiction_reason: str = Field(..., description="Reason why the nodes contradict")
    detection_confidence: float = Field(default=0.8, description="Confidence in contradiction detection")
    detected_in_episode: str = Field(..., description="Episode UUID where contradiction was detected")
    detection_timestamp: datetime = Field(default_factory=datetime.utcnow)
    contradiction_type: str = Field(default="semantic", description="Type of contradiction (semantic, preference, factual)")
    resolution_status: str = Field(default="unresolved", description="Status of contradiction resolution")
    user_feedback: Optional[str] = Field(default=None, description="User feedback on contradiction")


class CognitiveObjectPair(BaseModel):
    """Represents a pair of cognitive objects that contradict each other."""
    
    node1: EntityNode = Field(..., description="First cognitive object")
    node2: EntityNode = Field(..., description="Second cognitive object")
    contradiction_edge: EntityEdge = Field(..., description="Edge representing the contradiction")
    metadata: ContradictionMetadata = Field(..., description="Contradiction metadata")
    
    
class ContradictionDetectionResult(BaseModel):
    """Result of contradiction detection process."""
    
    pairs_detected: List[CognitiveObjectPair] = Field(default_factory=list)
    new_nodes_created: List[EntityNode] = Field(default_factory=list)
    edges_created: List[EntityEdge] = Field(default_factory=list)
    processing_time_ms: float = Field(default=0.0)
    success: bool = Field(default=True)
    error_message: Optional[str] = Field(default=None)


class ContradictionResolution(BaseModel):
    """Represents a resolution action for a contradiction."""
    
    contradiction_pair_id: str = Field(..., description="ID of the contradiction pair")
    resolution_type: str = Field(..., description="Type of resolution (accept_new, keep_old, merge, ignore)")
    user_choice: str = Field(..., description="User's choice for resolution")
    resolution_timestamp: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(default=None, description="Additional notes about resolution")


class ContradictionSummary(BaseModel):
    """Summary of contradictions in the system."""
    
    total_contradictions: int = Field(default=0)
    unresolved_contradictions: int = Field(default=0)
    contradiction_types: Dict[str, int] = Field(default_factory=dict)
    recent_contradictions: List[CognitiveObjectPair] = Field(default_factory=list)
    most_contradicted_concepts: List[str] = Field(default_factory=list)
