<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Yes I want what youre saying in 3

To auto-fill gaps using your codegen pack, use a fixed pipeline per meta file.

## Phase 1: Discover and classify meta files

Your pack scans the repo and builds a list:

- `**/README.meta.yaml` → generates/updates `README.md` in same directory.
- `tests/strategy.meta.yaml` → generates/updates `tests/strategy.md`.
- `tests/unit/meta.yaml` → governs `tests/unit/`.
- `tests/integration/meta.yaml` → governs `tests/integration/`.
- `tests/e2e/meta.yaml` → governs `tests/e2e/`.
- `**/tests.meta.yaml` under code folders (e.g. `l9/core/agents/tests.meta.yaml`) → governs tests for that subsystem.[^1]


## Phase 2: Build a “gap report” from each meta

For each `*.meta.yaml`, your pack:

- Parses fields like `location`, `type`, and any explicit `file` or `must_cover` entries.[^1]
- Checks the filesystem for referenced outputs:
    - Docs: `location` file and any per-section READMEs.
    - Tests: `file` paths in unit/integration/e2e sections.
- Produces a machine-readable GAP list, e.g.:

```yaml
gaps:
  - kind: "missing_doc"
    meta: "l9/core/agents/README.meta.yaml"
    target: "l9/core/agents/README.md"
  - kind: "missing_test_file"
    meta: "l9/core/agents/tests.meta.yaml"
    target: "tests/unit/test_agents_engine.py"
    required_behaviors:
      - "AgentExecutorService basic happy path."
      - "Handling of tasks with no tools."
```

This gap list is the single input your AI codegen step needs.

## Phase 3: Codegen for docs from meta

For each `missing_doc` gap:

- Inputs to the pack:
    - The `*.meta.yaml`.
    - The code under that directory (for context).
- Behavior:
    - If `README.md` is missing: generate a full README using meta fields (`name`, `purpose`, `key_components`, etc.).
    - If it exists: update sections that correspond to meta keys while preserving local edits (e.g. regenerate “Overview” and “Key components” blocks, leave custom notes).
- Output:
    - Concrete `README.md` in the target directory, consistent across the repo.


## Phase 4: Codegen for unit/integration/e2e tests from meta

For each `missing_test_file` or “incomplete coverage” gap:

- Inputs:
    - The relevant tests meta (`tests/unit/meta.yaml`, `tests/integration/meta.yaml`, or `subsystem/tests.meta.yaml`).
    - The target module(s) specified in `must_cover`.
- Behavior:
    - Generate a new `test_*.py` with:
        - Imports for the real module and types.
        - Test functions that directly exercise each `must_cover` behavior.
    - If the file exists, add new test functions for **missing** behaviors instead of rewriting the file.

Example pattern from `tests.meta.yaml`:

```yaml
- path: "l9/core/agents/engine.py"
  file: "tests/unit/test_agents_engine.py"
  must_cover:
    - "AgentExecutorService basic happy path."
    - "Handling of tasks with no tools."
```

Your codegen translates each `must_cover` string into 1–N concrete tests in that file.

## Phase 5: Loop with CI to enforce

Once generation runs:

- CI executes:
    - Meta compliance check (no remaining “missing_*” gaps).
    - `pytest` + lint + type checks.
- If anything fails, the gap report is updated and you rerun the pack; because behavior is driven by meta, it’s repeatable and consistent across repos.[^1]

If you want, next step can be drafting the exact YAML shape for the “gap report” your pack will consume, so you can hook it into your existing GMP/phase workflow.

<div align="center">⁂</div>

[^1]: https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_28a5acba-b23e-4b01-9740-de9323d1c6c6/c3ad8924-7fa9-4b7f-afea-1b63dc9e1b8e/can-u-act-as-a-tutor-and-expla-kGNhGCDyQDWqsE9k2ujtjw.md

