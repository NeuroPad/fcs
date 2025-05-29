# FCS Core

The FCS (Feedback and Clarification System) Core module provides enhanced memory management with automatic contradiction detection and alert generation.

## Features

### 1. Enhanced Memory Service with Contradiction Detection

The `FCSMemoryService` extends the standard Graphiti functionality with:
- **Automatic contradiction detection** between new and existing nodes
- **Real-time contradiction alerts** for immediate user feedback
- **Enhanced search** with contradiction awareness
- **Modular architecture** following graphiti_extend conventions

### 2. Contradiction Alert System

When contradictions are detected, the system:
- Creates structured `ContradictionAlert` objects
- Stores alerts for later retrieval and management
- Supports callback functions for custom handling
- Provides severity levels (low, medium, high)
- Tracks alert status (pending, acknowledged, resolved, ignored)

### 3. Background Processing with Retry Logic

- **Async worker** for background episode processing
- **Retry logic** for graphiti_core errors with exponential backoff
- **Graceful shutdown** with queue cleanup
- **Error isolation** to prevent worker crashes

## Quick Start

```python
import asyncio
from fcs_core import FCSMemoryService, Message
from datetime import datetime

async def contradiction_callback(alert):
    """Handle contradiction alerts"""
    print(f"🚨 Contradiction detected: {alert.message}")
    print(f"Severity: {alert.severity}")

async def main():
    # Initialize FCS Memory Service
    fcs_service = FCSMemoryService(
        enable_contradiction_detection=True,
        contradiction_threshold=0.7,
        contradiction_callback=contradiction_callback
    )
    
    # Initialize the service
    await fcs_service.initialize()
    await FCSMemoryService.initialize_worker()
    
    try:
        # Add a message
        message1 = Message(
            content="I love vanilla ice cream",
            role_type="user",
            timestamp=datetime.now()
        )
        
        response1 = await fcs_service.add_message("user123", message1)
        print(f"Response: {response1.message}")
        
        # Add a contradicting message
        message2 = Message(
            content="I hate vanilla ice cream, chocolate is better",
            role_type="user", 
            timestamp=datetime.now()
        )
        
        response2 = await fcs_service.add_message("user123", message2)
        print(f"Response: {response2.message}")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Check for contradiction alerts
        alerts = await fcs_service.get_contradiction_alerts("user123")
        for alert in alerts:
            print(f"Alert: {alert.message} (Status: {alert.status})")
        
        # Get contradiction summary
        summary = await fcs_service.get_contradiction_summary("user123")
        print(f"Total contradictions: {summary.get('total_contradictions', 0)}")
        
    finally:
        await fcs_service.close()
        await FCSMemoryService.shutdown_worker()

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### FCSMemoryService

#### Constructor Parameters

- `enable_contradiction_detection`: Enable/disable contradiction detection (default: True)
- `contradiction_threshold`: Similarity threshold for contradictions (default: 0.7)
- `contradiction_callback`: Optional callback function for handling alerts

#### Key Methods

##### `add_message(user_id, message) -> FCSResponse`

Add a chat message with contradiction detection.

```python
message = Message(
    content="I prefer tea over coffee",
    role_type="user",
    timestamp=datetime.now()
)

response = await fcs_service.add_message("user123", message)
if response.contradiction_alert:
    print(f"Contradiction: {response.contradiction_alert.message}")
```

##### `add_messages(user_id, messages) -> FCSResponse`

Add multiple messages with contradiction detection.

##### `add_text(user_id, content, source_name, source_description) -> FCSResponse`

Add text content with chunking and contradiction detection.

##### `search_memory(user_id, query) -> Dict`

Search memory with contradiction awareness.

```python
from schemas.memory import SearchQuery

query = SearchQuery(query="ice cream preferences", max_facts=10)
results = await fcs_service.search_memory("user123", query)

print(f"Found {results['count']} results")
print(f"Contradictions: {results['contradiction_count']}")
```

##### `get_contradiction_alerts(user_id, status=None) -> List[ContradictionAlert]`

Get contradiction alerts for a user.

```python
# Get all alerts
all_alerts = await fcs_service.get_contradiction_alerts("user123")

# Get only pending alerts
pending_alerts = await fcs_service.get_contradiction_alerts("user123", "pending")
```

##### `update_contradiction_alert(alert_id, status, user_response, resolution_action) -> bool`

Update an alert's status and response.

```python
success = await fcs_service.update_contradiction_alert(
    alert_id="2024-01-01T12:00:00",
    status="resolved",
    user_response="I changed my mind about ice cream",
    resolution_action="belief_updated"
)
```

##### `get_contradiction_summary(user_id) -> Dict`

Get a comprehensive contradiction summary.

```python
summary = await fcs_service.get_contradiction_summary("user123")
print(f"Total contradictions: {summary['total_contradictions']}")
print(f"Pending FCS alerts: {summary['fcs_alerts_pending']}")
```

## Data Models

### ContradictionAlert

```python
class ContradictionAlert(BaseModel):
    user_id: str
    message: str  # Human-readable contradiction message
    contradicting_nodes: List[str]  # UUIDs of contradicting nodes
    contradicted_nodes: List[str]   # UUIDs of contradicted nodes
    contradiction_edges: List[str]  # UUIDs of CONTRADICTS edges
    timestamp: datetime
    severity: str  # "low", "medium", "high"
    status: str   # "pending", "acknowledged", "resolved", "ignored"
    user_response: Optional[str]
    resolution_action: Optional[str]
```

### FCSResponse

```python
class FCSResponse(BaseModel):
    status: str  # "success", "error", "contradiction_detected", "queued"
    message: str
    contradiction_alert: Optional[ContradictionAlert]
    queue_size: Optional[int]
    additional_data: Optional[dict]
```

### Message

```python
class Message(BaseModel):
    content: str
    uuid: Optional[str]
    name: str
    role_type: str  # "user", "assistant", "system"
    role: Optional[str]
    timestamp: datetime
    source_description: str
```

## Integration with FCS System

The FCS Core is designed to integrate seamlessly with user interfaces:

### 1. Real-time Contradiction Alerts

```python
async def handle_contradiction(alert: ContradictionAlert):
    """Send alert to user interface"""
    await websocket.send_json({
        "type": "contradiction_alert",
        "message": alert.message,
        "severity": alert.severity,
        "options": ["Yes", "No", "I now believe this..."]
    })

fcs_service = FCSMemoryService(contradiction_callback=handle_contradiction)
```

### 2. User Response Handling

```python
async def handle_user_response(alert_id: str, response: str):
    """Handle user's response to contradiction"""
    if response == "Yes":
        # Show detailed contradiction information
        await show_contradiction_details(alert_id)
    elif response == "No":
        # Mark as acknowledged but not resolved
        await fcs_service.update_contradiction_alert(
            alert_id, "acknowledged", response, "user_dismissed"
        )
    elif response.startswith("I now believe"):
        # Update user's belief
        await fcs_service.update_contradiction_alert(
            alert_id, "resolved", response, "belief_updated"
        )
```

### 3. Dashboard Integration

```python
async def get_user_dashboard(user_id: str):
    """Get dashboard data with contradiction info"""
    summary = await fcs_service.get_contradiction_summary(user_id)
    pending_alerts = await fcs_service.get_contradiction_alerts(user_id, "pending")
    
    return {
        "total_contradictions": summary["total_contradictions"],
        "pending_alerts": len(pending_alerts),
        "recent_alerts": summary["fcs_alerts_recent"],
        "needs_attention": len(pending_alerts) > 0
    }
```

## Configuration

### Environment Variables

The service uses the same configuration as the original GraphitiMemoryService:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
PROCESSED_FILES_DIR=./processed_files
```

### Contradiction Detection Settings

```python
# High sensitivity - detects more contradictions
fcs_service = FCSMemoryService(contradiction_threshold=0.5)

# Low sensitivity - only obvious contradictions
fcs_service = FCSMemoryService(contradiction_threshold=0.9)

# Disable contradiction detection
fcs_service = FCSMemoryService(enable_contradiction_detection=False)
```

## Background Processing

The FCS Core uses an enhanced async worker with:

- **Retry logic** for transient graphiti_core errors
- **Exponential backoff** for failed jobs
- **Graceful shutdown** with queue cleanup
- **Error isolation** to prevent worker crashes

### Worker Management

```python
# Start the worker
await FCSMemoryService.initialize_worker()

# Check worker status
print(f"Worker running: {async_worker.is_running}")
print(f"Queue size: {async_worker.queue_size}")

# Stop the worker
await FCSMemoryService.shutdown_worker()
```

## Error Handling

The service provides comprehensive error handling:

```python
try:
    response = await fcs_service.add_message(user_id, message)
    if response.status == "error":
        print(f"Error: {response.message}")
    elif response.contradiction_alert:
        print(f"Contradiction detected: {response.contradiction_alert.message}")
except Exception as e:
    print(f"Unexpected error: {str(e)}")
```

## Performance Considerations

1. **Background Processing**: All episode processing happens asynchronously
2. **Contradiction Detection**: Adds ~10-20% overhead to episode processing
3. **Memory Usage**: Contradiction alerts are stored in memory (consider persistence for production)
4. **Search Performance**: Contradiction-aware search has minimal overhead

## Migration from GraphitiMemoryService

The FCS Core maintains API compatibility with the original service:

```python
# Old way
from services.graphiti_memory_service import GraphitiMemoryService
service = GraphitiMemoryService()

# New way
from fcs_core import FCSMemoryService
service = FCSMemoryService()

# All existing methods work the same way
response = await service.add_message(user_id, message)
results = await service.search_memory(user_id, query)
```

## License

This module follows the same Apache 2.0 license as the core Graphiti project. 