"""
Comprehensive example demonstrating the FCS Salience System.

This example shows how to:
1. Set up the ExtendedGraphiti with salience management
2. Configure the salience scheduler for automatic decay
3. Process episodes with automatic salience updates
4. Run manual decay cycles
5. Monitor salience changes over time

The system implements brain-like memory reinforcement where:
- Frequently mentioned concepts become more salient
- Connected concepts reinforce each other
- Unused concepts naturally decay and may be forgotten
"""

import asyncio
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the salience system components
from graphiti_extend import (
    ExtendedGraphiti,
    SalienceManager,
    SalienceConfig,
    SalienceScheduler,
    setup_salience_scheduler
)
from fcs_core.models import CognitiveObject


class SalienceDemo:
    """Demonstration of the complete salience system."""
    
    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password"
    ):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.graphiti = None
        self.scheduler = None
        
    async def setup_graphiti(self):
        """Set up ExtendedGraphiti with salience management."""
        self.graphiti = ExtendedGraphiti(
            uri=self.neo4j_uri,
            user=self.neo4j_user,
            password=self.neo4j_password,
            enable_contradiction_detection=True,
            contradiction_threshold=0.7
        )
        logger.info("ExtendedGraphiti initialized with salience management")
        
    def setup_fastapi_scheduler(self) -> FastAPI:
        """Set up FastAPI with automatic salience decay scheduler."""
        app = FastAPI(title="Salience System Demo")
        
        # Set up scheduler to run every 4 hours
        self.scheduler = setup_salience_scheduler(
            app=app,
            neo4j_uri=self.neo4j_uri,
            neo4j_user=self.neo4j_user,
            neo4j_password=self.neo4j_password,
            cron_schedule="0 */4 * * *",  # Every 4 hours
            batch_size=50
        )
        
        # Add API endpoints for manual control
        @app.get("/salience/decay/manual")
        async def run_manual_decay():
            """Run a manual decay cycle."""
            stats = await self.scheduler.run_manual_decay()
            return {"message": "Manual decay completed", "stats": stats}
        
        @app.get("/salience/stats")
        async def get_salience_stats():
            """Get salience statistics."""
            # This would query the database for salience distribution
            return {"message": "Salience stats endpoint"}
        
        logger.info("FastAPI app configured with salience scheduler")
        return app
    
    async def demonstrate_salience_updates(self):
        """Demonstrate how salience updates work during episode processing."""
        logger.info("=== Demonstrating Salience Updates ===")
        
        # Define CognitiveObject entity type
        entity_types = {
            'CognitiveObject': CognitiveObject
        }
        
        # Episode 1: Initial mention of concepts
        logger.info("Processing Episode 1: Initial concepts")
        result1 = await self.graphiti.add_episode_with_contradictions(
            name="Initial Learning",
            episode_body="I love Python programming. It's my favorite language for data science.",
            source_description="User preference statement",
            reference_time=datetime.now(),
            group_id="demo_user",
            entity_types=entity_types
        )
        
        logger.info(f"Episode 1 created {len(result1.nodes)} nodes")
        for node in result1.nodes:
            if 'CognitiveObject' in node.labels:
                salience = node.attributes.get('salience', 0.5)
                logger.info(f"  - {node.name}: salience={salience:.3f}")
        
        # Episode 2: Reinforcement through repetition
        logger.info("\nProcessing Episode 2: Reinforcement")
        result2 = await self.graphiti.add_episode_with_contradictions(
            name="Reinforcement",
            episode_body="Python is really great for machine learning projects. I use it daily.",
            source_description="User reinforcement",
            reference_time=datetime.now(),
            group_id="demo_user",
            entity_types=entity_types
        )
        
        logger.info(f"Episode 2 created {len(result2.nodes)} nodes")
        for node in result2.nodes:
            if 'CognitiveObject' in node.labels:
                salience = node.attributes.get('salience', 0.5)
                logger.info(f"  - {node.name}: salience={salience:.3f}")
        
        # Episode 3: Contradiction
        logger.info("\nProcessing Episode 3: Contradiction")
        result3 = await self.graphiti.add_episode_with_contradictions(
            name="Contradiction",
            episode_body="Actually, I think JavaScript is better than Python for most projects.",
            source_description="User contradiction",
            reference_time=datetime.now(),
            group_id="demo_user",
            entity_types=entity_types
        )
        
        logger.info(f"Episode 3 created {len(result3.nodes)} nodes")
        if result3.contradiction_result.contradictions_found:
            logger.info(f"Contradictions detected: {len(result3.contradiction_result.contradiction_edges)} edges")
            logger.info(f"Contradiction message: {result3.contradiction_result.contradiction_message}")
        
        for node in result3.nodes:
            if 'CognitiveObject' in node.labels:
                salience = node.attributes.get('salience', 0.5)
                logger.info(f"  - {node.name}: salience={salience:.3f}")
    
    async def demonstrate_network_reinforcement(self):
        """Demonstrate network pathway reinforcement."""
        logger.info("\n=== Demonstrating Network Reinforcement ===")
        
        # Create some connected concepts
        entity_types = {'CognitiveObject': CognitiveObject}
        
        episodes = [
            "Machine learning requires good data preprocessing.",
            "Data preprocessing is crucial for model accuracy.",
            "Model accuracy depends on feature engineering.",
            "Feature engineering is part of data science workflow."
        ]
        
        for i, episode_text in enumerate(episodes):
            result = await self.graphiti.add_episode_with_contradictions(
                name=f"Network Episode {i+1}",
                episode_body=episode_text,
                source_description="Building connected concepts",
                reference_time=datetime.now(),
                group_id="demo_user",
                entity_types=entity_types
            )
            
            logger.info(f"Episode {i+1}: {len(result.nodes)} nodes")
        
        # Now mention one concept to see network reinforcement
        logger.info("\nTriggering network reinforcement...")
        result = await self.graphiti.add_episode_with_contradictions(
            name="Network Trigger",
            episode_body="I'm working on machine learning today.",
            source_description="Triggering network reinforcement",
            reference_time=datetime.now(),
            group_id="demo_user",
            entity_types=entity_types
        )
        
        logger.info("Network reinforcement should have propagated to connected concepts")
    
    async def demonstrate_decay_cycle(self):
        """Demonstrate the decay cycle functionality."""
        logger.info("\n=== Demonstrating Decay Cycle ===")
        
        # Run a manual decay cycle
        if self.scheduler:
            stats = await self.scheduler.run_manual_decay(group_ids=["demo_user"])
            logger.info(f"Decay cycle stats: {stats}")
        else:
            # Create a temporary salience manager for demonstration
            from neo4j import AsyncGraphDatabase
            driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            
            salience_manager = SalienceManager(driver)
            stats = await salience_manager.run_decay_cycle(
                group_ids=["demo_user"],
                batch_size=50
            )
            
            logger.info(f"Manual decay cycle stats: {stats}")
            await driver.close()
    
    async def demonstrate_configuration(self):
        """Demonstrate salience configuration options."""
        logger.info("\n=== Demonstrating Configuration ===")
        
        # Show default configuration
        config = SalienceConfig()
        logger.info("Default Salience Configuration:")
        logger.info(f"  Conversation mention boost: {config.CONVERSATION_MENTION}")
        logger.info(f"  Duplicate found boost: {config.DUPLICATE_FOUND}")
        logger.info(f"  Reasoning usage boost: {config.REASONING_USAGE}")
        logger.info(f"  Network reinforcement: {config.BASE_NETWORK_REINFORCEMENT}")
        logger.info(f"  Base decay rate: {config.BASE_DECAY_RATE}")
        logger.info(f"  Orphaned decay rate: {config.ORPHANED_DECAY}")
        
        # Show how to create custom configuration
        custom_config = SalienceConfig()
        custom_config.CONVERSATION_MENTION = 0.4  # Higher boost for mentions
        custom_config.BASE_DECAY_RATE = 0.01      # Slower decay
        
        logger.info("\nCustom configuration example created")
    
    async def run_complete_demo(self):
        """Run the complete salience system demonstration."""
        logger.info("Starting Complete Salience System Demonstration")
        logger.info("=" * 60)
        
        try:
            # Setup
            await self.setup_graphiti()
            
            # Demonstrate different aspects
            await self.demonstrate_configuration()
            await self.demonstrate_salience_updates()
            await self.demonstrate_network_reinforcement()
            await self.demonstrate_decay_cycle()
            
            logger.info("\n" + "=" * 60)
            logger.info("Salience System Demonstration Complete!")
            logger.info("\nKey Features Demonstrated:")
            logger.info("✓ Automatic salience updates during episode processing")
            logger.info("✓ Network pathway reinforcement")
            logger.info("✓ Contradiction detection with salience boosts")
            logger.info("✓ Temporal decay and forgetting mechanism")
            logger.info("✓ Configurable parameters")
            logger.info("✓ Scheduled background decay cycles")
            
        except Exception as e:
            logger.error(f"Error in demonstration: {str(e)}")
            raise
        finally:
            # Cleanup
            if self.graphiti and hasattr(self.graphiti, 'driver'):
                await self.graphiti.driver.close()


async def main():
    """Main function to run the demonstration."""
    demo = SalienceDemo()
    
    # Option 1: Run basic demo without FastAPI scheduler
    await demo.run_complete_demo()
    
    # Option 2: Set up FastAPI app with scheduler (uncomment to use)
    # app = demo.setup_fastapi_scheduler()
    # logger.info("FastAPI app created with salience scheduler")
    # logger.info("Run with: uvicorn example_salience_system:app --reload")


def create_fastapi_app():
    """Create FastAPI app for production use."""
    demo = SalienceDemo()
    return demo.setup_fastapi_scheduler()


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main()) 