# FCS - Soft Disagreement Logic for Expression

This guide outlines how to implement a form of system-level disagreement in FCS using salience and confidence, rather than binary contradiction.

The goal is not to say “you’re wrong,” but rather:
> “What you just said doesn’t carry the same weight as what you’ve said before.”

---

## Core Concepts

### Salience
Represents how often a CO (Cognitive Object) has been referenced, reinforced, or matched over time.

### Confidence
Represents how semantically clear, meaningful, or grounded a given CO is at the time of creation.

---

## Logic Overview

FCS should trigger a disagreement **only** when:

- A new input **conflicts with a prior CO**
- The prior CO has **high salience** AND **high confidence**
- The new input has **low confidence**

---

## Cypher: Identify Conflicting COs with High Weight

```cypher
MATCH (input:CO {uuid: $current_input_uuid})-[:CONTRADICTS]-(prior:CO)
WHERE prior.group_id = $group_id
  AND prior.salience > 0.7
  AND prior.confidence > 0.6
  AND input.confidence < 0.5
RETURN prior, input
LIMIT 1
```

---

## Prompt Format for System Disagreement

Inject this into the LLM prompt:

> "You’ve previously said: '{prior.content}', and that idea has been reinforced a lot. What you just said seems to conflict with that. Want to look at it?"

Optional: Offer to track both, dismiss the new one, or update the system’s focus.

---

## Output Behavior

This logic should set `should_express = true`  
and flag a response intent like `reflective_disagreement`.

---

Let us know if you want to extend this to multi-hop contradiction analysis or introduce adjustable thresholds.
