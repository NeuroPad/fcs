"""
Test script for default values functionality in ExtendedGraphiti.

This script demonstrates how default values are applied to new CognitiveObject nodes
while preserving existing values in duplicate nodes.
"""

import asyncio
import logging
import pytest
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock classes for testing (replace with actual imports in production)
class EntityNode:
    def __init__(self, name: str, labels: list[str], uuid: str = None, attributes: dict = None):
        self.name = name
        self.labels = labels
        self.uuid = uuid or f"uuid-{name.replace(' ', '-')}"
        self.attributes = attributes or {}

class MockCognitiveObject(BaseModel):
    """Mock CognitiveObject with default values for testing."""
    confidence: float = Field(default=0.7, description="Confidence level")
    salience: float = Field(default=0.5, description="Salience level")
    type: str = Field(default="idea", description="Type of cognitive object")
    flags: List[str] = Field(default_factory=list, description="Flags")


class TestDefaultValues:
    """Test cases for default values functionality."""
    
    def test_default_values_extraction(self):
        """Test extracting default values from Pydantic model."""
        from graphiti_extend.default_values_handler import _extract_default_values_from_model
        
        model = MockCognitiveObject
        defaults = _extract_default_values_from_model(model)
        
        logger.info("Extracted default values: %s", defaults)
        
        expected = {
            'confidence': 0.7,
            'salience': 0.5,
            'type': 'idea',
            'flags': []
        }
        
        assert defaults['confidence'] == expected['confidence'], f"Expected confidence {expected['confidence']}, got {defaults['confidence']}"
        assert defaults['salience'] == expected['salience'], f"Expected salience {expected['salience']}, got {defaults['salience']}"
        assert defaults['type'] == expected['type'], f"Expected type {expected['type']}, got {defaults['type']}"
        assert defaults['flags'] == expected['flags'], f"Expected flags {expected['flags']}, got {defaults['flags']}"
        
        logger.info("✓ Default values extraction test passed!")

    def test_apply_default_values(self):
        """Test applying default values to new nodes."""
        from graphiti_extend.default_values_handler import apply_default_values_to_new_nodes
        
        # Create test nodes
        extracted_nodes = [
            EntityNode("John", ["Entity", "CognitiveObject"], "extracted-1"),
            EntityNode("Mary", ["Entity", "CognitiveObject"], "extracted-2"),
            EntityNode("Project Alpha", ["Entity"], "extracted-3"),
        ]
        
        # Simulate resolution: John is new, Mary is a duplicate of existing node
        resolved_nodes = [
            EntityNode("John", ["Entity", "CognitiveObject"], "extracted-1"),  # New node (same UUID)
            EntityNode("Mary Smith", ["Entity", "CognitiveObject"], "existing-mary", {"confidence": 0.9, "salience": 0.8}),  # Existing node (different UUID)
            EntityNode("Project Alpha", ["Entity"], "extracted-3"),  # New node, no entity type
        ]
        
        uuid_map = {
            "extracted-1": "extracted-1",  # New node
            "extracted-2": "existing-mary",  # Duplicate
            "extracted-3": "extracted-3",  # New node
        }
        
        entity_types = {"CognitiveObject": MockCognitiveObject}
        
        # Apply default values
        result_nodes = apply_default_values_to_new_nodes(
            extracted_nodes, resolved_nodes, uuid_map, entity_types
        )
        
        # Check results
        john_node = next(n for n in result_nodes if n.name == "John")
        mary_node = next(n for n in result_nodes if n.name == "Mary Smith")
        project_node = next(n for n in result_nodes if n.name == "Project Alpha")
        
        # John should have default values (new node)
        assert john_node.attributes.get('confidence') == 0.7, f"John should have default confidence 0.7, got {john_node.attributes.get('confidence')}"
        assert john_node.attributes.get('salience') == 0.5, f"John should have default salience 0.5, got {john_node.attributes.get('salience')}"
        
        # Mary should keep existing values (duplicate node)
        assert mary_node.attributes.get('confidence') == 0.9, f"Mary should keep existing confidence 0.9, got {mary_node.attributes.get('confidence')}"
        assert mary_node.attributes.get('salience') == 0.8, f"Mary should keep existing salience 0.8, got {mary_node.attributes.get('salience')}"
        
        # Project should not have defaults (not CognitiveObject type)
        assert 'confidence' not in project_node.attributes, f"Project should not have confidence, but got {project_node.attributes}"
        assert 'salience' not in project_node.attributes, f"Project should not have salience, but got {project_node.attributes}"
        
        logger.info("✓ Default values application test passed!")
        logger.info("John's attributes: %s", john_node.attributes)
        logger.info("Mary's attributes: %s", mary_node.attributes)
        logger.info("Project's attributes: %s", project_node.attributes)

    def test_new_node_identification(self):
        """Test identification of new vs existing nodes."""
        extracted_nodes = [
            EntityNode("Alice", ["Entity", "CognitiveObject"], "uuid-1"),
            EntityNode("Bob", ["Entity", "CognitiveObject"], "uuid-2"),
        ]
        
        resolved_nodes = [
            EntityNode("Alice", ["Entity", "CognitiveObject"], "uuid-1"),  # Same UUID = new
            EntityNode("Bob Johnson", ["Entity", "CognitiveObject"], "existing-uuid"),  # Different UUID = existing
        ]
        
        uuid_map = {
            "uuid-1": "uuid-1",  # New node
            "uuid-2": "existing-uuid",  # Existing node
        }
        
        from graphiti_extend.default_values_handler import apply_default_values_to_new_nodes
        entity_types = {"CognitiveObject": MockCognitiveObject}
        
        result_nodes = apply_default_values_to_new_nodes(
            extracted_nodes, resolved_nodes, uuid_map, entity_types
        )
        
        alice_node = next(n for n in result_nodes if n.name == "Alice")
        bob_node = next(n for n in result_nodes if n.name == "Bob Johnson")
        
        # Alice should get defaults (new node)
        assert alice_node.attributes.get('confidence') == 0.7
        assert alice_node.attributes.get('salience') == 0.5
        
        # Bob should not get defaults (existing node)
        assert 'confidence' not in bob_node.attributes
        assert 'salience' not in bob_node.attributes

    def test_mixed_entity_types(self):
        """Test handling nodes with mixed entity types."""
        extracted_nodes = [
            EntityNode("Cognitive Node", ["Entity", "CognitiveObject"], "uuid-1"),
            EntityNode("Regular Node", ["Entity"], "uuid-2"),
            EntityNode("Multi Type", ["Entity", "CognitiveObject", "OtherType"], "uuid-3"),
        ]
        
        resolved_nodes = [
            EntityNode("Cognitive Node", ["Entity", "CognitiveObject"], "uuid-1"),
            EntityNode("Regular Node", ["Entity"], "uuid-2"),
            EntityNode("Multi Type", ["Entity", "CognitiveObject", "OtherType"], "uuid-3"),
        ]
        
        uuid_map = {
            "uuid-1": "uuid-1",
            "uuid-2": "uuid-2", 
            "uuid-3": "uuid-3",
        }
        
        from graphiti_extend.default_values_handler import apply_default_values_to_new_nodes
        entity_types = {"CognitiveObject": MockCognitiveObject}
        
        result_nodes = apply_default_values_to_new_nodes(
            extracted_nodes, resolved_nodes, uuid_map, entity_types
        )
        
        cognitive_node = next(n for n in result_nodes if n.name == "Cognitive Node")
        regular_node = next(n for n in result_nodes if n.name == "Regular Node")
        multi_node = next(n for n in result_nodes if n.name == "Multi Type")
        
        # Cognitive node should get defaults
        assert cognitive_node.attributes.get('confidence') == 0.7
        
        # Regular node should not get defaults
        assert 'confidence' not in regular_node.attributes
        
        # Multi-type node should get defaults (has CognitiveObject)
        assert multi_node.attributes.get('confidence') == 0.7


def test_default_values_extraction_standalone():
    """Standalone test for default values extraction."""
    from graphiti_extend.default_values_handler import _extract_default_values_from_model
    
    model = MockCognitiveObject
    defaults = _extract_default_values_from_model(model)
    
    print("Extracted default values:", defaults)
    
    expected = {
        'confidence': 0.7,
        'salience': 0.5,
        'type': 'idea',
        'flags': []
    }
    
    assert defaults['confidence'] == expected['confidence'], f"Expected confidence {expected['confidence']}, got {defaults['confidence']}"
    assert defaults['salience'] == expected['salience'], f"Expected salience {expected['salience']}, got {defaults['salience']}"
    assert defaults['type'] == expected['type'], f"Expected type {expected['type']}, got {defaults['type']}"
    assert defaults['flags'] == expected['flags'], f"Expected flags {expected['flags']}, got {defaults['flags']}"
    
    print("✓ Default values extraction test passed!")


def test_apply_default_values_standalone():
    """Standalone test for applying default values."""
    from graphiti_extend.default_values_handler import apply_default_values_to_new_nodes
    
    # Create test nodes
    extracted_nodes = [
        EntityNode("John", ["Entity", "CognitiveObject"], "extracted-1"),
        EntityNode("Mary", ["Entity", "CognitiveObject"], "extracted-2"),
        EntityNode("Project Alpha", ["Entity"], "extracted-3"),
    ]
    
    # Simulate resolution: John is new, Mary is a duplicate of existing node
    resolved_nodes = [
        EntityNode("John", ["Entity", "CognitiveObject"], "extracted-1"),  # New node (same UUID)
        EntityNode("Mary Smith", ["Entity", "CognitiveObject"], "existing-mary", {"confidence": 0.9, "salience": 0.8}),  # Existing node (different UUID)
        EntityNode("Project Alpha", ["Entity"], "extracted-3"),  # New node, no entity type
    ]
    
    uuid_map = {
        "extracted-1": "extracted-1",  # New node
        "extracted-2": "existing-mary",  # Duplicate
        "extracted-3": "extracted-3",  # New node
    }
    
    entity_types = {"CognitiveObject": MockCognitiveObject}
    
    # Apply default values
    result_nodes = apply_default_values_to_new_nodes(
        extracted_nodes, resolved_nodes, uuid_map, entity_types
    )
    
    # Check results
    john_node = next(n for n in result_nodes if n.name == "John")
    mary_node = next(n for n in result_nodes if n.name == "Mary Smith")
    project_node = next(n for n in result_nodes if n.name == "Project Alpha")
    
    # John should have default values (new node)
    assert john_node.attributes.get('confidence') == 0.7, f"John should have default confidence 0.7, got {john_node.attributes.get('confidence')}"
    assert john_node.attributes.get('salience') == 0.5, f"John should have default salience 0.5, got {john_node.attributes.get('salience')}"
    
    # Mary should keep existing values (duplicate node)
    assert mary_node.attributes.get('confidence') == 0.9, f"Mary should keep existing confidence 0.9, got {mary_node.attributes.get('confidence')}"
    assert mary_node.attributes.get('salience') == 0.8, f"Mary should keep existing salience 0.8, got {mary_node.attributes.get('salience')}"
    
    # Project should not have defaults (not CognitiveObject type)
    assert 'confidence' not in project_node.attributes, f"Project should not have confidence, but got {project_node.attributes}"
    assert 'salience' not in project_node.attributes, f"Project should not have salience, but got {project_node.attributes}"
    
    print("✓ Default values application test passed!")
    print(f"John's attributes: {john_node.attributes}")
    print(f"Mary's attributes: {mary_node.attributes}")
    print(f"Project's attributes: {project_node.attributes}")


def main():
    """Run all tests."""
    print("Testing default values functionality...")
    print()
    
    test_default_values_extraction_standalone()
    print()
    
    test_apply_default_values_standalone()
    print()
    
    print("All tests passed! 🎉")


if __name__ == "__main__":
    main() 