"""
Extension module for graphiti_core that adds additional functionalities
without modifying the original codebase.
"""

from graphiti_extend.custom_edges import (
    REINFORCES,
    CONTRADICTS,
    EXTENDS,
    SUPPORTS,
    ELABORATES,
)
from graphiti_extend.enhanced_graphiti import EnhancedGraphiti
from graphiti_extend.contradiction_handler import detect_and_connect_contradictions 