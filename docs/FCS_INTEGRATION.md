# FCS System Integration Guide

This document explains how to integrate the `graphiti_extend` module with the FCS to handle contradictions in user statements.

## Overview

When the `graphiti_extend` module detects contradictions between new and existing nodes, it generates human-readable messages that can be used by the FCS system to prompt users for clarification.

## Integration Flow

```
1. User Input → ExtendedGraphiti.add_episode_with_contradictions()
2. Contradiction Detection → Generate contradiction message
3. FCS System → Present options to user
4. User Response → Update knowledge graph accordingly
```

## Implementation Example

### 1. Basic Integration

```python
from graphiti_extend import ExtendedGraphiti
from datetime import datetime

class FCSIntegratedGraphiti:
    def __init__(self, graphiti: ExtendedGraphiti, fcs_callback=None):
        self.graphiti = graphiti
        self.fcs_callback = fcs_callback
    
    async def process_user_input(self, user_id: str, message: str):
        """Process user input with FCS integration."""
        
        # Add episode with contradiction detection
        result = await self.graphiti.add_episode_with_contradictions(
            name=f"User Message {datetime.now().isoformat()}",
            episode_body=message,
            source_description="User input",
            reference_time=datetime.now(),
            group_id=user_id
        )
        
        # Check for contradictions
        if result.contradiction_result.contradictions_found:
            # Send to FCS system for user clarification
            if self.fcs_callback:
                await self.fcs_callback(
                    user_id=user_id,
                    contradiction_message=result.contradiction_result.contradiction_message,
                    contradiction_data=result.contradiction_result
                )
            
            return {
                "status": "contradiction_detected",
                "message": result.contradiction_result.contradiction_message,
                "requires_clarification": True,
                "contradiction_data": result.contradiction_result
            }
        
        return {
            "status": "processed",
            "message": "Input processed successfully",
            "requires_clarification": False
        }
```

### 2. FCS Callback Implementation

```python
async def fcs_contradiction_handler(user_id: str, contradiction_message: str, contradiction_data):
    """Handle contradiction detection by presenting options to user."""
    
    # Present options to user through FCS interface
    options = [
        {
            "id": "explore",
            "text": "Yes",
            "description": "Explore the contradiction in detail"
        },
        {
            "id": "ignore", 
            "text": "No",
            "description": "Acknowledge but ignore the contradiction"
        },
        {
            "id": "update",
            "text": "I now believe this...",
            "description": "Update belief system with new information"
        }
    ]
    
    # Send to FCS system (implementation depends on your FCS architecture)
    await send_to_fcs_system(
        user_id=user_id,
        message=contradiction_message,
        options=options,
        context=contradiction_data
    )
```

### 3. Handling User Responses

```python
async def handle_fcs_response(user_id: str, response_type: str, response_data: dict):
    """Handle user response from FCS system."""
    
    if response_type == "explore":
        # Show detailed contradiction information
        return await show_contradiction_details(user_id, response_data)
    
    elif response_type == "ignore":
        # Mark contradiction as acknowledged but not resolved
        return await mark_contradiction_ignored(user_id, response_data)
    
    elif response_type == "update":
        # Update user's belief system
        return await update_user_beliefs(user_id, response_data)
    
    else:
        return {"error": "Unknown response type"}

async def show_contradiction_details(user_id: str, contradiction_data: dict):
    """Show detailed information about the contradiction."""
    
    # Get contradiction summary
    graphiti = get_graphiti_instance()
    summary = await graphiti.get_contradiction_summary(group_ids=[user_id])
    
    # Format detailed response
    details = {
        "contradicting_statements": [
            node.summary for node in contradiction_data["contradicting_nodes"]
        ],
        "contradicted_statements": [
            node.summary for node in contradiction_data["contradicted_nodes"]
        ],
        "total_contradictions": summary["total_contradictions"],
        "suggestion": "Consider which statement better reflects your current beliefs"
    }
    
    return {
        "status": "details_provided",
        "details": details
    }

async def mark_contradiction_ignored(user_id: str, contradiction_data: dict):
    """Mark contradiction as acknowledged but not resolved."""
    
    # You could add metadata to the contradiction edges
    # or create a separate tracking system
    
    return {
        "status": "contradiction_ignored",
        "message": "Contradiction acknowledged but not resolved"
    }

async def update_user_beliefs(user_id: str, response_data: dict):
    """Update user's belief system based on their clarification."""
    
    new_belief = response_data.get("new_belief", "")
    
    if new_belief:
        # Add new episode with the clarified belief
        graphiti = get_graphiti_instance()
        result = await graphiti.add_episode_with_contradictions(
            name="Belief Clarification",
            episode_body=f"To clarify: {new_belief}",
            source_description="User clarification via FCS",
            reference_time=datetime.now(),
            group_id=user_id
        )
        
        return {
            "status": "belief_updated",
            "message": "Your belief has been updated",
            "new_episode": result.episode.uuid
        }
    
    return {
        "status": "error",
        "message": "No new belief provided"
    }
```

## Message Templates

The system generates messages in the format:
```
"You said {previous_statement} before. This feels different with {new_statement}. Want to look at it?"
```

### Example Messages

- Single contradiction: "You said vanilla ice cream before. This feels different with chocolate ice cream. Want to look at it?"
- Multiple contradictions: "You said vanilla ice cream, strawberry ice cream before. This feels different with chocolate ice cream. Want to look at it?"

## Configuration Options

### FCS Integration Settings

```python
fcs_config = {
    "enable_contradiction_detection": True,
    "contradiction_threshold": 0.7,  # Sensitivity (0.0-1.0)
    "auto_present_options": True,    # Automatically show FCS options
    "require_user_response": True,   # Wait for user response before continuing
    "timeout_seconds": 300,          # Timeout for user response
}
```

### Customizing Messages

```python
class CustomMessageGenerator:
    def generate_contradiction_message(self, contradicting_nodes, contradicted_nodes):
        """Generate custom contradiction messages."""
        
        if len(contradicting_nodes) == 1 and len(contradicted_nodes) == 1:
            return f"I notice you previously mentioned {contradicted_nodes[0].name}. " \
                   f"Your current statement about {contradicting_nodes[0].name} seems different. " \
                   f"Would you like to discuss this?"
        
        # Handle multiple nodes...
        return "I've detected some conflicting information. Would you like to review it?"
```

## Error Handling

```python
async def safe_contradiction_processing(user_id: str, message: str):
    """Safely process user input with error handling."""
    
    try:
        result = await process_user_input(user_id, message)
        return result
    
    except Exception as e:
        logger.error(f"Error processing contradiction for user {user_id}: {str(e)}")
        
        # Fallback: process without contradiction detection
        graphiti = get_graphiti_instance()
        graphiti.enable_contradiction_detection = False
        
        try:
            result = await graphiti.add_episode_with_contradictions(
                name="Fallback Processing",
                episode_body=message,
                source_description="User input (fallback)",
                reference_time=datetime.now(),
                group_id=user_id
            )
            
            return {
                "status": "processed_fallback",
                "message": "Input processed (contradiction detection disabled due to error)"
            }
        
        finally:
            graphiti.enable_contradiction_detection = True
    
    except Exception as fallback_error:
        logger.error(f"Fallback processing failed for user {user_id}: {str(fallback_error)}")
        return {
            "status": "error",
            "message": "Failed to process input"
        }
```

## Performance Considerations

1. **Async Processing**: Use background tasks for contradiction detection to avoid blocking user interactions
2. **Caching**: Cache recent contradiction results to avoid redundant processing
3. **Timeouts**: Set reasonable timeouts for user responses
4. **Batch Processing**: Consider batching multiple inputs before checking for contradictions

## Testing FCS Integration

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_fcs_integration():
    """Test FCS integration with contradiction detection."""
    
    # Mock FCS callback
    fcs_callback = AsyncMock()
    
    # Create integrated system
    graphiti = ExtendedGraphiti(...)
    fcs_system = FCSIntegratedGraphiti(graphiti, fcs_callback)
    
    # Add contradicting statements
    await fcs_system.process_user_input("user123", "I love vanilla ice cream")
    result = await fcs_system.process_user_input("user123", "I hate vanilla ice cream")
    
    # Verify FCS callback was triggered
    assert result["requires_clarification"] == True
    fcs_callback.assert_called_once()
    
    # Verify message format
    assert "You said" in result["message"]
    assert "Want to look at it?" in result["message"]
```

## Best Practices

1. **User Experience**: Keep contradiction messages conversational and non-confrontational
2. **Context Preservation**: Maintain context about why contradictions were detected
3. **Graceful Degradation**: Always provide fallback behavior if contradiction detection fails
4. **Privacy**: Ensure contradiction data doesn't leak sensitive information
5. **Customization**: Allow users to adjust contradiction sensitivity
6. **Logging**: Log contradiction events for analysis and improvement

## Integration Checklist

- [ ] Implement FCS callback handler
- [ ] Configure contradiction detection settings
- [ ] Set up user response handling
- [ ] Add error handling and fallbacks
- [ ] Test with various contradiction scenarios
- [ ] Configure message templates
- [ ] Set up logging and monitoring
- [ ] Document user-facing features
- [ ] Train support team on contradiction handling
- [ ] Plan for system updates and maintenance 