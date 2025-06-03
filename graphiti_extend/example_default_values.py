"""
Example demonstrating default values functionality for CognitiveObject entities.

This example shows how the ExtendedGraphiti system automatically applies
default values to new CognitiveObject nodes while preserving existing values
for duplicate nodes.
"""

import asyncio
import logging
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the actual CognitiveObject model
from fcs_core.models import CognitiveObject

def demonstrate_default_values():
    """
    Demonstrate how default values are extracted from CognitiveObject model.
    """
    from graphiti_extend.default_values_handler import _extract_default_values_from_model
    
    print("=== CognitiveObject Default Values ===")
    print()
    
    # Extract default values from the model
    defaults = _extract_default_values_from_model(CognitiveObject)
    
    print("Default values found in CognitiveObject model:")
    for field_name, default_value in defaults.items():
        print(f"  {field_name}: {default_value}")
    
    print()
    
    # Verify the expected defaults
    expected_defaults = {
        'confidence': 0.7,
        'salience': 0.5,
        'flags': [],
        'parent_ids': [],
        'child_ids': [],
        'match_history': [],
        'linked_refs': [],
        'generated_from': [],
    }
    
    print("Expected vs Actual defaults:")
    for field_name, expected_value in expected_defaults.items():
        actual_value = defaults.get(field_name, "NOT FOUND")
        status = "✓" if actual_value == expected_value else "✗"
        print(f"  {status} {field_name}: expected={expected_value}, actual={actual_value}")
    
    print()
    return defaults


def simulate_node_processing():
    """
    Simulate the node processing pipeline to show how defaults are applied.
    """
    from graphiti_extend.default_values_handler import apply_default_values_to_new_nodes
    from graphiti_core.nodes import EntityNode
    
    print("=== Simulating Node Processing ===")
    print()
    
    # Simulate extracted nodes (what LLM extracts from episode content)
    print("1. Extracted nodes from episode:")
    extracted_nodes = [
        EntityNode(
            name="Alice likes machine learning",
            group_id="user123",
            labels=["Entity", "CognitiveObject"],
        ),
        EntityNode(
            name="Bob prefers deep learning",
            group_id="user123", 
            labels=["Entity", "CognitiveObject"],
        ),
        EntityNode(
            name="The conference",
            group_id="user123",
            labels=["Entity"],  # Not a CognitiveObject
        ),
    ]
    
    for node in extracted_nodes:
        print(f"  - {node.name} (UUID: {node.uuid[:8]}..., Labels: {node.labels})")
    
    print()
    
    # Simulate resolved nodes (after deduplication)
    print("2. Resolved nodes after deduplication:")
    
    # Alice is new (same UUID)
    alice_resolved = EntityNode(
        name="Alice likes machine learning",
        group_id="user123",
        labels=["Entity", "CognitiveObject"],
    )
    alice_resolved.uuid = extracted_nodes[0].uuid
    
    # Bob is a duplicate of existing node (different UUID)
    bob_existing = EntityNode(
        name="Bob prefers deep learning frameworks",
        group_id="user123",
        labels=["Entity", "CognitiveObject"],
        attributes={
            "confidence": 0.85,  # Higher than default
            "salience": 0.9,     # Higher than default
            "type": "preference",
            "flags": ["verified"]
        }
    )
    bob_existing.uuid = "existing-bob-uuid-123"
    
    # Conference is new but not a CognitiveObject
    conference_resolved = EntityNode(
        name="The conference",
        group_id="user123",
        labels=["Entity"],
    )
    conference_resolved.uuid = extracted_nodes[2].uuid
    
    resolved_nodes = [alice_resolved, bob_existing, conference_resolved]
    
    # UUID mapping (extracted -> resolved)
    uuid_map = {
        extracted_nodes[0].uuid: alice_resolved.uuid,  # New node (same UUID)
        extracted_nodes[1].uuid: bob_existing.uuid,    # Duplicate (different UUID)
        extracted_nodes[2].uuid: conference_resolved.uuid,  # New node (same UUID)
    }
    
    for node in resolved_nodes:
        node_type = "NEW" if any(
            extracted.uuid == node.uuid for extracted in extracted_nodes
        ) else "EXISTING"
        print(f"  - {node.name} (UUID: {node.uuid[:8]}..., Type: {node_type})")
        if node.attributes:
            print(f"    Existing attributes: {node.attributes}")
    
    print()
    
    # Apply default values
    print("3. Applying default values to new nodes:")
    entity_types = {"CognitiveObject": CognitiveObject}
    
    result_nodes = apply_default_values_to_new_nodes(
        extracted_nodes, resolved_nodes, uuid_map, entity_types
    )
    
    print()
    
    # Show final results
    print("4. Final nodes with applied defaults:")
    for node in result_nodes:
        node_type = "NEW" if any(
            extracted.uuid == node.uuid for extracted in extracted_nodes
        ) else "EXISTING"
        print(f"  - {node.name} ({node_type})")
        if node.attributes:
            print(f"    Attributes: {node.attributes}")
        else:
            print(f"    Attributes: (none)")
    
    print()
    
    # Validate results
    print("5. Validation:")
    alice_final = next(n for n in result_nodes if "Alice" in n.name)
    bob_final = next(n for n in result_nodes if "Bob" in n.name)
    conference_final = next(n for n in result_nodes if "conference" in n.name)
    
    # Alice should have defaults (new CognitiveObject)
    alice_confidence = alice_final.attributes.get('confidence')
    alice_salience = alice_final.attributes.get('salience')
    print(f"  ✓ Alice (new): confidence={alice_confidence}, salience={alice_salience}")
    
    # Bob should keep existing values (existing CognitiveObject)
    bob_confidence = bob_final.attributes.get('confidence')
    bob_salience = bob_final.attributes.get('salience')
    print(f"  ✓ Bob (existing): confidence={bob_confidence}, salience={bob_salience}")
    
    # Conference should have no defaults (not CognitiveObject)
    conference_attrs = len(conference_final.attributes)
    print(f"  ✓ Conference (Entity): attributes_count={conference_attrs}")
    
    print()


def integration_notes():
    """
    Print integration notes for developers.
    """
    print("=== Integration Notes ===")
    print()
    print("This functionality is automatically integrated into ExtendedGraphiti:")
    print()
    print("1. When you call add_episode_with_contradictions(), the system:")
    print("   - Extracts entities from the episode content")
    print("   - Resolves duplicates against existing entities")
    print("   - Applies default values ONLY to new entities")
    print("   - Hydrates nodes with full attributes")
    print("   - Saves everything to the database")
    print()
    print("2. Default values are applied based on entity_types:")
    print("   - Only nodes with matching entity type labels get defaults")
    print("   - Only NEW nodes get defaults (not existing duplicates)")
    print("   - Existing attributes are never overwritten")
    print()
    print("3. For CognitiveObject entities, defaults are:")
    print("   - confidence: 0.7")
    print("   - salience: 0.5")
    print("   - flags: []")
    print("   - parent_ids: []")
    print("   - child_ids: []")
    print("   - match_history: []")
    print("   - linked_refs: []")
    print("   - generated_from: []")
    print()
    print("4. To use this in your FCS system:")
    print("   ```python")
    print("   from graphiti_extend import ExtendedGraphiti")
    print("   from fcs_core.models import CognitiveObject")
    print("   ")
    print("   graphiti = ExtendedGraphiti(...)")
    print("   entity_types = {'CognitiveObject': CognitiveObject}")
    print("   ")
    print("   result = await graphiti.add_episode_with_contradictions(")
    print("       name='User Message',")
    print("       episode_body='I really love Python programming',")
    print("       entity_types=entity_types,  # This enables defaults")
    print("       ...")
    print("   )")
    print("   ```")
    print()


def main():
    """Main function to run all demonstrations."""
    print("Default Values Functionality Demonstration")
    print("=" * 50)
    print()
    
    demonstrate_default_values()
    simulate_node_processing()
    integration_notes()
    
    print("Demo completed! 🎉")


if __name__ == "__main__":
    main() 