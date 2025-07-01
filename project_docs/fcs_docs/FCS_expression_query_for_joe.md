# FCS - Expression Trigger Query for Prior High-Salience Ideas

This guide provides Cypher queries and response scaffolding for enabling memory-based reflection in FCS — specifically the kind of logic that supports system voice lines like:

> "You know, you once said that Y..."

The goal is to retrieve past Cognitive Objects (COs) from the graph that:

- Belong to the same user/session (`group_id`)
- Have high `salience`
- Are not the most recent message
- Optionally, share a relationship (`REINFORCES`, `CONTRADICTS`) with the current message

---

## 1. Retrieve Most Recent Input

```cypher
MATCH (input:CO {uuid: $current_input_uuid})
RETURN input.content AS recent_input, input.timestamp AS input_time
```

---

## 2. Get Prior High-Salience COs for Reflection

```cypher
MATCH (prior:CO)
WHERE prior.group_id = $group_id
  AND prior.salience > 0.4
  AND prior.uuid <> $current_input_uuid
  AND datetime(prior.timestamp) < datetime()
RETURN prior
ORDER BY prior.salience DESC, prior.timestamp DESC
LIMIT 3
```

---

## 3. (Optional) Retrieve Only Semantically Linked COs

```cypher
MATCH (input:CO {uuid: $current_input_uuid})-[:CONTRADICTS|REINFORCES]-(prior:CO)
WHERE prior.group_id = $group_id
  AND prior.salience > 0.4
RETURN prior
ORDER BY prior.salience DESC
LIMIT 3
```

---

## Output Use

These results can be injected into a natural language prompt to support FCS-style reflective behavior. Example:

> "You once said: '{prior.content}' — this may connect to what you're saying now. Want to explore that?"

The intent is not to answer questions, but to gently reflect themes or tensions across the graph state.

---

Let me know if you need a Python version for salience decay or reinforcement logic on fetch. This is the core of presence logic.
