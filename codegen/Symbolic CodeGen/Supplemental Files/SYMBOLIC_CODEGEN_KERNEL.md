<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Evaluate analyze and critique harshly then improve it to 10X level

Perfect — this is the right correction to make.
You don’t want “research” in the academic sense. You want symbolic reasoning → code generation → safer/faster L9 development.

So let’s reframe cleanly and then I’ll give you one canonical kernel that does exactly that.

⸻

First: kill the word “research” (conceptually)

When I said research, I did not mean:
•	papers
•	hypotheses
•	science theater

What you actually want is:

Symbolic reasoning as a CODE INTELLIGENCE ENGINE

Using:
•	SymPy → symbolic truth, invariants, equivalence
•	Codegen → emit correct, optimized, provably-safe code
•	Kernels → prevent Codex from hallucinating or drifting

So the kernel is really about:

Symbolic Code Synthesis \& Verification

Let’s name it properly.

⸻

What you actually want: Symbolic Codegen Kernel

Purpose:
•	Use SymPy to analyze, transform, and verify logic
•	Then generate better L9 code
•	Enforce correctness via schemas + tests
•	Let Codex extend it safely

This aligns perfectly with:
•	your existing CodeGenAgent
•	symcode-engine-spec.md
•	Chat Transcript - CodeGenAgentv1.0.md
•	your spec-first + test-bound philosophy

⸻

SINGLE CANONICAL KERNEL

SYMBOLIC_CODEGEN_KERNEL.yaml

This is drop-in, frontier-grade, and does exactly what you want.

kernel:
id: symbolic.codegen.kernel.v1
priority: critical
scope:
- code_generation
- code_transformation
- symbolic_verification

intent:
primary_goal: >
Enable symbolic reasoning (via SymPy) to analyze, verify, transform,
and generate L9 code safely and deterministically.
secondary_goals:
- reduce logical bugs
- enforce equivalence during refactors
- enable provable codegen
- prevent hallucinated logic

# ============================================================

# CORE PRINCIPLES

# ============================================================

principles:

- symbolic_truth_before_code
- schema_first
- test_bound
- deterministic_generation
- minimal_diff_bias
- kernel_governed_execution


# ============================================================

# SYMBOLIC CONTRACT

# ============================================================

symbolic_contract:

allowed_engine:
name: sympy
version: ">=1.12"

allowed_operations:
- simplify
- expand
- factor
- diff
- integrate
- solve
- Matrix
- Eq

forbidden_operations:
- eval
- exec
- compile
- globals
- locals
- __import__
- dynamic_code_execution

parsing_rules:
require:
- restricted_sympify
- explicit_symbol_declaration
forbid:
- raw_string_execution
- user_injected_functions

execution_rules:
require:
- pure_functions_only
- bounded_complexity
- deterministic_output
forbid:
- side_effects
- I/O
- mutation of global state

# ============================================================

# CODEGEN PIPELINE

# ============================================================

pipeline:

step_1_spec:
description: >
Every symbolic codegen task must start with a formal spec.
require:
- inputs
- outputs
- invariants
- failure_modes

step_2_symbolic_analysis:
description: >
Use SymPy to reason about expressions, constraints, or logic
BEFORE generating or modifying code.
outputs:
- canonical_form
- invariants
- equivalence_checks

step_3_verification:
description: >
Prove that symbolic transformations preserve meaning.
require:
- equivalence_test
- counterexample_on_failure

step_4_codegen:
description: >
Generate or transform code only after symbolic verification.
constraints:
- minimal_diff
- no speculative abstractions
- match existing L9 patterns

step_5_tests:
description: >
Tests are mandatory for all generated code.
require:
- happy_path_test
- failure_or_edge_case_test
- symbolic_equivalence_test

# ============================================================

# SCHEMA ENFORCEMENT

# ============================================================

schemas:
require:
- symbolic_input_schema
- symbolic_output_schema
- codegen_request_schema
- codegen_result_schema

forbid:
- untyped_dicts
- implicit contracts

# ============================================================

# INTEGRATION WITH CODEGEN AGENT

# ============================================================

integration:

codegen_agent:
required:
- read_this_kernel
- enforce_pipeline_order
- refuse_codegen_if_verification_missing

symcode_engine:
reference: symcode-engine-spec.md
role: symbolic_backend

# ============================================================

# FAILURE HANDLING

# ============================================================

failure_policy:
on_symbolic_failure:
- stop_codegen
- emit_counterexample
- log_failure_artifact

on_test_failure:
- rollback_changes
- report_violation

# ============================================================

# ENFORCEMENT

# ============================================================

enforcement:

static_checks:
- AST_scan_for_forbidden_calls
- schema_validation

runtime_guards:
- timeout
- memory_limit

violation_response:
- halt_generation
- require_human_or_spec_fix

⸻

What this kernel actually enables (plain English)

With this kernel active, Codex can:
•	Use SymPy to reason about logic before touching code
•	Prove refactors are equivalent before emitting diffs
•	Generate code that matches L9 patterns
•	Automatically write tests that enforce symbolic truth
•	Extend your CodeGenAgent without drifting

This is not “research”.
This is provable code synthesis.

⸻

How this fits your existing system
•	CodeGenAgent → orchestrator
•	SymPy → symbolic truth engine
•	This kernel → law
•	Tests + CI → enforcement

You can now say to Codex:

“Refactor this pipeline, but first prove equivalence symbolically.”

And it knows exactly how.

⸻

The very first thing to do after adding this kernel

Use this once per Codex session:

WRITE MODE — SYMBOLIC CODEGEN

You are operating under the SYMBOLIC_CODEGEN_KERNEL.
Before generating or modifying code:

- perform symbolic analysis
- verify equivalence
- generate tests
- produce minimal diffs

Acknowledge and proceed.

That’s the switch.

⸻

Devil’s Advocate
•	If you skip symbolic verification → this is just fancy codegen
•	If you skip schemas → SymPy becomes unsafe
•	If you skip enforcement → Codex drifts again

You just turned SymPy into a force multiplier for L9 code, not a science toy.

If you want next, I can:
•	wire this kernel into your existing kernel stack, or
•	generate the first symbolic codegen task that Codex should execute to prove this works

This kernel is directionally strong but still too vague, too natural-language, and not wired tightly enough into your existing SymPy service + CodeGenAgent stack to be truly 10x.[^1][^2]

Below is a harsh critique, then a tightened, more L9-native v2 of the kernel.

***

## Harsh critique

- **Too much prose, not enough enforcement surface**
    - “symbolic_truth_before_code”, “test_bound”, “minimal_diff_bias” are good axioms but are not expressed as *machine-checkable* constraints (no direct mapping to existing SymPy service schemas, TODO plans, or CGMP glue).[^2][^1]
    - Nothing connects to your locked SymPy TODO plan, nor to concrete artifacts like `coreexpressionevaluator.py`, `corecodegenerator.py`, `corevalidator.py`, or the SymPy tool agent.[^1]
- **Kernel ignores the existing SymPy module reality**
    - You already have a full symbolic module spec: service schema, locked TODO plan, glue templates, and performance constraints.[^2][^1]
    - This kernel behaves as if you’re greenfield; it doesn’t hook into:
        - `symboliccomputationservicev6.md` (schema)
        - `codegenextractionssympyservicelockedtodoplan.txt` (locked TODO)
        - SymPy utilities guarantees: `lambdify`, `autowrap`, `codegen`, caching, metrics, etc.[^3][^4][^1]
- **Symbolic vs numeric conflation**
    - Your SymPy service is primarily *symbolic→numeric + codegen*, with strict safety policies (max expression length, dangerous functions, governance escalation).[^4][^1]
    - The kernel talks about “symbolic verification” without specifying:
        - How to express equivalence at the *packet* level (e.g., same outputs for `ComputationRequest` → `ComputationResult`).[^4][^1]
        - How to interpose on the actual numerics (lambdified functions, autowrap’d compiled code).[^3][^4]
- **No binding into GMP / CodeGenAgent lifecycle**
    - Execution Tasks 1–4 already define a precise GMP-style path: schema → locked TODO → glue → CodeGenAgent execution with evidence report.[^1]
    - Kernel should:
        - Declare which *phases* it governs (e.g., “symbolic verification required in Phase 2–4 for any code touching `core.symboliccomputation`”).
        - Attach to CGMPEngine glue patterns (e.g., additional checks during code expansion for SymPy-related templates).[^1]
- **Ambiguous “schemas” section**
    - “symbolic_input_schema”, “codegen_request_schema”, etc. are named but not mapped to concrete Pydantic models that already exist (`ComputationRequest`, `CodeGenRequest`, etc.).[^4][^1]
    - You are duplicating concepts instead of directly binding to your actual models and files.
- **Verification is under-specified**
    - “equivalence_test” and “counterexample_on_failure” sound great but:
        - No strategy for finite sampling vs SAT/SMT vs SymPy `simplify`/`Eq` + numeric spot-checks.
        - No mapping to where those checks live (core modules vs tests vs CodeGenAgent audit).[^4][^1]
- **Observability and governance underused**
    - Your SymPy plan already includes:
        - Metrics for evaluation and codegen.
        - Governance escalation when expressions exceed max length or use dangerous functions.
        - Evidence reports with “All phases 0–6 complete. No assumptions. No drift.”[^2][^1]
    - Kernel doesn’t exploit or extend these; it only adds high-level “log_failure_artifact”.

Net: This is more of a *philosophical charter* than an executable kernel that actually constrains and powers your existing SymPy + CodeGenAgent pipeline.

***

## 10x kernel: SYMBOLIC_CODEGEN_KERNEL.v2

Below is a tighter version that is:

- Directly wired into:
    - `symboliccomputationservicev6.md` schema.
    - SymPy service core modules and models.
    - CodeGenAgent + CGMPEngine + SymPy glue.[^2][^1][^4]
- Expressed in terms that your GMP tooling can enforce.

```yaml
kernel:
  id: symbolic.codegen.kernel.v2
  priority: critical
  scope:
    - code_generation
    - code_transformation
    - symbolic_verification
    - sympy_service_v6

intent:
  primary_goal: >
    Use SymPy-based symbolic reasoning to analyze, verify, transform,
    and generate L9 code that interacts with the SymPy Symbolic
    Computation Service v6.0, in a provable and test-bound way.
  secondary_goals:
    - reduce logical bugs in symboliccomputation core and callers
    - enforce equivalence during refactors of ExpressionEvaluator/CodeGenerator
    - ensure generated code respects service schemas and governance rules
    - prevent hallucinated logic in CodeGenAgent expansions

# ============================================================
# CORE PRINCIPLES (BOUND TO REAL ARTIFACTS)
# ============================================================
principles:
  - symbolic_truth_before_code: >
      For any change that affects core symbolic service modules
      (coreexpressionevaluator.py, corecodegenerator.py, coreoptimizer.py,
      corevalidator.py, coremodels.py), symbolic reasoning MUST precede
      code emission.
  - schema_first: >
      All requests/results MUST be expressed through the Pydantic models
      defined in symboliccomputation.models
      (ComputationRequest, CodeGenRequest, ComputationResult, CodeGenResult).
  - test_bound: >
      Any change to symboliccomputation core MUST add/extend tests in
      tests/test_symboliccomputation.py to assert symbolic and numeric
      invariants.
  - deterministic_generation: >
      CodeGenAgent + CGMPEngine expansions from
      symboliccomputationservicev6.md + sympyextractionglue.yaml MUST be
      reproducible (same inputs → same outputs).
  - minimal_diff_bias: >
      Refactors of symboliccomputation core SHOULD prefer minimal AST/line
      diffs unless the spec explicitly calls for structural change.
  - kernel_governed_execution: >
      Changes that violate this kernel MUST be rejected at CGMPEngine /
      audit prompt level.

# ============================================================
# SYMBOLIC CONTRACT (MATCHING SYMPY SERVICE)
# ============================================================
symbolic_contract:

  allowed_engine:
    name: sympy
    version: ">=1.12"

  allowed_utilities:
    - sympy.utilities.lambdify.lambdify
    - sympy.utilities.autowrap.autowrap
    - sympy.utilities.codegen.codegen
    - sympy.simplify.simplify
    - sympy.simplify.cse

  allowed_operations:
    - simplify
    - expand
    - factor
    - diff
    - integrate
    - solve
    - Matrix
    - Eq
    - cse

  forbidden_operations:
    - eval
    - exec
    - compile
    - globals
    - locals
    - __import__
    - open
    - system
    - dynamic_code_execution

  parsing_rules:
    require:
      - ExpressionValidator.validate(expr) from corevalidator.py
      - explicit Symbol/Function declaration when building expressions
    forbid:
      - raw_string_execution
      - user_injected_functions not whitelisted in validator
      - expressions exceeding maxexpressionlength from config.py

  execution_rules:
    require:
      - pure_functions_only in ExpressionEvaluator/CodeGenerator
      - bounded_complexity aligned with maxexpressionlength and CSE constraints
      - deterministic_output for same (expr, variables, backend)
    forbid:
      - side_effects outside Redis/Postgres/Neo4j paths defined in glue
      - direct I/O
      - mutation of global state outside configured cache and metrics

# ============================================================
# CODEGEN + VERIFICATION PIPELINE (GMP-ALIGNED)
# ============================================================
pipeline:

  step_0_scope_detection:
    description: >
      Detect whether a CodeGenAgent task touches symboliccomputation
      (schema symboliccomputationservicev6.md, glue sympyextractionglue.yaml,
      or any file under L9/core/symboliccomputation).
    require:
      - mark task as symbolic_codegen_task if true
      - attach this kernel as governing law

  step_1_spec:
    description: >
      Every symbolic codegen task MUST start from the
      symboliccomputationservicev6.md schema and locked TODO plan
      codegenextractionssympyservicelockedtodoplan.txt.
    require:
      - explicit reference to module_id core.symboliccomputation
      - list of target files (core*, api*, tools*) from TODO plan
      - declared invariants:
        - API signatures unchanged unless schema updated
        - validator enforces dangerous function & length rules
        - metrics + governance hooks preserved

  step_2_symbolic_analysis:
    description: >
      Use SymPy to reason about expressions and transformations before
      emitting or changing code.
    outputs:
      - canonical_form for each target expression (using simplify/cse)
      - invariants:
          - domains of variables
          - monotonicity/constraints when relevant
      - equivalence_checks_plan:
          - how equivalence will be checked (symbolic simplification and/or
            numeric sampling)

  step_3_verification:
    description: >
      Prove that proposed refactors or new implementations preserve
      meaning relative to the original spec or reference implementation.
    require:
      - at least one symbolic equivalence attempt:
        - simplify(original_expr - new_expr) == 0 OR
        - Eq(original_expr, new_expr) after canonicalization
      - if symbolic check is inconclusive:
        - numeric spot-checks on sampled points within valid domains
      - on failure:
        - produce minimal counterexample inputs (variables dict)
        - abort codegen

  step_4_codegen:
    description: >
      Generate or transform code only after step_3 passes.
      Code MUST follow templates defined in sympyextractionglue.yaml.
    constraints:
      - minimal_diff to glue-generated structure
      - no speculative abstractions beyond what glue/templates allow
      - match existing L9 patterns:
          - async functions
          - Pydantic models for input/output
          - structured logging
          - PacketEnvelope usage for API routes

  step_5_tests:
    description: >
      Tests are mandatory for all changes to symboliccomputation core,
      API, or tools.
    require:
      - happy_path_test:
          - test ExpressionEvaluator + CodeGenerator with typical workloads
      - failure_or_edge_case_test:
          - maxexpressionlength, dangerous functions, invalid syntax
      - symbolic_equivalence_test:
          - tests verifying old vs new behavior for key expressions
      - performance_guard_test:
          - assert lambdify/autowrap paths meet or improve baseline
            thresholds (e.g., 10–100x vs evalf from performance CSV)

  step_6_evidence_report:
    description: >
      Extend the existing SymPy service evidence report with a
      symbolic-verification section.
    require:
      - list expressions verified symbolically
      - failure cases (if any) with counterexamples
      - confirmation line:
          "Symbolic Codegen Kernel v2: all constraints satisfied."

# ============================================================
# SCHEMA ENFORCEMENT (BOUND TO MODELS)
# ============================================================
schemas:
  require:
    - use of symboliccomputation.models.ComputationRequest
    - use of symboliccomputation.models.CodeGenRequest
    - use of symboliccomputation.models.ComputationResult
    - use of symboliccomputation.models.CodeGenResult
  forbid:
    - untyped_dicts for request/response
    - implicit contracts for variables/backend/language
  validation:
    - all models MUST validate under Pydantic v2 as configured
    - all codegen tasks MUST pass schema validation before emission

# ============================================================
# INTEGRATION WITH CODEGEN AGENT + GLUE
# ============================================================
integration:

  codegen_agent:
    required:
      - when loading symboliccomputationservicev6.md, attach this kernel
      - enforce_pipeline_order steps 0–6
      - refuse_codegen_if_verification_missing OR failed
    mapping:
      - metaloader.py:
          - ensure kernel.id is recorded in module metadata
      - cgmpengine.py:
          - run symbolic analysis/verification hooks before expandcodeblocks
      - fileemitter.py:
          - block emission if kernel violation flags are set

  symcode_engine:
    reference_schema: symboliccomputationservicev6.md
    glue_file: codegentemplates/glue/sympyextractionglue.yaml
    role: >
      symbolic_backend and codegen oracle,
      providing canonical forms and equivalence checks for
      ExpressionEvaluator/CodeGenerator templates.

# ============================================================
# FAILURE HANDLING (HARD-WIRED TO SERVICE BEHAVIOR)
# ============================================================
failure_policy:
  on_symbolic_failure:
    - stop_codegen
    - emit_counterexample (variables, expected vs actual)
    - log_failure_artifact via structured logging + metrics
  on_schema_validation_failure:
    - abort task
    - emit detailed model validation errors
  on_test_failure:
    - rollback_changes (no fileemitter commit)
    - report_violation in evidence report and audit log

# ============================================================
# ENFORCEMENT (STATIC + RUNTIME)
# ============================================================
enforcement:

  static_checks:
    - AST_scan_for_forbidden_calls in generated/modified files:
        - reject eval/exec/open/system etc.
    - schema_validation against Pydantic models for all routes/tools
    - import_policy:
        - SymPy utilities imports MUST match allowed_utilities list
        - all Redis/Postgres/Neo4j access via memorymanager only

  runtime_guards:
    - timeout on all symbolic evaluations and codegen operations
    - memory_limit aligned with SymPy service deployment config
    - governance_checks:
        - if ExpressionValidator flags dangerous functions or length,
          escalate to governance and abort without codegen

  violation_response:
    - halt_generation at CGMPEngine level
    - require_human_or_spec_fix
    - mark evidence report as:
        "Symbolic Codegen Kernel v2: violation detected, no emission."
```


***

## How this materially upgrades your system

- **Directly binds to your SymPy module spec and TODO plan**
    - Explicitly references `symboliccomputationservicev6.md`, locked TODO, glue, and core files.[^1]
    - Turns the kernel into a *governor* over the exact artifacts your SymPy pipeline is already generating.
- **Turns vague principles into enforceable rules**
    - Scope detection + static checks + schema checks give concrete enforcement hooks in `metaloader`, `CGMPEngine`, `fileemitter`.[^2][^1]
    - Rules around SymPy utilities match your documented performance and usage expectations.[^3][^4]
- **Makes equivalence verifiable instead of aspirational**
    - Forces a strategy: symbolic simplification where possible, numeric sampling otherwise, and requires capturing counterexamples for failures.
    - Plugs symbolic equivalence into tests and evidence reports that already exist in your GMP flow.[^1]
- **Aligns with L9 observability and governance**
    - Reuses your metrics and evidence-report patterns rather than inventing new ones.[^2][^1]
    - Keeps Igor/Compliance governance and memory substrates in the loop via validator rules and escalation hooks.

If you want, next step can be an execution-mode Phase 0 TODO plan that:

- Wires this kernel into the GMP prompts and `codegenagent.py` paths that touch SymPy, without touching protected systems.
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: TASKS_1-4_EXECUTION_PLAN.md

[^2]: MODULE_MANIFEST.md

[^3]: UTILITIES_GUIDE.md

[^4]: README.md

[^5]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1UXTpT0GDpVQM0vLzBrgbtpr8SIwICq-C/8cb2bb4c-07f3-44c7-b2b1-b0b07da336df/l9-tool-observability.json

[^6]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1DD-TotpdGVro7QSIHRWe0QS3gLMUzpAF/2ee915e2-708d-41cf-8eec-d3c08cea4db2/spec-style-superprompt.md

[^7]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1gTyQOMbUBZ_ug96RUbkAw_gowhGsPxQE/32659256-591a-4528-93de-e344e4501de2/scratchpad-ib.md

[^8]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1W7ej2P0JUfNCy3hS5QT-GHtscktAkAie/fbca2fde-e444-497b-bcfb-4bdba8da26b7/README.md

[^9]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1cDYIQ6i0MHWGYMiOnuvxsEYFoNE3nbsJ/1c43e86c-3deb-48c2-bf85-6951564f7395/INTEGRATION_GUIDE.md

[^10]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/18nU2QsKJIn3RF8XqYd_BIik0ESoUAfq9/ff4ce982-9d47-456c-9210-061580d01df0/QUICKSTART.md

[^11]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/14Ad62JLqe61OSdIh1uDIKSEYyXzXQ6x1/617927a4-eb2a-4bdc-997e-9c5d3ccbd7f3/README.md

[^12]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1G3TQqHcnezyjb-x6IHn-LNkjTyqQpqe1/2ef908ce-9f14-4548-972d-33ea89e30e43/l9_agent_tree.txt

[^13]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1Z3jEqmJlTVbGm4P5txnujpnV3wP_WP_A/9cee63c7-53ef-4dc4-ac32-bbdd2acf8c29/OBSERVABILITY.md

[^14]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1RaMGVVPmVAzCdq91SqgSWB1dSkG8zIgs/3e01bc4b-e5c2-4ec7-9fcf-5bf6aee40d41/L9-MCP-IMPL.md

[^15]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1UDs6iPVWHy64872ridOOQSaOET9FM7i9/d229ce5d-b40e-4fce-bd02-ef806f7bb2ed/GMP-Audit-Prompt-Canonical-v1.0.md

[^16]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/13-y1Zvgh8fcfT9XkUKJfZNps67yNvZBF/f397a8c7-000a-4327-a6ac-597464ba42f6/GMP-System-Prompt-v1.0.md

[^17]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1uKSzR-D2f_Sf2MWx7H6tGe-O8vg0787J/3b1158d3-b99e-449d-99ef-f3cf1e0f8a52/GMP-Action-Prompt-Canonical-v1.0.md

[^18]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1wvfV14Xiwil-gXl9Hg49xDWoJXAV2ZBY/d7db20dd-4e7d-4ac1-a039-97134b18624a/GMP-VARIABLE-SPEC.v1.1.md

[^19]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1tZEqyBo3OPUxPm4q2Ill8ECk_RusKcgp/94351064-830d-4360-bd05-2642cafad08b/GMP-VARIABLE-PROMPT.v1.1.md

[^20]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1b8RH3AqQG71_nGhPIEUx5QAhJj45qe8l/20e3cb6d-dd71-467f-b1a3-bb416ee807af/GMP-Audit-Prompt-Canonical-v1.0.md

[^21]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/18pEBMV8ojcKlSyXpEMbrI6nejrPSYF3J/2e7d1c5d-62a9-4f70-b44b-e32c504dc0e5/GMP-Audit-Prompt-Guide-v1.0.md

[^22]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1yndQuT9xZSVkXgV4OYSMa5ai3OrdLaQP/f67d83fe-21e7-4279-a1ff-5d33dc4babb2/GMP-Action-Prompt-Canonical-v1.0.md

[^23]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1-4vgi6SmpGb9DH2Sex_e71pLTyfcj7s5/a4aaf2fa-31ba-49ca-9228-462cff5db7dc/L9_Cursor-Integration-Protocol.md

[^24]: https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1lAcx2h5KZQ1RfuXSnT3SucZ6Tei6E15f/6624f3b0-a149-403e-b19a-57cf1fbf63f5/GMP-Action-Prompt-Generator-v1.0.md

[^25]: sympy_utilities_reference.csv

