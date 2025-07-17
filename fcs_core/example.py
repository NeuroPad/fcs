"""
Example usage of the fcs_core module.

This script demonstrates how to use the FCSMemoryService
to detect contradictions in user statements and handle alerts.
"""

import asyncio
import logging
from datetime import datetime


# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fcs_core import FCSMemoryService, Message, ContradictionAlert


async def contradiction_callback(alert: ContradictionAlert):
    """
    Handle contradiction alerts from the FCS system.
    
    In a real application, this would send alerts to the user interface,
    trigger notifications, or integrate with other systems.
    """
    print(f"\n🚨 CONTRADICTION ALERT 🚨")
    print(f"User: {alert.user_id}")
    print(f"Message: {alert.message}")
    print(f"Severity: {alert.severity}")
    print(f"Status: {alert.status}")
    print(f"Timestamp: {alert.timestamp}")
    print(f"Contradicting nodes: {len(alert.contradicting_nodes)}")
    print(f"Contradicted nodes: {len(alert.contradicted_nodes)}")
    print(f"Contradiction edges: {len(alert.contradiction_edges)}")
    
    # Simulate FCS system presenting options to user
    print("\nFCS System would present options:")
    print("1. 'Yes' - Explore the contradiction in detail")
    print("2. 'No' - Acknowledge but ignore the contradiction")
    print("3. 'I now believe this...' - Update belief system")
    print("-" * 50)


async def main():
    """
    Demonstrate FCS Core functionality with ice cream preference contradictions.
    """
    print("🍦 FCS Core Contradiction Detection Demo 🍦")
    print("=" * 50)
    
    # Initialize FCS Memory Service with contradiction detection
    fcs_service = FCSMemoryService(
        enable_contradiction_detection=True,
        contradiction_threshold=0.7,  # Adjust sensitivity
        contradiction_callback=contradiction_callback
    )
    
    try:
        # Initialize the service and worker
        await fcs_service.initialize()
        await FCSMemoryService.initialize_worker()
        
        user_id = "demo_user_123"
        
        print(f"\n1. Adding first message: User likes vanilla ice cream")
        message1 = Message(
            content="I absolutely love vanilla ice cream. It's my favorite flavor and I eat it every day.",
            role_type="user",
            timestamp=datetime.now(),
            source_description="User preference statement"
        )
        
        response1 = await fcs_service.add_message(user_id, message1)
        print(f"Response: {response1.message}")
        print(f"Queue size: {response1.queue_size}")
        
        # Wait for processing
        print("\nWaiting for background processing...")
        await asyncio.sleep(3)
        
        print(f"\n2. Adding contradicting message: User dislikes vanilla ice cream")
        message2 = Message(
            content="I hate vanilla ice cream. It's so boring and tasteless. Chocolate is much better.",
            role_type="user",
            timestamp=datetime.now(),
            source_description="User preference statement"
        )
        
        response2 = await fcs_service.add_message(user_id, message2)
        print(f"Response: {response2.message}")
        print(f"Queue size: {response2.queue_size}")
        
        # Wait for processing and contradiction detection
        print("\nWaiting for contradiction detection...")
        await asyncio.sleep(5)
        
        print(f"\n3. Checking for contradiction alerts")
        alerts = await fcs_service.get_contradiction_alerts(user_id)
        print(f"Found {len(alerts)} alerts for user {user_id}")
        
        for i, alert in enumerate(alerts, 1):
            print(f"\nAlert {i}:")
            print(f"  Message: {alert.message}")
            print(f"  Severity: {alert.severity}")
            print(f"  Status: {alert.status}")
        
        print(f"\n4. Getting contradiction summary")
        summary = await fcs_service.get_contradiction_summary(user_id)
        print(f"Total contradictions in graph: {summary.get('total_contradictions', 0)}")
        print(f"FCS alerts total: {summary.get('fcs_alerts_total', 0)}")
        print(f"FCS alerts pending: {summary.get('fcs_alerts_pending', 0)}")
        
        print(f"\n✅ Demo completed successfully!")
        print(f"The FCS Core successfully detected contradictions and provided")
        print(f"structured alerts for integration with user interfaces.")
        
    except Exception as e:
        logger.error(f"Error during demo: {str(e)}")
        raise
    
    finally:
        # Clean up
        await fcs_service.close()
        await FCSMemoryService.shutdown_worker()
        print(f"\n🧹 Cleanup completed!")


if __name__ == "__main__":
    asyncio.run(main()) 