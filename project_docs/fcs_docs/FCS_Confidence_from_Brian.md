FCS: Confidence Mechanism Specification
Author: Brian
Audience: Joseph (engineering implementation)
What is Confidence:
Confidence is a float between 0.0 and 1.0 that represents how stable, supported, and coherent a Cognitive Object (CO) is—based on both user behavior and relationships within the graph.
Confidence reflects:
Origin type (user-given vs. inferred)
Contradiction history
Reinforcement from other high-confidence COs
Revision frequency
Optional: long-term dormancy
Initial confidence values:
0.8 — User-given CO
0.5 — Inferred from context
0.4 — System-suggested or speculative
Confidence increases when:
+0.1 — User reaffirms CO
+0.1 — Supported by another CO with confidence > 0.75
+0.05 — Referenced during reasoning or summarization
+0.05 — Connected to ≥3 COs with confidence > 0.7
Confidence decreases when:
-0.3 — Contradicted by a CO with confidence > 0.7
-0.1 — User revises or weakens the CO
-0.05 — Not referenced for >30 days (optional)
-0.15 — Repeated contradiction without resolution
Values are additive but capped between 0.0 and 1.0.
How confidence is used:
In contradiction arbitration: choose the CO with higher confidence if unresolved
In expression: lower-confidence COs are described more tentatively
In mutation: flag COs with confidence < 0.4 as unstable
Optional: suppress COs < 0.2 from normal recall unless explicitly requested
CO object structure should include:
confidence (float)
last_updated (timestamp)
revisions (int)
supporting_CO_ids (array, with confidence annotations)
contradicting_CO_ids (array, with confidence annotations)
Confidence should be updated:
On CO creation
On contradiction, reinforcement, revision, or confirmation
Optionally via a scheduled re-evaluation process