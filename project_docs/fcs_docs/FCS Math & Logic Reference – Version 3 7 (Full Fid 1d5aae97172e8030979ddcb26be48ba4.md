# FCS Math & Logic Reference – Version 3.7 (Full Fidelity + Traceable State)

This document defines the cognitive logic, arbitration methods, contradiction handling, tracked idea behavior, expression triggers, session state integration, external access policy, and traceability model for the Fluid Cognitive Scaffolding (FCS) system. All logic adheres to the Fluid Processing Principle (FPP): structure is continuous, expression is contextual, and no transition is binary.

---

## 1. Cognitive Objects (COs)

- All inputs are parsed into **COs** — structured representations of user-expressed or system-derived ideas.
- Each CO includes:
    - `id`: Unique identifier (UUID)
    - `content`: Natural language text expressed or inferred
    - `type`: Enum: `idea`, `contradiction`, `reference`, `system_note`
    - `confidence`: Float [0.0 – 1.0] — how sure the system is this idea is currently valid
    - `salience`: Float — how central or reinforced this idea is within the session
    - `timestamp`: Time of creation or most recent reinforcement
    - `last_updated`: Timestamp — when the CO was last referenced, matched, or affected
    - `source`: One of `user`, `external`, or `system`
    - `flags`: Optional list, e.g. `tracked`, `contradiction`, `external`, `unverified`, `dismissed`
    - `parent_ids`: List of `UUIDs` — COs this idea directly builds on
    - `child_ids`: List of `UUIDs` — COs derived from this idea
    - `match_history`: Optional list of CO IDs that have semantically reinforced this CO
    - `arbitration_score`: Optional — last known score from arbitration pass
    - `linked_refs`: Optional list of `CO.id` or source string, e.g., reference DOI or URL
    - `external_metadata`: Optional dict with:
        - `source_url`: str
        - `title`: str
        - `authors`: List[str]
        - `abstract`: str
    - `generated_from`: Optional list of CO IDs used to construct this one (for LLM output tracking)

### Note:

All COs are stored in a single in-memory graph with directed edges. Edges are also typed separately (e.g., `contradicts`, `reinforces`) but parent/child are always retained.

---

## 1.1 Tracked Idea Logic (NEW in v3.4)

> FCS allows the user (or the system by confidence threshold) to designate specific COs as tracked, meaning future inputs will be monitored for relevance to that idea.
> 

### Marking an Idea as Tracked

- Tracked ideas carry the `flag=tracked`
- Tracking is initiated by the user or suggested by FCS:

> “You’ve said that a few different ways. Want me to keep track of that going forward?”
> 

### Matching Logic

- Every new CO is evaluated against tracked ideas:
    - Semantic similarity (embedding match)
    - Structural relationship (e.g. reinforces, contradicts, extends)
    - Optional keyword tagging or prompt overlap

### Behavior

- Matching increases `salience` of tracked CO
- System may selectively respond:

> “That touches on something we’re tracking. Want to connect it?”
> 
- Matching events are logged in CO metadata (`match_history`)

### Persistence

- In MVP, tracked ideas remain active indefinitely
- Tracked set is capped at 5 concurrent ideas by default (FIFO rotation)
- Post-MVP: add `tracked_decay_rate` to remove stale or irrelevant threads gently over time

---

## 1.2 Expression Trigger Conditions (NEW in v3.5)

> FCS does not speak continuously. It expresses only when certain thresholds are crossed, signaling a cognitively meaningful moment.
> 

### Trigger Classes and Conditions:

### 1. **Contradiction Trigger**

- `contradiction_count` ≥ 1 **and** `confidence_delta` > 0.2
- CO must contradict a previously reinforced or tracked idea

### 2. **Reinforcement Trigger**

- A `tracked` CO’s salience increases by ≥ 0.3 in the current window
- Repetition, semantic similarity, or user emphasis triggers this rise

### 3. **External Match Trigger**

- External CO matches existing idea with:
    - Cosine similarity ≥ 0.6 **and**
    - Semantic relevance confirmed by context

### 4. **Inflection or Novelty Trigger**

- A CO diverges sharply from recent input via semantic distance
    - Novelty score ≥ 0.7 (embedding delta or LLM-labeled shift)

### If a Trigger is Hit:

- FCS sets:

```json
{
  "should_express": true,
  "reason": "contradiction",
  "trigger_co_ids": ["abc123", "def456"]
}

```

- `route_intent()` is called → sets `reflect`, `challenge`, etc.
- `generate_prompt()` builds final LLM input
- System logs `expression_trigger_reason` in trace

### If No Trigger is Hit:

- `should_express = false`
- Log suppressed expression trace with reason
- FCS remains silent, graph continues evolving

---

## 1.3 Session State & Pipeline Integration (NEW in v3.6)

### SessionState

```json
{
  "active_graph": Graph,
  "tracked_cos": List[CO_ID],
  "last_intent": str,
  "last_response": List[CO_ID],
  "salience_map": Map[CO_ID, Float],
  "active_contradictions": List[CO_ID],
  "external_matches": List[CO_ID],
  "style_profile": "spoken_neutral_brief",
  "recently_spoken": Set[CO_ID],
  "last_arbitration_summary": Optional[Dict],
  "expression_attempt_failed": Optional[str] (with reason)
}

```

- Lives in memory and is rebuilt or cleared on reset
- Allows continuity of reasoning without personalization

---

## 1.4 LLM Output Failure Handling (NEW in v3.6)

- If LLM fails:

> “I’m not sure how to phrase that right now. Want to try again or move on?”
> 
- Trace must log:
    - Prompt payload
    - Arbitration context
    - Intent requested
    - Timestamp and failure reason (if any)

---

## 1.5 Style Profile Routing (Post-MVP)

- `style_profile` can be set manually or at session start
- Examples: `spoken_neutral_brief` (default), `analytical_structured`, `exploratory_expansive`
- Passed to `generate_prompt()`

---

## 1.6 Session Summary Generation (Post-MVP)

### `generate_session_summary(graph: Graph) -> str`

- Output includes:
    - Tracked ideas
    - Resolved vs. unresolved contradictions
    - External sources used

---

## 2. Graph State

- All COs are placed in a **single persistent session graph**
- Edges represent relationships:
    - `contradicts`
    - `supports`
    - `extends`
    - `elaborates`
- No graph actions are destructive. Contradictions are preserved, not collapsed.

### Salience Update Logic

- When a new CO matches a prior one:
    - `salience += reinforcement_weight`
- Salience and confidence decay independently:
    - `decay = base_decay_rate * time_elapsed` * reinforcement weight

---

## 3. Contradiction Detection

### `evaluate_contradictions(new_co: CO, graph) -> List[CO]`

- Compares `new_co.content` against existing COs
- Detects via:
    - Antonym pairs
    - Negation patterns
    - Logical reversals
- Generates contradiction COs
- Adds `contradicts` edges to both nodes
- Marks COs with `flag=contradicted`

---

## 4. Arbitration – Soft Relevance Ranking

### `run_arbitration(graph) -> CO`

- Evaluates all eligible COs
- Uses:
    - `confidence`
    - `recency`
    - `contradiction_density`
    - `reinforcement_density`

### Scoring Formula:

```
score(CO_i) = Softmax(α * confidence + β * recency + γ * reinforcement - δ * contradiction_density)

```

- Default weights: α=0.4, β=0.3, γ=0.2, δ=0.1
- Output: `focus_co` → used to drive intent

---

## 5. Expression Threshold Logic (FPP-Compliant)

- [References 1.2 and SessionState]
- `should_express = true` only if trigger condition is met
- Otherwise: no output, expression is suppressed and logged

---

## 6. External Knowledge Integration

- FCS may perform `external_search(query)` if user consents
- Sources must be domain-whitelisted (e.g., `nih.gov`, `pubmed`, `scholar.google.com`)
- Full article fallback only post-MVP
- External references parsed into COs with:
    - `confidence=0.3`
    - `source='external'`
    - `flag='unverified'`
- Paywalled summary fallback handled gracefully

---

## 7. Traceability (OpenTelemetry)

### Instrumented Functions:

- `parse_input_to_CO`
- `evaluate_contradictions`
- `run_arbitration`
- `generate_response`
- `external_search`
- `parse_external_to_CO`

### Required Metadata:

- `expression_trigger_reason`
- `expression_attempt_failed`
- `generated_from`
- `last_response`
- `style_profile`
- `external_metadata`

Traces must reconstruct:

- Why something was said
- Why something wasn’t
- What idea or trigger drove it
- How the system structured and prioritized thought

---

FCS is not reactive. It’s not generative. It’s structurally cognitive. And it shows its work.