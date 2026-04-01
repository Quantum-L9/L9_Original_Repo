Objective:
Upgrade the provided source instructions into one production-grade execution prompt that is stricter, clearer, denser, and more autonomous-agent reliable, with maximum determinism, minimum ambiguity, and direct deployability.

Constraints:
- Work only from the provided source instructions
- Preserve intent; improve execution quality
- Compress aggressively without dropping operational meaning
- Convert all soft guidance into enforceable rules
- Eliminate redundancy, vague wording, optionality, weak verbs, and cosmetic phrasing
- Enforce one execution path only; no branching, no interpretation, no commentary
- Use explicit missing-data markers: `MISSING:<field>`
- Prioritize deterministic behavior, scope control, validation, completeness, and operational precision
- No placeholders, TODOs, pseudocode, fake certainty, speculative features, or hidden assumptions
- Output must be copy-paste ready and deployment-safe

Execution Logic:
1. Read the source instructions end-to-end
2. Extract only outcome-critical directives, constraints, sequencing, and output rules
3. Deduplicate overlapping guidance and keep the strongest canonical version
4. Rewrite vague or advisory language as hard operational rules
5. Order instructions into a strict single-path flow: objective -> constraints -> execution logic -> output requirements
6. Encode validation, failure handling, scope limits, and completeness checks explicitly
7. Remove any phrasing that allows stylistic drift or agent interpretation
8. Emit one final prompt optimized for autonomous execution

Output Requirements:
- Return exactly one prompt snippet
- Length <=1800 characters
- Dense structured prose only
- No explanations, no alternatives, no surrounding commentary
- Must be self-contained, unambiguous, and immediately executable