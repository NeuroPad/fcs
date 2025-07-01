# FCS – Developer Summary (Sprint 2 Trunk Focus)

This summary outlines the current state of the FCS system, the key structural innovations, and a clean breakdown of what constitutes the "trunk" of the knowledge tree—the core functionality and graph architecture Joseph should focus on completing before expressive complexity is added.

---

## ✅ Where the Project Is Now

FCS is an early but working prototype of a system that helps users think by listening, storing structured memory, surfacing contradiction, and speaking only when conditions are meaningfully met. It is not a chatbot. It does not perform. It scaffolds cognition.

The system currently supports:

- Document ingestion (PDF, TXT, JSON, MD)
- Chunk parsing with embedding
- Graph storage via Neo4j (nodes and typed edges)
- GraphRAG retrieval
- Session-specific graph partitioning via `group_id`
- A functioning chat interface with traceable source return

Voice interface, expression restraint, salience logic, and contradiction-based reflection are being actively implemented.

---

## 🧠 What FCS Is (Big Picture)

FCS is a memory and presence engine.
It listens, stores what matters, detects contradiction, and only responds when the structural state justifies doing so. It’s a quiet, reflective system that becomes more useful over time.

It’s being built for:

- Cognitive reflection
- Theme tracking
- Personal thinking support
- Human-in-the-loop scaffolding

It is not a chatbot, assistant, or reasoning simulator. It is a **memory scaffold that only speaks when the shape of a user’s thinking demands it.**

---

## 🔧 Major Innovations

- **CO Graph Memory:** Memory is structured as Cognitive Objects (COs), each with salience, confidence, timestamp, and reinforcement history.
- **Salience & Confidence:** Nodes are weighted over time via reinforcement and decay.
- **Contradiction Holding:** System detects contradiction and defers expression unless salience/confidence warrants reflection.
- **Expression Gating:** `should_express` logic drives when and how FCS responds.
- **Session-Scoped Memory:** Each graph is tied to a `group_id`, isolating context.
- **Seeded Voice:** Cold-start session logic introduces a known system opinion for the user to respond to or push against.

---

## 🌲 TRUNK: What Joseph Should Build Before Expression Layers

This list defines the *foundational graph structure and logic* that must be in place before any higher-order UX, voice timing, or reflection behavior is introduced.

### Core Graph Schema (CO nodes):

- `uuid`
- `content`
- `type` (idea, contradiction, reference, system_opinion, etc.)
- `confidence` (float)
- `salience` (float)
- `timestamp`
- `group_id`
- `source` (user, system, external)
- `flags` (list)
- `parent_ids` / `child_ids` (optional for structure lineage)

### Edge Types (Sprint 5):

- `REINFORCES`
- `CONTRADICTS`
- `EXTENDS`
- `MENTIONS` (optional / implicit)

### Salience Logic:

- On semantic match → increase salience
- On inactivity (by time) → decay salience
- Salience capped between [0.0 – 1.0]

### Confidence:

- Set at CO creation (LLM-estimated or static for now)

### Contradiction Detection:

- Semantic or logical triggers
- Contradictory nodes linked with `CONTRADICTS`
- Track source and salience of both COs involved

### Expression Trigger (core logic only):

- If a high-salience, high-confidence node is contradicted → flag for possible output
- If new node conflicts with reinforced prior → flag for response *if* salience delta exceeds threshold

---

## 🔜 Next Layer (Post-Trunk)

- Expression templates: *“You said X before. This feels different. Want to look at it?”*
- Voice interface
- Live salience heatmaps
- Graph visualization

---

This doc allows Joseph to continue building the system’s core with clarity, without waiting for aesthetic polish. Once this trunk is complete, FCS will be ready to behave like the quiet presence it was designed to be.