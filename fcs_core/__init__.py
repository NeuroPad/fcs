"""
Core implementation of the Fluid Cognitive Scaffolding (FCS) system
using graphiti_core and graphiti_extend.
"""

from fcs_core.contradiction_detector import ContradictionDetector
from fcs_core.cognitive_objects import (
    CognitiveObject, 
    COType, 
    COSource, 
    COFlags, 
    FCSSessionState
)
from fcs_core.fcs import FCS 