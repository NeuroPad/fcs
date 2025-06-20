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
from typing import Optional
from fastapi import FastAPI
from fastapi_utilities import repeat_at
from neo4j import AsyncGraphDatabase, AsyncDriver

from .manager import ConfidenceManager

logger = logging.getLogger(__name__)


class ConfidenceScheduler:
    """
    Scheduler for running confidence decay cycles at regular intervals.
    
    Uses fastapi-utilities to schedule periodic decay operations that
    maintain the confidence degradation for dormant CognitiveObjects.
    """
    
    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        cron_schedule: str = "0 2 * * *",  # Every day at 2 AM
        group_ids: Optional[list[str]] = None,
        batch_size: int = 100
    ):
        """
        Initialize the confidence scheduler.
        
        Parameters
        ----------
        neo4j_uri : str
            Neo4j database URI
        neo4j_user : str
            Neo4j username
        neo4j_password : str
            Neo4j password
        cron_schedule : str, optional
            Cron expression for decay schedule. Default: every day at 2 AM
        group_ids : list[str], optional
            Limit decay to specific groups
        batch_size : int, optional
            Batch size for processing nodes
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.cron_schedule = cron_schedule
        self.group_ids = group_ids
        self.batch_size = batch_size
        self.driver: Optional[AsyncDriver] = None
        self.confidence_manager: Optional[ConfidenceManager] = None
        
    async def initialize(self):
        """Initialize database connection and confidence manager."""
        self.driver = AsyncGraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password)
        )
        self.confidence_manager = ConfidenceManager(self.driver)
        logger.info(f"Confidence scheduler initialized with cron: {self.cron_schedule}")
        
    async def cleanup(self):
        """Clean up database connections."""
        if self.driver:
            await self.driver.close()
            logger.info("Confidence scheduler cleaned up")
    
    def setup_scheduler(self, app: FastAPI):
        """
        Set up the scheduled decay cycle with FastAPI.
        
        Parameters
        ----------
        app : FastAPI
            FastAPI application instance
        """
        
        @app.on_event("startup")
        async def startup_scheduler():
            """Initialize scheduler on app startup."""
            await self.initialize()
        
        @app.on_event("shutdown")
        async def shutdown_scheduler():
            """Clean up scheduler on app shutdown."""
            await self.cleanup()
        
        @app.on_event("startup")
        @repeat_at(cron=self.cron_schedule)
        async def run_confidence_decay():
            """Run the confidence decay cycle."""
            await self.run_decay_cycle()
    
    async def run_decay_cycle(self) -> dict[str, int]:
        """
        Run a single confidence decay cycle.
        
        Returns
        -------
        dict[str, int]
            Statistics about the decay cycle
        """
        if not self.confidence_manager:
            logger.error("Confidence manager not initialized")
            return {}
            
        try:
            logger.info("Starting scheduled confidence decay cycle...")
            
            stats = await self._run_dormancy_decay()
            
            logger.info(
                f"Scheduled confidence decay cycle completed: "
                f"processed={stats.get('processed', 0)}, "
                f"dormancy_decay={stats.get('dormancy_decay', 0)}, "
                f"extended_dormancy={stats.get('extended_dormancy', 0)}, "
                f"orphaned={stats.get('orphaned', 0)}"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in scheduled confidence decay cycle: {str(e)}")
            return {"error": str(e)}
    
    async def run_manual_decay(self, group_ids: Optional[list[str]] = None) -> dict[str, int]:
        """
        Run a manual decay cycle (for testing or immediate execution).
        
        Parameters
        ----------
        group_ids : list[str], optional
            Override group IDs for this run
            
        Returns
        -------
        dict[str, int]
            Statistics about the decay cycle
        """
        if not self.confidence_manager:
            await self.initialize()
            
        try:
            logger.info("Starting manual confidence decay cycle...")
            
            stats = await self._run_dormancy_decay(group_ids or self.group_ids)
            
            logger.info(
                f"Manual confidence decay cycle completed: "
                f"processed={stats.get('processed', 0)}, "
                f"dormancy_decay={stats.get('dormancy_decay', 0)}, "
                f"extended_dormancy={stats.get('extended_dormancy', 0)}, "
                f"orphaned={stats.get('orphaned', 0)}"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in manual confidence decay cycle: {str(e)}")
            return {"error": str(e)}
    
    async def _run_dormancy_decay(self, group_ids: Optional[list[str]] = None) -> dict[str, int]:
        """
        Run dormancy decay for nodes that haven't been referenced recently.
        
        Parameters
        ----------
        group_ids : list[str], optional
            Group IDs to filter nodes for decay
            
        Returns
        -------
        dict[str, int]
            Statistics about the decay cycle
        """
        stats = {
            "processed": 0,
            "dormancy_decay": 0,
            "extended_dormancy": 0,
            "orphaned": 0
        }
        
        try:
            # Build query with optional group filter
            if group_ids:
                group_filter = "AND n.group_id IN $group_ids"
                query_params = {"group_ids": group_ids}
            else:
                group_filter = ""
                query_params = {}
            
            # Get nodes with confidence data
            query = f"""
            MATCH (n:Entity)
            WHERE n.confidence IS NOT NULL
            AND n.confidence_metadata IS NOT NULL
            {group_filter}
            RETURN n.uuid as uuid, n.confidence_metadata as metadata
            LIMIT $batch_size
            """
            
            query_params["batch_size"] = self.batch_size
            
            records, _, _ = await self.driver.execute_query(query, **query_params)
            stats["processed"] = len(records)
            
            from datetime import datetime
            from .models import ConfidenceTrigger
            
            decay_updates = []
            
            for record in records:
                node_uuid = record["uuid"]
                metadata_json = record["metadata"]
                
                if metadata_json:
                    try:
                        import json
                        metadata = json.loads(metadata_json)
                        last_reference = metadata.get("last_user_validation")
                        
                        if last_reference:
                            last_reference_dt = datetime.fromisoformat(last_reference)
                            from graphiti_core.utils.datetime_utils import utc_now
                            now = utc_now()
                            days_since_reference = (now - last_reference_dt).days
                            
                            if days_since_reference > 90:
                                decay_updates.append((
                                    node_uuid,
                                    ConfidenceTrigger.EXTENDED_DORMANCY,
                                    f"Extended dormancy: {days_since_reference} days",
                                    {"days_since_reference": days_since_reference}
                                ))
                                stats["extended_dormancy"] += 1
                            elif days_since_reference > 30:
                                decay_updates.append((
                                    node_uuid,
                                    ConfidenceTrigger.DORMANCY_DECAY,
                                    f"Dormancy decay: {days_since_reference} days",
                                    {"days_since_reference": days_since_reference}
                                ))
                                stats["dormancy_decay"] += 1
                    except Exception as e:
                        logger.error(f"Error processing dormancy for node {node_uuid}: {e}")
            
            # Check for orphaned entities (no connections)
            orphaned_query = f"""
            MATCH (n:Entity)
            WHERE n.confidence IS NOT NULL
            AND n.confidence_metadata IS NOT NULL
            {group_filter}
            AND NOT (n)-[]-()
            RETURN n.uuid as uuid
            LIMIT $batch_size
            """
            
            orphaned_records, _, _ = await self.driver.execute_query(orphaned_query, **query_params)
            
            for record in orphaned_records:
                node_uuid = record["uuid"]
                decay_updates.append((
                    node_uuid,
                    ConfidenceTrigger.ORPHANED_ENTITY,
                    "Orphaned entity with no connections",
                    {}
                ))
                stats["orphaned"] += 1
            
            # Apply decay updates in batch
            if decay_updates:
                await self.confidence_manager.update_confidence_batch(decay_updates)
                logger.info(f"Applied confidence decay to {len(decay_updates)} nodes")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in dormancy decay: {e}")
            return stats


# Convenience function for easy setup
def setup_confidence_scheduler(
    app: FastAPI,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    cron_schedule: str = "0 2 * * *",
    group_ids: Optional[list[str]] = None,
    batch_size: int = 100
) -> ConfidenceScheduler:
    """
    Convenience function to set up confidence scheduler with FastAPI.
    
    Parameters
    ----------
    app : FastAPI
        FastAPI application instance
    neo4j_uri : str
        Neo4j database URI
    neo4j_user : str
        Neo4j username
    neo4j_password : str
        Neo4j password
    cron_schedule : str, optional
        Cron expression for decay schedule
    group_ids : list[str], optional
        Limit decay to specific groups
    batch_size : int, optional
        Batch size for processing nodes
        
    Returns
    -------
    ConfidenceScheduler
        Configured confidence scheduler instance
    """
    scheduler = ConfidenceScheduler(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        cron_schedule=cron_schedule,
        group_ids=group_ids,
        batch_size=batch_size
    )
    
    scheduler.setup_scheduler(app)
    return scheduler 