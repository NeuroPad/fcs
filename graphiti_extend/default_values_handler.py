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
from typing import Any, Dict
from datetime import datetime

from pydantic import BaseModel
from graphiti_core.nodes import EntityNode

logger = logging.getLogger(__name__)


def _safe_datetime_to_iso(dt: Any) -> str:
    """
    Safely convert any datetime-like object to ISO format string.
    
    Handles both Python datetime objects and Neo4j DateTime objects.
    """
    if dt is None:
        return None
    
    # If it's already a string, return it
    if isinstance(dt, str):
        return dt
    
    # If it has to_native method (Neo4j DateTime), convert it
    if hasattr(dt, 'to_native'):
        return dt.to_native().isoformat()
    
    # If it's a Python datetime, use isoformat
    if hasattr(dt, 'isoformat'):
        return dt.isoformat()
    
    # Return as-is if not a datetime
    return dt


def _sanitize_value(value: Any) -> Any:
    """
    Recursively sanitize a value to ensure it's JSON serializable.
    
    Converts datetime objects to ISO strings and handles nested structures.
    """
    if value is None:
        return None
    
    # Handle datetime objects
    if isinstance(value, datetime) or hasattr(value, 'to_native') or hasattr(value, 'isoformat'):
        return _safe_datetime_to_iso(value)
    
    # Handle lists
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    
    # Handle dictionaries
    if isinstance(value, dict):
        return {key: _sanitize_value(val) for key, val in value.items()}
    
    # Return as-is for other types
    return value


def sanitize_node_attributes(nodes: list[EntityNode]) -> list[EntityNode]:
    """
    Sanitize node attributes to ensure they are JSON serializable.
    
    This function converts any datetime objects in node attributes to ISO format strings
    to prevent JSON serialization errors during deduplication.
    
    Parameters
    ----------
    nodes : list[EntityNode]
        Nodes to sanitize
        
    Returns
    -------
    list[EntityNode]
        Nodes with sanitized attributes
    """
    for node in nodes:
        # Sanitize attributes
        if node.attributes:
            node.attributes = _sanitize_value(node.attributes)
        
        # Sanitize other node properties that might contain datetime objects
        if hasattr(node, 'created_at') and node.created_at:
            node.created_at = _safe_datetime_to_iso(node.created_at)
        
        if hasattr(node, 'updated_at') and node.updated_at:
            node.updated_at = _safe_datetime_to_iso(node.updated_at)
        
        if hasattr(node, 'valid_at') and node.valid_at:
            node.valid_at = _safe_datetime_to_iso(node.valid_at)
        
        if hasattr(node, 'invalid_at') and node.invalid_at:
            node.invalid_at = _safe_datetime_to_iso(node.invalid_at)
    
    return nodes


def apply_default_values_to_new_nodes(
    extracted_nodes: list[EntityNode],
    resolved_nodes: list[EntityNode],
    uuid_map: dict[str, str],
    entity_types: dict[str, BaseModel] | None = None,
) -> list[EntityNode]:
    """
    Apply default values to new entity nodes based on their entity types.
    
    This function identifies which nodes are new (not duplicates of existing nodes)
    and applies default values from their entity type definitions to their attributes.
    
    Parameters
    ----------
    extracted_nodes : list[EntityNode]
        The originally extracted nodes before resolution
    resolved_nodes : list[EntityNode]
        The resolved nodes after deduplication
    uuid_map : dict[str, str]
        Mapping from extracted node UUIDs to resolved node UUIDs
    entity_types : dict[str, BaseModel] | None
        Entity type definitions with default values
        
    Returns
    -------
    list[EntityNode]
        The resolved nodes with default values applied to new nodes
    """
    if not entity_types:
        return resolved_nodes
    
    # Create a mapping from extracted node index to resolved node
    extracted_to_resolved_map = {}
    for i, extracted_node in enumerate(extracted_nodes):
        extracted_uuid = extracted_node.uuid
        resolved_uuid = uuid_map.get(extracted_uuid, extracted_uuid)
        
        # Find the resolved node with this UUID
        for resolved_node in resolved_nodes:
            if resolved_node.uuid == resolved_uuid:
                extracted_to_resolved_map[i] = resolved_node
                break
    
    # Apply default values to new nodes
    new_nodes_count = 0
    for i, extracted_node in enumerate(extracted_nodes):
        resolved_node = extracted_to_resolved_map.get(i)
        if not resolved_node:
            continue
            
        # Check if this is a new node (UUIDs match) vs existing node (UUIDs different)
        is_new_node = extracted_node.uuid == resolved_node.uuid
        
        if is_new_node:
            # Apply default values for this entity type
            _apply_default_values_to_node(resolved_node, entity_types)
            new_nodes_count += 1
            logger.debug(f"Applied default values to new node: {resolved_node.name} (UUID: {resolved_node.uuid})")
    
    if new_nodes_count > 0:
        logger.info(f"Applied default values to {new_nodes_count} new nodes")
    
    return resolved_nodes


def _apply_default_values_to_node(
    node: EntityNode,
    entity_types: dict[str, BaseModel],
) -> None:
    """
    Apply default values to a single node based on its entity type.
    
    Parameters
    ----------
    node : EntityNode
        The node to apply default values to
    entity_types : dict[str, BaseModel]
        Entity type definitions with default values
    """
    # Find the entity type for this node (excluding 'Entity' label)
    entity_type_name = None
    for label in node.labels:
        if label != 'Entity' and label in entity_types:
            entity_type_name = label
            break
    
    if not entity_type_name:
        return
    
    entity_type_model = entity_types[entity_type_name]
    
    # Get default values from the model
    default_values = _extract_default_values_from_model(entity_type_model)
    
    if default_values:
        # Apply default values to node attributes (only if not already set)
        for field_name, default_value in default_values.items():
            if field_name not in node.attributes:
                node.attributes[field_name] = default_value
                logger.debug(f"Set default value for {field_name}: {default_value} on node {node.name}")


def _extract_default_values_from_model(model: BaseModel) -> dict[str, Any]:
    """
    Extract default values from a Pydantic model.
    
    Parameters
    ----------
    model : BaseModel
        The Pydantic model to extract defaults from
        
    Returns
    -------
    dict[str, Any]
        Dictionary of field names to default values
    """
    try:
        from pydantic_core import PydanticUndefined
    except ImportError:
        # Fallback for older Pydantic versions
        try:
            from pydantic import PydanticUndefined
        except ImportError:
            # For very old versions, use a different approach
            PydanticUndefined = object()
    
    default_values = {}
    
    for field_name, field_info in model.model_fields.items():
        # Check if field has a default value (not PydanticUndefined)
        if hasattr(field_info, 'default') and field_info.default is not PydanticUndefined:
            default_values[field_name] = field_info.default
        elif hasattr(field_info, 'default_factory') and field_info.default_factory is not None:
            # Handle default_factory (like default_factory=list)
            try:
                default_values[field_name] = field_info.default_factory()
            except Exception as e:
                logger.warning(f"Could not evaluate default_factory for field {field_name}: {e}")
    
    return default_values