"""
Confidence system models and data structures.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OriginType(str, Enum):
    """Origin types for Cognitive Objects."""
    USER_GIVEN = "user_given"
    INFERRED = "inferred" 
    SYSTEM_SUGGESTED = "system_suggested"


class ConfidenceTrigger(str, Enum):
    """Triggers that cause confidence updates."""
    # User validation triggers
    USER_REAFFIRMATION = "user_reaffirmation"
    USER_REFERENCE = "user_reference"
    USER_REASONING = "user_reasoning"
    USER_CORRECTION = "user_correction"
    USER_UNCERTAINTY = "user_uncertainty"
    
    # Network reinforcement triggers
    NETWORK_SUPPORT = "network_support"
    REASONING_USAGE = "reasoning_usage"
    STRUCTURAL_SUPPORT = "structural_support"
    INDIRECT_SUPPORT = "indirect_support"
    
    # System validation triggers
    CONSISTENCY_CHECK = "consistency_check"
    EXTERNAL_CORROBORATION = "external_corroboration"
    
    # Contradiction triggers
    CONTRADICTION_DETECTED = "contradiction_detected"
    REPEATED_CONTRADICTION = "repeated_contradiction"
    CONTRADICTION_RESOLUTION = "contradiction_resolution"
    
    # Temporal triggers
    DORMANCY_DECAY = "dormancy_decay"
    EXTENDED_DORMANCY = "extended_dormancy"
    ORPHANED_ENTITY = "orphaned_entity"
    
    # Initial assignment
    INITIAL_ASSIGNMENT = "initial_assignment"
    DUPLICATE_FOUND = "duplicate_found"


class ConfidenceHistory(BaseModel):
    """History entry for confidence changes."""
    timestamp: datetime
    value: float = Field(ge=0.0, le=1.0)
    trigger: ConfidenceTrigger
    reason: str
    metadata: Optional[Dict[str, Any]] = None


class ConfidenceUpdate(BaseModel):
    """Represents a confidence update operation."""
    node_uuid: str
    old_value: float
    new_value: float
    trigger: ConfidenceTrigger
    reason: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConfidenceConfig(BaseModel):
    """Configuration for confidence system."""
    # Initial confidence values
    initial_user_given: float = 0.8
    initial_inferred: float = 0.5
    initial_system_suggested: float = 0.4
    initial_duplicate_found: float = 0.1  # Additional boost for user reaffirmation
    
    # Confidence increase values
    user_reaffirmation_boost: float = 0.1
    user_reference_boost: float = 0.05
    user_reasoning_boost: float = 0.03
    network_support_boost: float = 0.1
    reasoning_usage_boost: float = 0.05
    structural_support_boost: float = 0.05
    indirect_support_boost: float = 0.03
    consistency_boost: float = 0.02
    external_corroboration_boost: float = 0.01
    
    # Confidence decrease values
    contradiction_penalty: float = 0.3
    repeated_contradiction_penalty: float = 0.15
    user_correction_penalty: float = 0.1
    user_uncertainty_penalty: float = 0.1
    soft_contradiction_penalty: float = 0.05
    dormancy_decay_penalty: float = 0.05
    extended_dormancy_penalty: float = 0.1
    orphaned_entity_penalty: float = 0.15
    
    # Thresholds
    network_support_threshold: float = 0.75
    structural_support_threshold: float = 0.7
    structural_support_min_connections: int = 3
    dormancy_threshold_days: int = 30
    extended_dormancy_threshold_days: int = 90
    unstable_confidence_threshold: float = 0.4
    deletion_consideration_threshold: float = 0.2
    
    # Network propagation
    direct_connection_boost_factor: float = 0.1
    indirect_connection_boost_factor: float = 0.05
    propagation_threshold: float = 0.7 