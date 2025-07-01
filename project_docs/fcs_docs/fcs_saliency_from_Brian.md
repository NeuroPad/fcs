FCS: Salience Mechanism Specification
Author: Brian
Purpose: Define how salience is calculated, updated, and used in the belief graph
Audience: Joseph (engineering implementation)
What is Salience:
Salience represents how mentally active or contextually relevant a belief is within the system. It is used to prioritize beliefs during recall, contradiction surfacing, summarization, and arbitration.
It is a float between 0.0 and 1.0.
Salience is affected by:
Recency – when it was last mentioned, used, updated, or recalled
Frequency – how often it’s referenced or interacted with
Connectivity – how many other beliefs it’s connected to
Confidence-weighted proximity – whether it’s connected to high-confidence nodes
Initial value on creation:
salience = 0.5
Salience increases when:
+0.3 — mentioned in conversation (explicit reference)
+0.2 — used in reasoning or inference generation
+0.25 — recalled explicitly by the user
+0.1 — contradicted directly
+0.2 — involved in arbitration
+0.15 — connected to 3 or more nodes with confidence > 0.75
+0.1 — within 1–2 hops of other highly salient or active nodes
Values are additive but capped at 1.0
Salience decays when:
-0.1 — no reference or update in 14 days
-0.05 — no connection to any other salient nodes
Decay can be run as background process or on access.
Relational logic for structural salience:
If a node is structurally important in the graph (many links, especially to high-confidence beliefs), it should gain passive salience.
Rules:
Count directly connected nodes (1-hop)
If 3 or more of them have confidence > 0.75, apply a passive salience boost of +0.15
If node is within 2 hops of any active node, apply +0.1
Use of salience:
Belief ranking in recall and summarization
Contradiction detection priority
Reinforcement signal for belief updates
Optional: affect tone of expression (more salient = more assertive)
Field structure:
Include salience (float), last_updated (timestamp), and connectivity in each belief object.
Salience should be updated during belief access, during graph mutation, and through decay pass.