"""
Confidence Manager for ExtendedGraphiti.

This module provides the main confidence management functionality for tracking
and updating confidence levels of Cognitive Objects in the knowledge graph.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from graphiti_core.driver.driver import GraphDriver
from graphiti_core.nodes import EntityNode
from graphiti_core.utils.datetime_utils import utc_now

from .models import (
    ConfidenceConfig,
    ConfidenceHistory,
    ConfidenceTrigger,
    ConfidenceUpdate,
    OriginType,
)

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceMetadata:
    """Extended metadata for confidence tracking."""
    origin_type: OriginType
    confidence_history: List[ConfidenceHistory]
    revisions: int = 0
    last_user_validation: Optional[datetime] = None
    supporting_co_ids: List[str] = None
    contradicting_co_ids: List[str] = None
    contradiction_resolution_status: str = "unresolved"
    dormancy_start: Optional[datetime] = None
    stability_score: float = 0.0
    
    def __post_init__(self):
        if self.supporting_co_ids is None:
            self.supporting_co_ids = []
        if self.contradicting_co_ids is None:
            self.contradicting_co_ids = []


class ConfidenceManager:
    """
    Manages confidence levels for Cognitive Objects in the knowledge graph.
    
    This class handles:
    - Initial confidence assignment based on origin type
    - Confidence updates from various triggers
    - Network reinforcement calculations
    - Contradiction impact assessment
    - Temporal decay and dormancy tracking
    - Confidence history and metadata management
    """
    
    def __init__(self, driver: GraphDriver, config: Optional[ConfidenceConfig] = None):
        """
        Initialize the ConfidenceManager.
        
        Parameters
        ----------
        driver : GraphDriver
            The graph database driver
        config : ConfidenceConfig, optional
            Configuration for confidence system. Uses defaults if not provided.
        """
        self.driver = driver
        self.config = config or ConfidenceConfig()
        
        # Cache for confidence metadata to avoid repeated database queries
        self._confidence_cache: Dict[str, ConfidenceMetadata] = {}
        self._cache_ttl = timedelta(minutes=30)  # Cache for 30 minutes
        self._last_cache_cleanup = utc_now()
    
    async def assign_initial_confidence(
        self, 
        node: EntityNode, 
        origin_type: OriginType,
        is_duplicate: bool = False
    ) -> float:
        """
        Assign initial confidence to a new Cognitive Object.
        
        Parameters
        ----------
        node : EntityNode
            The node to assign confidence to
        origin_type : OriginType
            The origin type of the node
        is_duplicate : bool, optional
            Whether this is a duplicate of an existing node (user reaffirmation)
            
        Returns
        -------
        float
            The initial confidence value
        """
        # Get base confidence based on origin type
        if origin_type == OriginType.USER_GIVEN:
            base_confidence = self.config.initial_user_given
        elif origin_type == OriginType.INFERRED:
            base_confidence = self.config.initial_inferred
        elif origin_type == OriginType.SYSTEM_SUGGESTED:
            base_confidence = self.config.initial_system_suggested
        else:
            base_confidence = self.config.initial_inferred
        
        # Add boost for user reaffirmation (duplicate found)
        if is_duplicate:
            base_confidence += self.config.initial_duplicate_found
        
        # Ensure confidence is within bounds
        confidence = max(0.0, min(1.0, base_confidence))
        
        # Create confidence metadata
        metadata = ConfidenceMetadata(
            origin_type=origin_type,
            confidence_history=[
                ConfidenceHistory(
                    timestamp=utc_now(),
                    value=confidence,
                    trigger=ConfidenceTrigger.INITIAL_ASSIGNMENT,
                    reason=f"Initial confidence assignment for {origin_type.value} origin"
                )
            ]
        )
        
        # Store metadata
        await self._store_confidence_metadata(node.uuid, confidence, metadata)
        
        logger.info(f"Assigned initial confidence {confidence} to node {node.uuid} ({origin_type.value})")
        return confidence
    
    async def update_confidence(
        self,
        node_uuid: str,
        trigger: ConfidenceTrigger,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ConfidenceUpdate]:
        """
        Update confidence for a node based on a trigger.
        
        Parameters
        ----------
        node_uuid : str
            UUID of the node to update
        trigger : ConfidenceTrigger
            The trigger causing the update
        reason : str
            Human-readable reason for the update
        metadata : Dict[str, Any], optional
            Additional metadata for the update
            
        Returns
        -------
        ConfidenceUpdate, optional
            The confidence update that was applied, or None if no update occurred
        """
        # Get current confidence and metadata
        current_confidence, confidence_metadata = await self._get_confidence_and_metadata(node_uuid)
        if current_confidence is None:
            logger.warning(f"No confidence data found for node {node_uuid}")
            return None
        
        # Calculate confidence change
        confidence_change = await self._calculate_confidence_change(trigger, metadata)
        if confidence_change == 0:
            return None
        
        # Apply change
        new_confidence = max(0.0, min(1.0, current_confidence + confidence_change))
        
        # Create update record
        update = ConfidenceUpdate(
            node_uuid=node_uuid,
            old_value=current_confidence,
            new_value=new_confidence,
            trigger=trigger,
            reason=reason,
            metadata=metadata
        )
        
        # Update metadata
        if confidence_metadata:
            confidence_metadata.confidence_history.append(
                ConfidenceHistory(
                    timestamp=update.timestamp,
                    value=new_confidence,
                    trigger=trigger,
                    reason=reason,
                    metadata=metadata
                )
            )
            
            # Update other metadata fields based on trigger
            await self._update_metadata_for_trigger(confidence_metadata, trigger, metadata)
        
        # Store updated confidence
        await self._store_confidence_metadata(node_uuid, new_confidence, confidence_metadata)
        
        logger.info(f"Updated confidence for node {node_uuid}: {current_confidence} -> {new_confidence} ({trigger.value})")
        return update
    
    async def update_confidence_batch(
        self,
        updates: List[Tuple[str, ConfidenceTrigger, str, Optional[Dict[str, Any]]]]
    ) -> List[ConfidenceUpdate]:
        """
        Update confidence for multiple nodes in batch.
        
        Parameters
        ----------
        updates : List[Tuple[str, ConfidenceTrigger, str, Optional[Dict[str, Any]]]]
            List of (node_uuid, trigger, reason, metadata) tuples
            
        Returns
        -------
        List[ConfidenceUpdate]
            List of applied confidence updates
        """
        results = []
        for node_uuid, trigger, reason, metadata in updates:
            update = await self.update_confidence(node_uuid, trigger, reason, metadata)
            if update:
                results.append(update)
        return results
    
    async def get_confidence(self, node_uuid: str) -> Optional[float]:
        """
        Get current confidence for a node.
        
        Parameters
        ----------
        node_uuid : str
            UUID of the node
            
        Returns
        -------
        float, optional
            Current confidence value, or None if not found
        """
        confidence, _ = await self._get_confidence_and_metadata(node_uuid)
        return confidence
    
    async def get_confidence_metadata(self, node_uuid: str) -> Optional[ConfidenceMetadata]:
        """
        Get confidence metadata for a node.
        
        Parameters
        ----------
        node_uuid : str
            UUID of the node
            
        Returns
        -------
        ConfidenceMetadata, optional
            Confidence metadata, or None if not found
        """
        _, metadata = await self._get_confidence_and_metadata(node_uuid)
        return metadata
    
    async def calculate_network_reinforcement(
        self, 
        node_uuid: str,
        connected_nodes: List[EntityNode]
    ) -> float:
        """
        Calculate network reinforcement boost from connected nodes.
        
        Parameters
        ----------
        node_uuid : str
            UUID of the node to calculate reinforcement for
        connected_nodes : List[EntityNode]
            List of directly connected nodes
            
        Returns
        -------
        float
            Total network reinforcement boost
        """
        total_boost = 0.0
        
        for connected_node in connected_nodes:
            if connected_node.uuid == node_uuid:
                continue
                
            connected_confidence = await self.get_confidence(connected_node.uuid)
            if connected_confidence and connected_confidence > self.config.propagation_threshold:
                # Direct connection boost
                boost = connected_confidence * self.config.direct_connection_boost_factor
                total_boost += boost
                
                # Check for structural support (3+ high-confidence connections)
                high_confidence_connections = 0
                for other_node in connected_nodes:
                    if other_node.uuid != node_uuid and other_node.uuid != connected_node.uuid:
                        other_confidence = await self.get_confidence(other_node.uuid)
                        if other_confidence and other_confidence > self.config.structural_support_threshold:
                            high_confidence_connections += 1
                
                if high_confidence_connections >= self.config.structural_support_min_connections:
                    total_boost += self.config.structural_support_boost
        
        return min(0.2, total_boost)  # Cap at 0.2 total boost
    
    async def detect_origin_type(
        self, 
        node: EntityNode, 
        episode_content: str,
        is_duplicate: bool = False
    ) -> OriginType:
        """
        Detect the origin type of a node based on context.
        
        Parameters
        ----------
        node : EntityNode
            The node to analyze
        episode_content : str
            The episode content for context analysis
        is_duplicate : bool
            Whether this is a duplicate of an existing node
            
        Returns
        -------
        OriginType
            The detected origin type
        """
        # If it's a duplicate, it's likely user reaffirmation
        if is_duplicate:
            return OriginType.USER_GIVEN
        
        # Simple heuristic: check if node name appears in episode content
        # This is a basic implementation - could be enhanced with LLM analysis
        node_name_lower = node.name.lower()
        episode_lower = episode_content.lower()
        
        # Check for direct mentions
        if node_name_lower in episode_lower:
            # Look for patterns that suggest user-given vs inferred
            user_given_indicators = [
                "i am", "i'm", "i like", "i love", "i prefer", "i hate", "i don't like",
                "my favorite", "my name is", "i work", "i live", "i have"
            ]
            
            for indicator in user_given_indicators:
                if indicator in episode_lower and node_name_lower in episode_lower:
                    return OriginType.USER_GIVEN
            
            return OriginType.INFERRED
        
        return OriginType.SYSTEM_SUGGESTED
    
    async def apply_contradiction_penalties(
        self,
        contradicted_node_uuid: str,
        contradicting_node_uuid: str,
        contradiction_strength: float = 1.0
    ) -> Optional[ConfidenceUpdate]:
        """
        Apply contradiction penalties to a contradicted node.
        
        Parameters
        ----------
        contradicted_node_uuid : str
            UUID of the node being contradicted
        contradicting_node_uuid : str
            UUID of the node doing the contradicting
        contradiction_strength : float, optional
            Strength of the contradiction (0.0 to 1.0)
            
        Returns
        -------
        ConfidenceUpdate, optional
            The confidence update that was applied
        """
        # Get contradicting node's confidence
        contradicting_confidence = await self.get_confidence(contradicting_node_uuid)
        if not contradicting_confidence or contradicting_confidence < self.config.network_support_threshold:
            return None
        
        # Calculate penalty based on contradiction strength
        base_penalty = self.config.contradiction_penalty
        adjusted_penalty = base_penalty * contradiction_strength
        
        # Check if this is a repeated contradiction
        metadata = await self.get_confidence_metadata(contradicted_node_uuid)
        if metadata and contradicting_node_uuid in metadata.contradicting_co_ids:
            adjusted_penalty = self.config.repeated_contradiction_penalty
        
        # Apply the penalty
        return await self.update_confidence(
            contradicted_node_uuid,
            ConfidenceTrigger.CONTRADICTION_DETECTED,
            f"Contradicted by node {contradicting_node_uuid} with confidence {contradicting_confidence}",
            {
                "contradicting_node_uuid": contradicting_node_uuid,
                "contradiction_strength": contradiction_strength,
                "penalty_applied": adjusted_penalty
            }
        )
    
    async def _calculate_confidence_change(
        self, 
        trigger: ConfidenceTrigger, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate confidence change for a given trigger."""
        if trigger == ConfidenceTrigger.USER_REAFFIRMATION:
            return self.config.user_reaffirmation_boost
        elif trigger == ConfidenceTrigger.USER_REFERENCE:
            return self.config.user_reference_boost
        elif trigger == ConfidenceTrigger.USER_REASONING:
            return self.config.user_reasoning_boost
        elif trigger == ConfidenceTrigger.NETWORK_SUPPORT:
            return self.config.network_support_boost
        elif trigger == ConfidenceTrigger.REASONING_USAGE:
            return self.config.reasoning_usage_boost
        elif trigger == ConfidenceTrigger.STRUCTURAL_SUPPORT:
            return self.config.structural_support_boost
        elif trigger == ConfidenceTrigger.INDIRECT_SUPPORT:
            return self.config.indirect_support_boost
        elif trigger == ConfidenceTrigger.CONSISTENCY_CHECK:
            return self.config.consistency_boost
        elif trigger == ConfidenceTrigger.EXTERNAL_CORROBORATION:
            return self.config.external_corroboration_boost
        elif trigger == ConfidenceTrigger.CONTRADICTION_DETECTED:
            penalty = metadata.get("penalty_applied", self.config.contradiction_penalty) if metadata else self.config.contradiction_penalty
            return -penalty
        elif trigger == ConfidenceTrigger.REPEATED_CONTRADICTION:
            return -self.config.repeated_contradiction_penalty
        elif trigger == ConfidenceTrigger.USER_CORRECTION:
            return -self.config.user_correction_penalty
        elif trigger == ConfidenceTrigger.USER_UNCERTAINTY:
            return -self.config.user_uncertainty_penalty
        elif trigger == ConfidenceTrigger.DORMANCY_DECAY:
            return -self.config.dormancy_decay_penalty
        elif trigger == ConfidenceTrigger.EXTENDED_DORMANCY:
            return -self.config.extended_dormancy_penalty
        elif trigger == ConfidenceTrigger.ORPHANED_ENTITY:
            return -self.config.orphaned_entity_penalty
        elif trigger == ConfidenceTrigger.DUPLICATE_FOUND:
            return self.config.initial_duplicate_found
        
        return 0.0
    
    async def _get_confidence_and_metadata(
        self, 
        node_uuid: str
    ) -> Tuple[Optional[float], Optional[ConfidenceMetadata]]:
        """Get confidence value and metadata for a node."""
        # Check cache first
        if node_uuid in self._confidence_cache:
            metadata = self._confidence_cache[node_uuid]
            if metadata.confidence_history:
                return metadata.confidence_history[-1].value, metadata
        
        # Query database
        query = """
        MATCH (n:Entity {uuid: $uuid})
        RETURN n.confidence as confidence, n.confidence_metadata as metadata
        """
        
        try:
            records, _, _ = await self.driver.execute_query(query, uuid=node_uuid)
            if records:
                record = records[0]
                confidence = record.get("confidence")
                metadata_json = record.get("metadata")
                
                if metadata_json:
                    # Parse metadata
                    metadata = self._parse_confidence_metadata(metadata_json)
                else:
                    metadata = None
                
                # Cache the result
                if metadata:
                    self._confidence_cache[node_uuid] = metadata
                
                return confidence, metadata
            
        except Exception as e:
            logger.error(f"Error getting confidence for node {node_uuid}: {e}")
        
        return None, None
    
    async def _store_confidence_metadata(
        self, 
        node_uuid: str, 
        confidence: float, 
        metadata: Optional[ConfidenceMetadata]
    ):
        """Store confidence value and metadata in the database."""
        query = """
        MATCH (n:Entity {uuid: $uuid})
        SET n.confidence = $confidence, n.confidence_metadata = $metadata
        """
        
        try:
            metadata_json = self._serialize_confidence_metadata(metadata) if metadata else None
            await self.driver.execute_query(
                query, 
                uuid=node_uuid, 
                confidence=confidence, 
                metadata=metadata_json
            )
            
            # Update cache
            if metadata:
                self._confidence_cache[node_uuid] = metadata
            
        except Exception as e:
            logger.error(f"Error storing confidence for node {node_uuid}: {e}")
    
    async def _update_metadata_for_trigger(
        self, 
        metadata: ConfidenceMetadata, 
        trigger: ConfidenceTrigger, 
        trigger_metadata: Optional[Dict[str, Any]]
    ):
        """Update metadata fields based on trigger."""
        if trigger == ConfidenceTrigger.USER_REAFFIRMATION:
            metadata.last_user_validation = utc_now()
        elif trigger == ConfidenceTrigger.USER_CORRECTION:
            metadata.revisions += 1
        elif trigger == ConfidenceTrigger.CONTRADICTION_DETECTED:
            if trigger_metadata and "contradicting_node_uuid" in trigger_metadata:
                contradicting_uuid = trigger_metadata["contradicting_node_uuid"]
                if contradicting_uuid not in metadata.contradicting_co_ids:
                    metadata.contradicting_co_ids.append(contradicting_uuid)
        elif trigger == ConfidenceTrigger.NETWORK_SUPPORT:
            if trigger_metadata and "supporting_node_uuid" in trigger_metadata:
                supporting_uuid = trigger_metadata["supporting_node_uuid"]
                if supporting_uuid not in metadata.supporting_co_ids:
                    metadata.supporting_co_ids.append(supporting_uuid)
    
    def _parse_confidence_metadata(self, metadata_json: str) -> ConfidenceMetadata:
        """Parse confidence metadata from JSON string."""
        try:
            import json
            data = json.loads(metadata_json)
            
            # Parse confidence history
            history = []
            for entry in data.get("confidence_history", []):
                history.append(ConfidenceHistory(**entry))
            
            # Parse origin type
            origin_type = OriginType(data.get("origin_type", "inferred"))
            
            # Parse dates
            last_user_validation = None
            if data.get("last_user_validation"):
                last_user_validation = datetime.fromisoformat(data["last_user_validation"])
            
            dormancy_start = None
            if data.get("dormancy_start"):
                dormancy_start = datetime.fromisoformat(data["dormancy_start"])
            
            return ConfidenceMetadata(
                origin_type=origin_type,
                confidence_history=history,
                revisions=data.get("revisions", 0),
                last_user_validation=last_user_validation,
                supporting_co_ids=data.get("supporting_co_ids", []),
                contradicting_co_ids=data.get("contradicting_co_ids", []),
                contradiction_resolution_status=data.get("contradiction_resolution_status", "unresolved"),
                dormancy_start=dormancy_start,
                stability_score=data.get("stability_score", 0.0)
            )
            
        except Exception as e:
            logger.error(f"Error parsing confidence metadata: {e}")
            return ConfidenceMetadata(
                origin_type=OriginType.INFERRED,
                confidence_history=[]
            )
    
    def _serialize_confidence_metadata(self, metadata: ConfidenceMetadata) -> str:
        """Serialize confidence metadata to JSON string."""
        try:
            import json
            
            data = {
                "origin_type": metadata.origin_type.value,
                "confidence_history": [
                    {
                        "timestamp": entry.timestamp.isoformat(),
                        "value": entry.value,
                        "trigger": entry.trigger.value,
                        "reason": entry.reason,
                        "metadata": entry.metadata
                    }
                    for entry in metadata.confidence_history
                ],
                "revisions": metadata.revisions,
                "last_user_validation": metadata.last_user_validation.isoformat() if metadata.last_user_validation else None,
                "supporting_co_ids": metadata.supporting_co_ids,
                "contradicting_co_ids": metadata.contradicting_co_ids,
                "contradiction_resolution_status": metadata.contradiction_resolution_status,
                "dormancy_start": metadata.dormancy_start.isoformat() if metadata.dormancy_start else None,
                "stability_score": metadata.stability_score
            }
            
            return json.dumps(data)
            
        except Exception as e:
            logger.error(f"Error serializing confidence metadata: {e}")
            return "{}"
    
    async def _cleanup_cache(self):
        """Clean up expired cache entries."""
        now = utc_now()
        if now - self._last_cache_cleanup > self._cache_ttl:
            expired_keys = []
            for key, metadata in self._confidence_cache.items():
                if metadata.confidence_history:
                    last_update = metadata.confidence_history[-1].timestamp
                    if now - last_update > self._cache_ttl:
                        expired_keys.append(key)
            
            for key in expired_keys:
                del self._confidence_cache[key]
            
            self._last_cache_cleanup = now 