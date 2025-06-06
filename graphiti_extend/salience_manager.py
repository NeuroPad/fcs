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

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set, Tuple
from time import time

from neo4j import AsyncDriver
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
from graphiti_core.utils.datetime_utils import utc_now
from graphiti_core.helpers import DEFAULT_DATABASE

logger = logging.getLogger(__name__)


def _safe_datetime_to_iso(dt: Any) -> str:
    """
    Safely convert any datetime-like object to ISO format string.
    
    Handles both Python datetime objects and Neo4j DateTime objects.
    """
    if dt is None:
        return utc_now().isoformat()
    
    # If it's already a string, return it
    if isinstance(dt, str):
        return dt
    
    # If it has to_native method (Neo4j DateTime), convert it
    if hasattr(dt, 'to_native'):
        return dt.to_native().isoformat()
    
    # If it's a Python datetime, use isoformat
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    
    # Fallback to current time
    return utc_now().isoformat()


class SalienceConfig:
    """Configuration for salience calculations and decay."""
    
    # Direct activation values
    CONVERSATION_MENTION = 0.3
    DUPLICATE_FOUND = 0.25
    REASONING_USAGE = 0.2
    STRUCTURAL_BOOST = 0.15
    NETWORK_PROXIMITY = 0.1
    CONTRADICTION_INVOLVEMENT = 0.1
    
    # Network reinforcement
    BASE_NETWORK_REINFORCEMENT = 0.05
    MAX_HOP_DISTANCE = 2
    CONNECTIVITY_BOOST_FACTOR = 0.05
    
    # Temporal factors
    RECENCY_BOOST_RECENT = 1.5    # < 1 day
    RECENCY_BOOST_NORMAL = 1.0    # < 1 week
    RECENCY_BOOST_OLD = 0.8       # > 1 week
    
    # Decay rates
    BASE_DECAY_RATE = 0.02        # per week
    NO_REFERENCE_DECAY = 0.1      # 14+ days
    ORPHANED_DECAY = 0.2          # no connections
    LOW_CONFIDENCE_DECAY = 0.15   # confidence < 0.3
    
    # Deletion thresholds
    MIN_SALIENCE_THRESHOLD = 0.1
    DELETION_SALIENCE_THRESHOLD = 0.05
    ORPHAN_DELETION_DAYS = 30
    LOW_CONFIDENCE_DELETION_DAYS = 60
    
    # Limits
    MAX_SALIENCE = 1.0
    MIN_SALIENCE = 0.0
    STRUCTURAL_CONNECTION_THRESHOLD = 3
    HIGH_CONFIDENCE_THRESHOLD = 0.75


class SalienceManager:
    """
    Manages salience updates and decay for CognitiveObject nodes.
    
    Implements brain-like reinforcement learning where:
    - Frequently accessed concepts become more salient
    - Connected concepts reinforce each other
    - Unused concepts naturally decay and may be forgotten
    """
    
    def __init__(self, driver: AsyncDriver, config: SalienceConfig = None):
        self.driver = driver
        self.config = config or SalienceConfig()
        
    async def update_direct_salience(
        self,
        nodes: List[EntityNode],
        trigger_type: str,
        episode_timestamp: datetime = None
    ) -> List[EntityNode]:
        """
        Apply direct salience updates to nodes based on activation triggers.
        
        Parameters
        ----------
        nodes : List[EntityNode]
            Nodes to update
        trigger_type : str
            Type of activation: 'conversation_mention', 'duplicate_found', 
            'reasoning_usage', 'contradiction_involvement'
        episode_timestamp : datetime, optional
            When the activation occurred
            
        Returns
        -------
        List[EntityNode]
            Updated nodes with new salience values
        """
        if not nodes:
            return nodes
            
        # Get base increment for trigger type
        base_increments = {
            'conversation_mention': self.config.CONVERSATION_MENTION,
            'duplicate_found': self.config.DUPLICATE_FOUND,
            'reasoning_usage': self.config.REASONING_USAGE,
            'contradiction_involvement': self.config.CONTRADICTION_INVOLVEMENT,
        }
        
        base_increment = base_increments.get(trigger_type, 0.1)
        current_time = episode_timestamp or utc_now()
        
        updated_nodes = []
        for node in nodes:
            if not self._is_cognitive_object(node):
                updated_nodes.append(node)
                continue
                
            # Calculate reinforcement weight
            reinforcement_weight = await self._calculate_reinforcement_weight(
                node, base_increment, current_time
            )
            
            # Update salience
            current_salience = node.attributes.get('salience', 0.5)
            new_salience = min(
                current_salience + reinforcement_weight,
                self.config.MAX_SALIENCE
            )
            
            # Update node attributes
            node.attributes['salience'] = new_salience
            # Don't store last_salience_update in attributes - let graphiti handle datetime fields
            # node.attributes['last_salience_update'] = _safe_datetime_to_iso(current_time)
            
            logger.debug(
                f"Direct salience update: {node.name} "
                f"({current_salience:.3f} -> {new_salience:.3f}) "
                f"trigger={trigger_type}, weight={reinforcement_weight:.3f}"
            )
            
            updated_nodes.append(node)
            
        return updated_nodes
    
    async def propagate_network_reinforcement(
        self,
        activated_nodes: List[EntityNode],
        group_ids: List[str] = None
    ) -> int:
        """
        Apply network pathway reinforcement to connected CognitiveObjects.
        
        Parameters
        ----------
        activated_nodes : List[EntityNode]
            Nodes that were directly activated
        group_ids : List[str], optional
            Limit reinforcement to specific groups
            
        Returns
        -------
        int
            Number of nodes that received network reinforcement
        """
        if not activated_nodes:
            return 0
            
        cognitive_activated = [
            node for node in activated_nodes 
            if self._is_cognitive_object(node)
        ]
        
        if not cognitive_activated:
            return 0
            
        reinforcement_map = {}
        
        for activated_node in cognitive_activated:
            # Find connected nodes within hop distance
            connected_nodes = await self._find_connected_cognitive_objects(
                activated_node.uuid, 
                self.config.MAX_HOP_DISTANCE,
                group_ids
            )
            
            activated_salience = activated_node.attributes.get('salience', 0.5)
            
            for connected_uuid, hop_distance, edge_confidence in connected_nodes:
                if connected_uuid == activated_node.uuid:
                    continue  # Skip self
                    
                # Calculate pathway strength
                pathway_strength = (1.0 / hop_distance) * edge_confidence * activated_salience
                reinforcement = self.config.BASE_NETWORK_REINFORCEMENT * pathway_strength
                
                # Accumulate reinforcement for this node
                if connected_uuid not in reinforcement_map:
                    reinforcement_map[connected_uuid] = 0
                reinforcement_map[connected_uuid] += reinforcement
        
        # Apply network reinforcement
        if reinforcement_map:
            await self._apply_network_reinforcement_batch(reinforcement_map)
            
        logger.info(
            f"Applied network reinforcement to {len(reinforcement_map)} nodes "
            f"from {len(cognitive_activated)} activated nodes"
        )
        
        return len(reinforcement_map)
    
    async def apply_structural_boosts(
        self,
        nodes: List[EntityNode]
    ) -> List[EntityNode]:
        """
        Apply structural importance boosts to well-connected nodes.
        
        Parameters
        ----------
        nodes : List[EntityNode]
            Nodes to check for structural importance
            
        Returns
        -------
        List[EntityNode]
            Updated nodes with structural boosts applied
        """
        updated_nodes = []
        
        for node in nodes:
            if not self._is_cognitive_object(node):
                updated_nodes.append(node)
                continue
                
            # Count high-confidence connections
            high_conf_connections = await self._count_high_confidence_connections(node.uuid)
            
            if high_conf_connections >= self.config.STRUCTURAL_CONNECTION_THRESHOLD:
                current_salience = node.attributes.get('salience', 0.5)
                new_salience = min(
                    current_salience + self.config.STRUCTURAL_BOOST,
                    self.config.MAX_SALIENCE
                )
                
                node.attributes['salience'] = new_salience
                # Don't store last_salience_update in attributes - let graphiti handle datetime fields
                # node.attributes['last_salience_update'] = _safe_datetime_to_iso(utc_now())
                
                logger.debug(
                    f"Structural boost: {node.name} "
                    f"({current_salience:.3f} -> {new_salience:.3f}) "
                    f"connections={high_conf_connections}"
                )
            
            updated_nodes.append(node)
            
        return updated_nodes
    
    async def run_decay_cycle(
        self,
        group_ids: List[str] = None,
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Run temporal decay and cleanup cycle for CognitiveObjects.
        
        Parameters
        ----------
        group_ids : List[str], optional
            Limit decay to specific groups
        batch_size : int
            Number of nodes to process per batch
            
        Returns
        -------
        Dict[str, int]
            Statistics about the decay cycle
        """
        start_time = time()
        stats = {
            'processed': 0,
            'decayed': 0,
            'deleted': 0,
            'orphaned': 0,
            'low_confidence': 0
        }
        
        logger.info("Starting salience decay cycle...")
        
        # Get all CognitiveObjects in batches
        offset = 0
        while True:
            cognitive_objects = await self._get_cognitive_objects_batch(
                group_ids, batch_size, offset
            )
            
            if not cognitive_objects:
                break
                
            batch_stats = await self._process_decay_batch(cognitive_objects)
            
            # Update overall stats
            for key, value in batch_stats.items():
                stats[key] += value
                
            offset += batch_size
            
        end_time = time()
        duration = end_time - start_time
        
        logger.info(
            f"Decay cycle completed in {duration:.2f}s: "
            f"processed={stats['processed']}, decayed={stats['decayed']}, "
            f"deleted={stats['deleted']}, orphaned={stats['orphaned']}"
        )
        
        return stats
    
    async def _calculate_reinforcement_weight(
        self,
        node: EntityNode,
        base_increment: float,
        current_time: datetime
    ) -> float:
        """Calculate the reinforcement weight for a node activation."""
        
        # Get node properties
        confidence = node.attributes.get('confidence', 0.7)
        # Skip recency calculation since we're not tracking last_salience_update anymore
        # last_update_str = node.attributes.get('last_salience_update')
        
        # Calculate recency multiplier (default to normal since we don't track update times)
        recency_multiplier = self.config.RECENCY_BOOST_NORMAL
        # if last_update_str:
        #     try:
        #         last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
        #         time_diff = current_time - last_update
        #         
        #         if time_diff < timedelta(days=1):
        #             recency_multiplier = self.config.RECENCY_BOOST_RECENT
        #         elif time_diff < timedelta(days=7):
        #             recency_multiplier = self.config.RECENCY_BOOST_NORMAL
        #         else:
        #             recency_multiplier = self.config.RECENCY_BOOST_OLD
        #     except (ValueError, TypeError):
        #         pass
        
        # Calculate connectivity multiplier
        connection_count = await self._get_connection_count(node.uuid)
        connectivity_multiplier = 1 + (connection_count * self.config.CONNECTIVITY_BOOST_FACTOR)
        
        # Calculate confidence multiplier
        confidence_multiplier = 0.7 + (confidence * 0.3)
        
        # Final reinforcement weight
        reinforcement_weight = (
            base_increment * 
            connectivity_multiplier * 
            recency_multiplier * 
            confidence_multiplier
        )
        
        return reinforcement_weight
    
    async def _find_connected_cognitive_objects(
        self,
        node_uuid: str,
        max_hops: int,
        group_ids: List[str] = None
    ) -> List[Tuple[str, int, float]]:
        """
        Find connected CognitiveObjects within hop distance.
        
        Returns list of (node_uuid, hop_distance, edge_confidence) tuples.
        """
        group_filter = ""
        if group_ids:
            group_filter = "AND n.group_id IN $group_ids"
            
        query = f"""
        MATCH path = (start:Entity {{uuid: $node_uuid}})-[*1..{max_hops}]-(n:Entity)
        WHERE 'CognitiveObject' IN n.labels {group_filter}
        WITH n, length(path) as hop_distance,
             [r in relationships(path) | coalesce(r.confidence, 0.5)] as edge_confidences
        RETURN DISTINCT n.uuid as uuid, hop_distance, 
               reduce(conf = 1.0, c in edge_confidences | conf * c) as path_confidence
        ORDER BY hop_distance, path_confidence DESC
        LIMIT 50
        """
        
        records, _, _ = await self.driver.execute_query(
            query,
            node_uuid=node_uuid,
            group_ids=group_ids,
            database_=DEFAULT_DATABASE,
            routing_='r'
        )
        
        return [(record['uuid'], record['hop_distance'], record['path_confidence']) 
                for record in records]
    
    async def _apply_network_reinforcement_batch(
        self,
        reinforcement_map: Dict[str, float]
    ) -> None:
        """Apply network reinforcement to a batch of nodes."""
        
        if not reinforcement_map:
            return
            
        # Build batch update query
        query = """
        UNWIND $updates as update
        MATCH (n:Entity {uuid: update.uuid})
        WHERE 'CognitiveObject' IN n.labels
        SET n.salience = CASE 
            WHEN n.salience IS NULL THEN 
                CASE WHEN 0.5 + update.reinforcement > 1.0 THEN 1.0 ELSE 0.5 + update.reinforcement END
            ELSE 
                CASE WHEN coalesce(n.salience, 0.5) + update.reinforcement > 1.0 
                     THEN 1.0 
                     ELSE coalesce(n.salience, 0.5) + update.reinforcement 
                END
        END
        RETURN n.uuid, n.salience
        """
        
        updates = [
            {'uuid': uuid, 'reinforcement': reinforcement}
            for uuid, reinforcement in reinforcement_map.items()
        ]
        
        await self.driver.execute_query(
            query,
            updates=updates,
            database_=DEFAULT_DATABASE
        )
    
    async def _count_high_confidence_connections(self, node_uuid: str) -> int:
        """Count connections to high-confidence nodes."""
        
        query = """
        MATCH (n:Entity {uuid: $node_uuid})-[r]-(connected:Entity)
        WHERE 'CognitiveObject' IN connected.labels 
        AND coalesce(connected.confidence, 0.7) > $threshold
        RETURN count(DISTINCT connected) as count
        """
        
        records, _, _ = await self.driver.execute_query(
            query,
            node_uuid=node_uuid,
            threshold=self.config.HIGH_CONFIDENCE_THRESHOLD,
            database_=DEFAULT_DATABASE,
            routing_='r'
        )
        
        return records[0]['count'] if records else 0
    
    async def _get_connection_count(self, node_uuid: str) -> int:
        """Get total connection count for a node."""
        
        query = """
        MATCH (n:Entity {uuid: $node_uuid})-[r]-(connected)
        RETURN count(DISTINCT connected) as count
        """
        
        records, _, _ = await self.driver.execute_query(
            query,
            node_uuid=node_uuid,
            database_=DEFAULT_DATABASE,
            routing_='r'
        )
        
        return records[0]['count'] if records else 0
    
    async def _get_cognitive_objects_batch(
        self,
        group_ids: List[str] = None,
        batch_size: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get a batch of CognitiveObjects for processing."""
        
        group_filter = ""
        if group_ids:
            group_filter = "AND n.group_id IN $group_ids"
            
        query = f"""
        MATCH (n:Entity)
        WHERE 'CognitiveObject' IN n.labels {group_filter}
        RETURN n.uuid as uuid, n.salience as salience, n.confidence as confidence,
               n.updated_at as updated_at, n.created_at as created_at,
               n.name as name
        ORDER BY n.uuid
        SKIP $offset LIMIT $batch_size
        """
        
        records, _, _ = await self.driver.execute_query(
            query,
            group_ids=group_ids,
            offset=offset,
            batch_size=batch_size,
            database_=DEFAULT_DATABASE,
            routing_='r'
        )
        
        return [dict(record) for record in records]
    
    async def _process_decay_batch(
        self,
        cognitive_objects: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Process decay for a batch of CognitiveObjects."""
        
        stats = {
            'processed': 0,
            'decayed': 0,
            'deleted': 0,
            'orphaned': 0,
            'low_confidence': 0
        }
        
        current_time = utc_now()
        updates = []
        deletions = []
        
        for obj in cognitive_objects:
            stats['processed'] += 1
            
            uuid = obj['uuid']
            current_salience = obj.get('salience', 0.5)
            confidence = obj.get('confidence', 0.7)
            updated_at = obj.get('updated_at')
            created_at = obj.get('created_at')
            
            # Calculate time since last update
            days_since_update = 0
            if updated_at:
                try:
                    updated_time = updated_at.to_native() if hasattr(updated_at, 'to_native') else updated_at
                    days_since_update = (current_time - updated_time).days
                except (ValueError, TypeError):
                    pass
            elif created_at:
                try:
                    created_time = created_at.to_native() if hasattr(created_at, 'to_native') else created_at
                    days_since_update = (current_time - created_time).days
                except (ValueError, TypeError):
                    pass
            
            # Get connection count
            connection_count = await self._get_connection_count(uuid)
            
            # Calculate decay
            decay_amount = await self._calculate_decay_amount(
                current_salience, confidence, days_since_update, connection_count
            )
            
            new_salience = max(
                current_salience - decay_amount,
                self.config.MIN_SALIENCE
            )
            
            # Check deletion criteria
            should_delete = await self._should_delete_node(
                uuid, new_salience, confidence, connection_count, days_since_update
            )
            
            if should_delete:
                deletions.append(uuid)
                stats['deleted'] += 1
                if connection_count == 0:
                    stats['orphaned'] += 1
                if confidence < 0.3:
                    stats['low_confidence'] += 1
            elif decay_amount > 0:
                updates.append({
                    'uuid': uuid,
                    'salience': new_salience
                })
                stats['decayed'] += 1
        
        # Apply updates and deletions
        if updates:
            await self._apply_decay_updates(updates)
        if deletions:
            await self._delete_nodes(deletions)
            
        return stats
    
    async def _calculate_decay_amount(
        self,
        current_salience: float,
        confidence: float,
        days_since_update: int,
        connection_count: int
    ) -> float:
        """Calculate the decay amount for a node."""
        
        decay_amount = self.config.BASE_DECAY_RATE
        
        # No reference decay
        if days_since_update >= 14:
            decay_amount += self.config.NO_REFERENCE_DECAY
            
        # Orphaned node decay
        if connection_count == 0:
            decay_amount += self.config.ORPHANED_DECAY
            
        # Low confidence decay
        if confidence < 0.3:
            decay_amount += self.config.LOW_CONFIDENCE_DECAY
            
        # Connection-based decay resistance
        decay_resistance = min(0.8, connection_count * 0.1)
        final_decay = decay_amount * (1 - decay_resistance)
        
        return final_decay
    
    async def _should_delete_node(
        self,
        uuid: str,
        salience: float,
        confidence: float,
        connection_count: int,
        days_since_update: int
    ) -> bool:
        """Determine if a node should be deleted."""
        
        # Orphaned nodes with low salience
        if (salience < self.config.MIN_SALIENCE_THRESHOLD and 
            connection_count == 0 and 
            days_since_update >= self.config.ORPHAN_DELETION_DAYS):
            return True
            
        # Low confidence, low salience nodes
        if (salience < self.config.DELETION_SALIENCE_THRESHOLD and 
            confidence < 0.3 and 
            days_since_update >= self.config.LOW_CONFIDENCE_DELETION_DAYS):
            return True
            
        # Explicitly dismissed nodes
        dismissed_flags = await self._check_dismissed_flags(uuid)
        if dismissed_flags and salience < 0.2:
            return True
            
        return False
    
    async def _apply_decay_updates(self, updates: List[Dict[str, Any]]) -> None:
        """Apply decay updates to nodes."""
        
        query = """
        UNWIND $updates as update
        MATCH (n:Entity {uuid: update.uuid})
        SET n.salience = update.salience
        """
        
        await self.driver.execute_query(
            query,
            updates=updates,
            database_=DEFAULT_DATABASE
        )
    
    async def _delete_nodes(self, node_uuids: List[str]) -> None:
        """Delete nodes and their relationships."""
        
        query = """
        UNWIND $uuids as uuid
        MATCH (n:Entity {uuid: uuid})
        WHERE 'CognitiveObject' IN n.labels
        DETACH DELETE n
        """
        
        await self.driver.execute_query(
            query,
            uuids=node_uuids,
            database_=DEFAULT_DATABASE
        )
        
        logger.info(f"Deleted {len(node_uuids)} forgotten CognitiveObjects")
    
    async def _check_dismissed_flags(self, uuid: str) -> bool:
        """Check if a node has been explicitly dismissed."""
        
        query = """
        MATCH (n:Entity {uuid: $uuid})
        RETURN 'dismissed' IN coalesce(n.flags, []) as dismissed
        """
        
        records, _, _ = await self.driver.execute_query(
            query,
            uuid=uuid,
            database_=DEFAULT_DATABASE,
            routing_='r'
        )
        
        return records[0]['dismissed'] if records else False
    
    def _is_cognitive_object(self, node: EntityNode) -> bool:
        """Check if a node is a CognitiveObject."""
        return 'CognitiveObject' in node.labels 