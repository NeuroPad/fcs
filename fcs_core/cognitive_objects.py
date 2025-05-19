"""
Implementation of Cognitive Objects (COs) as defined in the FCS specifications.
"""

from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Set
from uuid import uuid4
from pydantic import BaseModel, Field

class COType(Enum):
    """
    Types of Cognitive Objects as defined in the FCS specification.
    """
    IDEA = "idea"
    CONTRADICTION = "contradiction"
    REFERENCE = "reference"
    SYSTEM_NOTE = "system_note"

class COSource(Enum):
    """
    Source of Cognitive Objects as defined in the FCS specification.
    """
    USER = "user"
    EXTERNAL = "external"
    SYSTEM = "system"

class COFlags(Enum):
    """
    Optional flags for Cognitive Objects as defined in the FCS specification.
    """
    TRACKED = "tracked"
    CONTRADICTION = "contradiction"
    EXTERNAL = "external"
    UNVERIFIED = "unverified"
    DISMISSED = "dismissed"

class CognitiveObject(BaseModel):
    """
    Representation of a Cognitive Object (CO) as defined in the FCS specifications.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    type: COType
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    salience: float = Field(default=0.5)
    timestamp: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    source: COSource
    flags: List[str] = Field(default_factory=list)
    parent_ids: List[str] = Field(default_factory=list)
    child_ids: List[str] = Field(default_factory=list)
    match_history: Optional[List[str]] = Field(default=None)
    arbitration_score: Optional[float] = Field(default=None)
    linked_refs: Optional[List[str]] = Field(default=None)
    external_metadata: Optional[Dict[str, Any]] = Field(default=None)
    generated_from: Optional[List[str]] = Field(default=None)
    
    def add_flag(self, flag: COFlags) -> None:
        """
        Add a flag to the Cognitive Object.
        
        Parameters
        ----------
        flag : COFlags
            The flag to add
        """
        if flag.value not in self.flags:
            self.flags.append(flag.value)
            self.last_updated = datetime.now()
    
    def remove_flag(self, flag: COFlags) -> None:
        """
        Remove a flag from the Cognitive Object.
        
        Parameters
        ----------
        flag : COFlags
            The flag to remove
        """
        if flag.value in self.flags:
            self.flags.remove(flag.value)
            self.last_updated = datetime.now()
    
    def has_flag(self, flag: COFlags) -> bool:
        """
        Check if the Cognitive Object has a specific flag.
        
        Parameters
        ----------
        flag : COFlags
            The flag to check
            
        Returns
        -------
        bool
            True if the flag is present, False otherwise
        """
        return flag.value in self.flags
    
    def add_parent(self, parent_id: str) -> None:
        """
        Add a parent Cognitive Object.
        
        Parameters
        ----------
        parent_id : str
            The ID of the parent CO
        """
        if parent_id not in self.parent_ids:
            self.parent_ids.append(parent_id)
            self.last_updated = datetime.now()
    
    def add_child(self, child_id: str) -> None:
        """
        Add a child Cognitive Object.
        
        Parameters
        ----------
        child_id : str
            The ID of the child CO
        """
        if child_id not in self.child_ids:
            self.child_ids.append(child_id)
            self.last_updated = datetime.now()
    
    def record_match(self, matched_co_id: str) -> None:
        """
        Record a match with another Cognitive Object.
        
        Parameters
        ----------
        matched_co_id : str
            The ID of the matching CO
        """
        if self.match_history is None:
            self.match_history = []
        
        if matched_co_id not in self.match_history:
            self.match_history.append(matched_co_id)
            self.last_updated = datetime.now()
    
    def increase_salience(self, amount: float = 0.1) -> None:
        """
        Increase the salience of the Cognitive Object.
        
        Parameters
        ----------
        amount : float, optional
            The amount to increase salience by, by default 0.1
        """
        self.salience = min(1.0, self.salience + amount)
        self.last_updated = datetime.now()
    
    def decrease_salience(self, amount: float = 0.1) -> None:
        """
        Decrease the salience of the Cognitive Object.
        
        Parameters
        ----------
        amount : float, optional
            The amount to decrease salience by, by default 0.1
        """
        self.salience = max(0.0, self.salience - amount)
        self.last_updated = datetime.now()
    
    def set_arbitration_score(self, score: float) -> None:
        """
        Set the arbitration score for the Cognitive Object.
        
        Parameters
        ----------
        score : float
            The arbitration score
        """
        self.arbitration_score = score
        self.last_updated = datetime.now()

class FCSSessionState(BaseModel):
    """
    Represents the state of an FCS session.
    """
    active_graph: Dict[str, CognitiveObject] = Field(default_factory=dict)
    tracked_cos: List[str] = Field(default_factory=list)
    last_intent: Optional[str] = None
    last_response: List[str] = Field(default_factory=list)
    salience_map: Dict[str, float] = Field(default_factory=dict)
    active_contradictions: List[str] = Field(default_factory=list)
    external_matches: List[str] = Field(default_factory=list)
    style_profile: str = "spoken_neutral_brief"
    recently_spoken: Set[str] = Field(default_factory=set)
    last_arbitration_summary: Optional[Dict[str, Any]] = None
    expression_attempt_failed: Optional[str] = None
    
    def add_cognitive_object(self, co: CognitiveObject) -> None:
        """
        Add a Cognitive Object to the session state.
        
        Parameters
        ----------
        co : CognitiveObject
            The Cognitive Object to add
        """
        self.active_graph[co.id] = co
        self.salience_map[co.id] = co.salience
        
        # If the CO is tracked, add it to tracked_cos
        if COFlags.TRACKED.value in co.flags:
            if co.id not in self.tracked_cos:
                self.tracked_cos.append(co.id)
        
        # If the CO is a contradiction, add it to active_contradictions
        if co.type == COType.CONTRADICTION or COFlags.CONTRADICTION.value in co.flags:
            if co.id not in self.active_contradictions:
                self.active_contradictions.append(co.id)
        
        # If the CO is from an external source, add it to external_matches
        if co.source == COSource.EXTERNAL:
            if co.id not in self.external_matches:
                self.external_matches.append(co.id)
    
    def get_cognitive_object(self, co_id: str) -> Optional[CognitiveObject]:
        """
        Get a Cognitive Object by ID.
        
        Parameters
        ----------
        co_id : str
            The ID of the Cognitive Object
            
        Returns
        -------
        Optional[CognitiveObject]
            The Cognitive Object if found, None otherwise
        """
        return self.active_graph.get(co_id)
    
    def track_cognitive_object(self, co_id: str) -> None:
        """
        Mark a Cognitive Object as tracked.
        
        Parameters
        ----------
        co_id : str
            The ID of the Cognitive Object to track
        """
        co = self.get_cognitive_object(co_id)
        if co:
            co.add_flag(COFlags.TRACKED)
            if co_id not in self.tracked_cos:
                self.tracked_cos.append(co_id)
    
    def untrack_cognitive_object(self, co_id: str) -> None:
        """
        Unmark a Cognitive Object as tracked.
        
        Parameters
        ----------
        co_id : str
            The ID of the Cognitive Object to untrack
        """
        co = self.get_cognitive_object(co_id)
        if co:
            co.remove_flag(COFlags.TRACKED)
            if co_id in self.tracked_cos:
                self.tracked_cos.remove(co_id)
    
    def reset(self) -> None:
        """
        Reset the session state.
        """
        self.active_graph = {}
        self.tracked_cos = []
        self.last_intent = None
        self.last_response = []
        self.salience_map = {}
        self.active_contradictions = []
        self.external_matches = []
        self.recently_spoken = set()
        self.last_arbitration_summary = None
        self.expression_attempt_failed = None 