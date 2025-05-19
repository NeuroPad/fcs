"""
Contradiction detector for identifying contradictions between cognitive objects.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from graphiti_core.llm_client import LLMClient
from graphiti_extend.custom_edges import CONTRADICTS
from fcs_core.cognitive_objects import (
    CognitiveObject, 
    COType, 
    COSource, 
    COFlags, 
    FCSSessionState
)

logger = logging.getLogger(__name__)

class ContradictionDetector:
    """
    Detects contradictions between cognitive objects in an FCS session.
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize the ContradictionDetector.
        
        Parameters
        ----------
        llm_client : LLMClient
            The LLM client to use for detecting contradictions
        """
        self.llm_client = llm_client
    
    async def detect_contradictions(
        self,
        new_co: CognitiveObject,
        session_state: FCSSessionState,
        similarity_threshold: float = 0.7,
        confidence_threshold: float = 0.3,
    ) -> List[Tuple[CognitiveObject, float]]:
        """
        Detect contradictions between a new cognitive object and existing tracked ones.
        
        Parameters
        ----------
        new_co : CognitiveObject
            The new cognitive object to check
        session_state : FCSSessionState
            The current session state
        similarity_threshold : float, optional
            The threshold for semantic similarity, by default 0.7
        confidence_threshold : float, optional
            The minimum confidence for considered objects, by default 0.3
            
        Returns
        -------
        List[Tuple[CognitiveObject, float]]
            List of contradicting cognitive objects and their contradiction scores
        """
        if new_co.type != COType.IDEA:
            # Only check contradictions for ideas
            return []
        
        contradictions = []
        
        # Only check tracked COs with sufficient confidence
        candidates = [
            co for co_id, co in session_state.active_graph.items()
            if (co_id in session_state.tracked_cos or 
                COFlags.TRACKED.value in co.flags or 
                COFlags.CONTRADICTION.value in co.flags) and
            co.confidence >= confidence_threshold and
            co.id != new_co.id and
            co.type == COType.IDEA
        ]
        
        for existing_co in candidates:
            contradiction_score = await self._evaluate_contradiction(new_co, existing_co)
            
            if contradiction_score >= similarity_threshold:
                contradictions.append((existing_co, contradiction_score))
        
        return sorted(contradictions, key=lambda x: x[1], reverse=True)
    
    async def _evaluate_contradiction(
        self,
        co1: CognitiveObject,
        co2: CognitiveObject
    ) -> float:
        """
        Evaluate the contradiction between two cognitive objects using the LLM.
        
        Parameters
        ----------
        co1 : CognitiveObject
            The first cognitive object
        co2 : CognitiveObject
            The second cognitive object
            
        Returns
        -------
        float
            A score between 0 and 1 indicating the level of contradiction
        """
        prompt = self._build_contradiction_prompt(co1, co2)
        
        response = await self.llm_client.agenerate(prompt)
        
        try:
            result = self._parse_contradiction_response(response)
            return result["contradiction_score"]
        except Exception as e:
            logger.error(f"Error parsing contradiction response: {e}")
            return 0.0
    
    def _build_contradiction_prompt(self, co1: CognitiveObject, co2: CognitiveObject) -> str:
        """
        Build a prompt for the LLM to evaluate contradiction between two COs.
        
        Parameters
        ----------
        co1 : CognitiveObject
            The first cognitive object
        co2 : CognitiveObject
            The second cognitive object
            
        Returns
        -------
        str
            The prompt for the LLM
        """
        return f"""
        Evaluate whether the following two statements contradict each other:
        
        Statement 1: "{co1.content}"
        Statement 2: "{co2.content}"
        
        Consider direct contradictions, logical inconsistencies, and factual disagreements.
        Assign a contradiction score between 0.0 and 1.0, where:
        - 0.0 means no contradiction (the statements are consistent or unrelated)
        - 0.5 means partial contradiction (the statements have some inconsistencies)
        - 1.0 means complete contradiction (the statements directly oppose each other)
        
        Respond in JSON format with the following structure:
        {{
            "contradiction_score": float, // between 0.0 and 1.0
            "reasoning": string, // brief explanation of the contradiction assessment
            "contradicting_elements": [string] // specific elements that contradict (if any)
        }}
        """
    
    def _parse_contradiction_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response to extract the contradiction assessment.
        
        Parameters
        ----------
        response : str
            The LLM response
            
        Returns
        -------
        Dict[str, Any]
            The parsed contradiction assessment
        """
        # Simple implementation - would need more robust parsing in production
        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback if the response is not valid JSON
            logger.warning(f"Invalid JSON response: {response}")
            return {
                "contradiction_score": 0.0,
                "reasoning": "Failed to parse response",
                "contradicting_elements": []
            }
    
    async def create_contradiction_co(
        self,
        co1: CognitiveObject,
        co2: CognitiveObject,
        contradiction_score: float,
        session_state: FCSSessionState
    ) -> CognitiveObject:
        """
        Create a new contradiction cognitive object.
        
        Parameters
        ----------
        co1 : CognitiveObject
            The first contradicting cognitive object
        co2 : CognitiveObject
            The second contradicting cognitive object
        contradiction_score : float
            The contradiction score
        session_state : FCSSessionState
            The current session state
            
        Returns
        -------
        CognitiveObject
            The created contradiction cognitive object
        """
        # Generate content for the contradiction CO
        content = f"Contradiction detected between:\n1. \"{co1.content}\"\n2. \"{co2.content}\""
        
        # Create the contradiction CO
        contradiction_co = CognitiveObject(
            content=content,
            type=COType.CONTRADICTION,
            confidence=contradiction_score,
            salience=max(co1.salience, co2.salience),
            source=COSource.SYSTEM,
            flags=[COFlags.CONTRADICTION.value],
            parent_ids=[co1.id, co2.id],
        )
        
        # Add the contradiction CO to the session state
        session_state.add_cognitive_object(contradiction_co)
        
        # Add child references
        co1.add_child(contradiction_co.id)
        co2.add_child(contradiction_co.id)
        
        # Add contradiction flags to the contradicting COs if not already present
        if not co1.has_flag(COFlags.CONTRADICTION):
            co1.add_flag(COFlags.CONTRADICTION)
        
        if not co2.has_flag(COFlags.CONTRADICTION):
            co2.add_flag(COFlags.CONTRADICTION)
        
        return contradiction_co 