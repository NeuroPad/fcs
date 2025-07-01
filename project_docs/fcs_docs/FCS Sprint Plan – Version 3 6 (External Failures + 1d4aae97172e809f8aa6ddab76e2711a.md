# FCS Sprint Plan – Version 3.6 (External Failures + Tracked Ideas)

This execution roadmap defines the full MVP delivery of FCS. Includes tracked idea logic and failover handling for external search. All tasks are implementation-ready and FPP-aligned.

---

## 🧱 Sprint 1 – Foundations (50 hrs)

### Tasks:

- `CO` schema with full metadata
- `parse_input_to_CO(text)`
- In-memory graph (DAG)
- `reset()` wipes all session state
- `load_text_block()` for longform parsing

---

## 🧠 Sprint 2 – Contradiction + Tracking (50 hrs)

### Tasks:

- `evaluate_contradictions()` logic and edge typing
- `run_arbitration()` w/ score tuning
- `mark_as_tracked(co)` → `flag=tracked`
- Match future COs against tracked set
- Log `match_history`

---

## 🗣 Sprint 3 – Voice + LLM Response (50 hrs)

### Tasks:

- STT integration → `parse_input_to_CO()`
- `route_intent()` selects: `reflect`, `challenge`, `external_request`, `reframe`
- `generate_prompt()` → LLM → TTS
- Voice in → response out loop complete

---

## 🔍 Sprint 4 – Trace + External Source + Failover (50 hrs)

### Tasks:

- `external_search(query)` → scoped, domain-filtered
- `parse_external_to_CO()` → low-confidence, `flag=external`
- Handle paywall: offer abstract summary
- **On failure (timeout, 404, etc):**
    - FCS should say:
        
        > “That source didn’t respond. Want to rephrase or keep going?”
        > 
    - Never fabricate or fill
    - Log failed query + fallback status
- Trace all spans via OpenTelemetry

---

## Demo-Ready Conditions:

- Tracked ideas surface when reinforced
- Contradictions handled, not collapsed
- External pulls are real or gracefully skipped
- Voice input → structured response
- Reset wipes all memory

FCS should never break presence. If it can’t help, it should still protect the moment.