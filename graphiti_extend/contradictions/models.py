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

from typing import Any, Optional
from pydantic import BaseModel, Field

from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge


class ContradictionDetectionResult(BaseModel):
    """Result of contradiction detection during episode processing."""
    
    contradictions_found: bool
    contradiction_edges: list[EntityEdge]
    contradicted_nodes: list[EntityNode]
    contradicting_nodes: list[EntityNode]
    contradiction_message: Optional[str] = None


class ContradictionType(BaseModel):
    """Type of contradiction detected."""
    
    type: str = Field(..., description="Type of contradiction (e.g., 'preference_change', 'factual_contradiction')")
    description: str = Field(..., description="Human-readable description of the contradiction type")
    requires_alternative: bool = Field(..., description="Whether this type of contradiction requires an alternative to be specified")


class ContradictionContext(BaseModel):
    """Context for contradiction detection."""
    
    original_node: EntityNode
    new_node: Optional[EntityNode] = None
    contradiction_type: Optional[ContradictionType] = None
    alternative_provided: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict) 