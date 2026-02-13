Canonical Template 1 — Perplexity Super God Prompt (PSGP)
YOU ARE OPERATING IN UNIVERSAL EXTRACTION MODE FOR THE L9 AGENT SYSTEM.

MODULE
- module_id: {{module_id}}
- module_name: {{module_name}}
- purpose: {{purpose_one_liner}}

MISSION
Generate ONLY the missing code needed to implement this module inside the existing L9 repo.
Reuse existing repo implementations. Minimal surface area. No parallel stacks.

BINDING INPUTS (ASSUME PRESENT IN REPO)
- Existing FastAPI app + routing conventions exist.
- Existing infra/helpers exist and MUST be imported/used when present:
  {{must_import_and_use_list}}
- SQL migrations define schema truth. No invented schema.
- Existing AIOS endpoints exist (/chat, /memory/*). This module must integrate with AIOS (thin wrappers only).

HARD CONSTRAINTS (NO EXCEPTIONS)
1) NO NEW TABLES / NO NEW TABLE NAMES / NO MIGRATIONS
   - Use ONLY existing tables/columns from migrations: {{schema_truth_tables}}
2) NO DUPLICATE STACKS
   - Do NOT create parallel database/models/logger/exceptions/config layers unless explicitly listed as missing in repo.
3) MINIMAL FILE SURFACE AREA
   - Only create/modify files listed under DELIVERABLE.
4) STRICT I/O + SECURITY
   - Validate inputs, sanitize external payloads, fail-closed on auth/signature checks.
5) IDENTITY + GOVERNANCE
   - Must load/inject identity kernel and obey governance rules if present:
     {{identity_kernel_binding}}

REQUIRED BEHAVIOR (END-TO-END)
For each trigger/input defined below:
- Verify/authenticate (if applicable)
- Normalize into internal model (typed)
- Read context from existing memory substrate/services
- Call AIOS (/chat and optionally /memory/embeddings) as specified
- Persist inbound + outbound artifacts into existing substrate tables
- Produce outward side-effect (API response, Slack post, file write, etc.)
- Enforce idempotency/dedupe where applicable

TRIGGERS / INPUTS
{{triggers_block}}

OUTPUTS / SIDE EFFECTS
{{outputs_block}}

DEDUP / IDEMPOTENCY (REQUIRED IF EVENT-DRIVEN)
- Primary key: {{dedupe_primary}}
- Fallback key: {{dedupe_fallback}}
- Behavior on duplicate: {{dedupe_behavior}}

ERROR POLICY (MATRIX)
- invalid_auth_or_signature => {{policy_invalid_auth}}
- upstream_aios_failure     => {{policy_aios_failure}}
- downstream_side_effect_fail (e.g., Slack/API) => {{policy_side_effect_fail}}

NEO4J / EXTERNAL DEPENDENCIES
- Optional; may be stubbed.
- Must never block core flow.

DELIVERABLE (ONLY THESE FILES)
{{deliverable_file_list}}

OUTPUT FORMAT (STRICT)
- Output ONLY the files listed under DELIVERABLE.
- For each file:
  - Start with: ### FILE: path
  - Then full contents in a fenced code block.
- Python: {{python_version}}+, async-first, full type hints, runnable.
- No TODO/pass placeholders in core paths.
- Any ambiguity: choose ONE consistent mapping and document it in code comments.

QUALITY GATES
- Provide unit tests ONLY for: {{tests_scope}}
- No “package scaffold spam” (no requirements/docker/readme unless explicitly required).