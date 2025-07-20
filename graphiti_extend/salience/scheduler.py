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

from .manager import SalienceManager

logger = logging.getLogger(__name__)


class SalienceScheduler:
    """
    Scheduler for running salience decay cycles at regular intervals.
    
    Uses fastapi-utilities to schedule periodic decay operations that
    maintain the brain-like forgetting mechanism for CognitiveObjects.
    """
    
    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        cron_schedule: str = "0 */4 * * *",  # Every 4 hours
        group_ids: Optional[list[str]] = None,
        batch_size: int = 100
    ):
        """
        Initialize the salience scheduler.
        
        Parameters
        ----------
        neo4j_uri : str
            Neo4j database URI
        neo4j_user : str
            Neo4j username
        neo4j_password : str
            Neo4j password
        cron_schedule : str, optional
            Cron expression for decay schedule. Default: every 4 hours
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
        self.salience_manager: Optional[SalienceManager] = None
        
    async def initialize(self):
        """Initialize database connection and salience manager."""
        self.driver = AsyncGraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password)
        )
        self.salience_manager = SalienceManager(self.driver)
        logger.info(f"Salience scheduler initialized with cron: {self.cron_schedule}")
        
    async def cleanup(self):
        """Clean up database connections."""
        if self.driver:
            await self.driver.close()
            logger.info("Salience scheduler cleaned up")
    
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
        async def run_salience_decay():
            """Run the salience decay cycle."""
            await self.run_decay_cycle()
    
    async def run_decay_cycle(self) -> dict[str, int]:
        """
        Run a single decay cycle.
        
        Returns
        -------
        dict[str, int]
            Statistics about the decay cycle
        """
        if not self.salience_manager:
            logger.error("Salience manager not initialized")
            return {}
            
        try:
            logger.info("Starting scheduled salience decay cycle...")
            
            stats = await self.salience_manager.run_decay_cycle(
                group_ids=self.group_ids,
                batch_size=self.batch_size
            )
            
            logger.info(
                f"Scheduled decay cycle completed: "
                f"processed={stats.get('processed', 0)}, "
                f"decayed={stats.get('decayed', 0)}, "
                f"deleted={stats.get('deleted', 0)}"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in scheduled decay cycle: {str(e)}")
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
        if not self.salience_manager:
            await self.initialize()
            
        try:
            logger.info("Starting manual salience decay cycle...")
            
            stats = await self.salience_manager.run_decay_cycle(
                group_ids=group_ids or self.group_ids,
                batch_size=self.batch_size
            )
            
            logger.info(
                f"Manual decay cycle completed: "
                f"processed={stats.get('processed', 0)}, "
                f"decayed={stats.get('decayed', 0)}, "
                f"deleted={stats.get('deleted', 0)}"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in manual decay cycle: {str(e)}")
            return {"error": str(e)}


# Convenience function for easy setup
def setup_salience_scheduler(
    app: FastAPI,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    cron_schedule: str = "0 */4 * * *",
    group_ids: Optional[list[str]] = None,
    batch_size: int = 100
) -> SalienceScheduler:
    """
    Convenience function to set up salience scheduler with FastAPI.
    
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
        Cron expression for decay schedule. Default: every 4 hours
    group_ids : list[str], optional
        Limit decay to specific groups
    batch_size : int, optional
        Batch size for processing nodes
        
    Returns
    -------
    SalienceScheduler
        Configured scheduler instance
        
    Example
    -------
    ```python
    from fastapi import FastAPI
    from graphiti_extend.salience_scheduler import setup_salience_scheduler
    
    app = FastAPI()
    
    scheduler = setup_salience_scheduler(
        app=app,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        cron_schedule="0 */4 * * *"  # Every 4 hours
    )
    ```
    """
    scheduler = SalienceScheduler(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        cron_schedule=cron_schedule,
        group_ids=group_ids,
        batch_size=batch_size
    )
    
    scheduler.setup_scheduler(app)
    return scheduler