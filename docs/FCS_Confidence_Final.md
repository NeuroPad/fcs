FCS: Confidence Mechanism Specification
Author: Development Team (Based on Brian's Specification)
Audience: Engineering Implementation
Date: January 2025

## What is Confidence:

Confidence is a float between 0.0 and 1.0 that represents how stable, supported, and coherent a Cognitive Object (CO) is—based on both user behavior and relationships within the graph. It reflects the system's certainty about the accuracy and reliability of information stored in each entity.

Confidence represents:
- Origin type and source reliability (user-given vs. inferred)
- Contradiction history and resolution patterns
- Reinforcement from other high-confidence entities in the network
- Revision frequency and stability over time
- Long-term dormancy and lack of validation

## Initial Confidence Values:

**0.8** — User-given CO (direct user statement or confirmation)
**0.5** — Inferred from context (extracted from conversation context)
**0.4** — System-suggested or speculative (algorithmic inference)
**0.2** — Minimum threshold before flagging as unstable
**0.1** — Deletion consideration threshold

## Confidence Increases When:

**User Validation:**
- **+0.1** — User reaffirms CO (explicit confirmation or repetition)
- **+0.05** — User references CO positively in conversation
- **+0.03** — CO appears in user's reasoning chain

**Network Reinforcement:**
- **+0.1** — Supported by another CO with confidence > 0.75
- **+0.05** — Referenced during reasoning or summarization processes
- **+0.05** — Connected to ≥3 COs with confidence > 0.7 (structural support)
- **+0.03** — Indirect support through 2-hop network connections

**System Validation:**
- **+0.02** — Consistent across multiple episodes without contradiction
- **+0.01** — Corroborated by external sources (if available)

## Confidence Decreases When:

**Contradiction Events:**
- **-0.3** — Contradicted by a CO with confidence > 0.7
- **-0.15** — Repeated contradiction without resolution
- **-0.1** — User revises or weakens the CO explicitly
- **-0.05** — Soft contradiction (conflicting implications)

**Temporal Degradation:**
- **-0.05** — Not referenced for >30 days (dormancy decay)
- **-0.1** — No references for >90 days (extended dormancy)
- **-0.15** — Orphaned entity with no supporting connections

**User Behavior:**
- **-0.1** — User questions or expresses uncertainty about CO
- **-0.05** — User provides conflicting information indirectly

Values are additive but capped between 0.0 and 1.0.

## How Confidence is Used:

**Contradiction Arbitration:**
- Choose the CO with higher confidence when contradictions are unresolved
- Confidence differential determines override strength
- Low confidence entities yield to high confidence ones

**Expression and Communication:**
- Lower-confidence COs are described more tentatively ("it seems", "possibly", "you might")
- High-confidence COs are stated with certainty ("you definitely", "you always")
- Confidence levels influence language certainty markers

**Memory Management:**
- Flag COs with confidence < 0.4 as unstable for review
- Suppress COs < 0.2 from normal recall unless explicitly requested
- Prioritize high-confidence entities in search and retrieval

**Network Effects:**
- High-confidence nodes provide stronger support to connected entities
- Confidence propagation through relationship networks
- Trust weighting in reasoning and inference chains

## CO Object Structure Requirements:

```json
{
    "confidence": "float (0.0-1.0)",
    "confidence_last_updated": "timestamp",
    "confidence_history": "array of {timestamp, value, trigger, reason}",
    "origin_type": "enum (user_given, inferred, system_suggested)",
    "revisions": "integer count of modifications",
    "last_user_validation": "timestamp",
    "supporting_CO_ids": "array with confidence annotations",
    "contradicting_CO_ids": "array with confidence annotations",
    "contradiction_resolution_status": "enum (unresolved, user_resolved, system_resolved)",
    "dormancy_start": "timestamp of last reference",
    "stability_score": "float (derived from revision frequency)"
}
```

## Confidence Update Triggers:

**During Episode Processing:**
1. **Entity Extraction** — Assign initial confidence based on origin type
2. **Duplicate Resolution** — Apply user reaffirmation if entity mentioned again
3. **Contradiction Detection** — Apply contradiction penalties and network effects
4. **Network Analysis** — Calculate structural support from connected entities
5. **Post-Processing** — Update confidence history and propagate changes

**During Search Operations:**
1. **User Query Processing** — Boost confidence for entities user actively seeks
2. **Result Selection** — Track which entities user finds useful/relevant
3. **Follow-up Questions** — Detect user validation or questioning patterns

**During Conversation Flow:**
1. **User Confirmations** — Direct confidence boosts from positive responses
2. **User Corrections** — Apply revision penalties and update confidence
3. **Reasoning Chains** — Boost confidence for entities used in logical processes
4. **Uncertainty Expressions** — Detect and apply uncertainty penalties

**Scheduled Maintenance:**
1. **Dormancy Analysis** — Apply time-based confidence decay
2. **Network Recalculation** — Update structural support scores
3. **Contradiction Resolution** — Attempt to resolve confidence conflicts
4. **Stability Assessment** — Calculate long-term confidence trends

## Implementation Steps:

### Phase 1: Core Confidence Infrastructure
1. **Extend EntityNode Model** — Add confidence fields and metadata tracking
2. **Create ConfidenceManager Class** — Central orchestrator for all confidence operations
3. **Database Schema Updates** — Add confidence columns, indexes, and history tables
4. **Basic Computation Engine** — Initial confidence assignment and simple updates

### Phase 2: Origin Type Classification
1. **Entity Origin Detector** — Classify extraction source (user/inferred/system)
2. **User Statement Parser** — Identify direct user assertions vs. contextual inference
3. **Confidence Assignment Rules** — Apply initial confidence based on origin classification
4. **Origin Metadata Tracking** — Store provenance information for confidence decisions

### Phase 3: User Validation System
1. **Confirmation Pattern Recognition** — Detect user reaffirmation in conversation
2. **Correction Detection** — Identify when users revise or challenge existing COs
3. **Uncertainty Expression Analysis** — Parse language patterns indicating doubt
4. **Validation Tracking** — Record user interaction patterns with specific entities

### Phase 4: Network Reinforcement Engine
1. **Structural Support Calculator** — Analyze entity connections and support networks
2. **Confidence Propagation** — Spread confidence changes through relationship graphs
3. **Multi-hop Analysis** — Calculate indirect support through network pathways
4. **Network Stability Metrics** — Assess overall confidence ecosystem health

### Phase 5: Contradiction Integration
1. **Confidence-Based Arbitration** — Use confidence in contradiction resolution
2. **Dynamic Confidence Updates** — Real-time confidence changes during conflicts
3. **Resolution Status Tracking** — Monitor how contradictions affect confidence over time
4. **Cascade Effect Management** — Handle confidence changes rippling through networks

### Phase 6: Temporal Dynamics
1. **Dormancy Detection** — Identify entities not referenced for extended periods
2. **Decay Scheduling** — Regular confidence degradation for unused entities
3. **Stability Analysis** — Track confidence stability and revision patterns
4. **Long-term Trend Analysis** — Identify entities with declining reliability

### Phase 7: Expression Integration
1. **Language Certainty Mapping** — Convert confidence levels to expression styles
2. **Tentative Language Generation** — Modify responses based on confidence levels
3. **Uncertainty Communication** — Clearly communicate system confidence to users
4. **Confidence Visualization** — Display confidence levels in user interfaces

## Technical Integration Points:

**In ExtendedGraphiti.add_episode_with_contradictions():**
- Assign initial confidence during entity extraction
- Apply user reaffirmation during duplicate detection
- Execute network reinforcement after contradiction resolution
- Update confidence history with episode context

**In Node Extraction Pipeline:**
- Classify entity origin type (user-given, inferred, system-suggested)
- Apply appropriate initial confidence values
- Track extraction confidence metadata
- Store provenance information for future reference

**In Contradiction Detection System:**
- Use confidence levels to determine contradiction winner
- Apply confidence penalties to contradicted entities
- Boost confidence for entities that successfully contradict others
- Track contradiction resolution impact on confidence

**In Search and Retrieval:**
- Weight search results by confidence levels
- Suppress low-confidence entities unless explicitly requested
- Track user interaction with confidence-ranked results
- Apply confidence boosts for user-selected entities

**In Conversation Management:**
- Modify response language based on entity confidence levels
- Generate uncertainty markers for low-confidence information
- Detect user validation patterns and update confidence accordingly
- Handle user corrections and apply appropriate confidence adjustments

## Success Metrics:

1. **Accuracy Correlation** — Higher confidence entities should be more accurate over time
2. **User Trust** — Users should find high-confidence information more reliable
3. **Contradiction Resolution** — Confidence-based arbitration should resolve conflicts effectively
4. **System Calibration** — Confidence levels should correlate with actual reliability
5. **Response Quality** — Tentative language should improve user experience with uncertain information

## Special Implementation Considerations:

### Confidence Propagation Algorithm:
- Direct connections: confidence * 0.1 boost to connected entities
- 2-hop connections: confidence * 0.05 boost to indirectly connected entities
- Decay factor: propagation strength decreases with network distance
- Threshold filtering: only entities with confidence > 0.7 provide network support

### User Validation Detection Patterns:
- **Explicit confirmation**: "Yes, that's right", "Exactly", "Correct"
- **Repetition patterns**: User mentions same information multiple times
- **Correction patterns**: "Actually, it's...", "No, I meant..."
- **Uncertainty expressions**: "I think", "Maybe", "I'm not sure"

### Confidence-Based Language Modulation:
- **High confidence (>0.8)**: "You definitely prefer...", "You always..."
- **Medium confidence (0.5-0.8)**: "You generally prefer...", "You often..."
- **Low confidence (<0.5)**: "You might prefer...", "It seems you..."
- **Very low confidence (<0.3)**: "I'm not certain, but you possibly..."

## Notes for Implementation:

- All confidence code must be implemented in `graphiti_extend` package only
- No modifications to `graphiti_core` allowed
- Integrate with existing salience system without conflicts
- Maintain backward compatibility with existing entity structures
- Implement comprehensive logging for confidence decisions
- Design for efficient batch confidence updates
- Consider performance impact on large entity networks
- Ensure confidence updates are atomic and consistent
- Handle edge cases (e.g., circular confidence dependencies)
- Provide debugging tools for confidence decision analysis