<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# How would CI force cursor to create the readme files and tests automatically?  Using the specific meta yamls?

CI itself can’t “force” Cursor to act, but you can wire them together so CI **fails when meta contracts aren’t met**, and a Cursor GMP/codegen job is the standard way to fix that failure.

Think of it as: meta YAML → CI check → “Cursor job required if failing”.

## 1. CI step: meta compliance check

Add a CI job that reads the `*.meta.yaml` files and verifies required artifacts exist.

- It parses fields like:
    - `location` (expected README/docs path).
    - `file` or `must_cover` entries in `tests.meta.yaml`.
- It fails if:
    - Any `location` file is missing (`README.md`, `docs/*.md`).
    - Any required test file is missing (`tests/unit/test_*.py`, etc.).
    - Optionally, if a file exists but has no tests or no matching section headers.

This job is just a small Python/Node script run in CI; it exits non‑zero on gaps.

## 2. Standard Cursor GMP for “fix meta gaps”

You then define a single, reusable Cursor/GMP prompt that:

- Reads the **gap report** produced by the CI script (e.g. a `meta-gaps.yaml` artifact).
- Reads the corresponding `*.meta.yaml` and target code.
- Generates/updates:
    - Missing `README.md` files.
    - Missing `test_*.py` files.
    - Additional tests for uncovered `must_cover` behaviors.

Because the prompt is fixed and deterministic, it always behaves the same way across repos.

## 3. CI + Cursor flow

Typical flow per PR:

1. **Developer (or AI) pushes changes.**
2. CI runs:
    - Meta compliance job (reads `*.meta.yaml` and fails on missing artifacts).
    - Tests, lint, type-checks.
3. If meta compliance fails:
    - CI uploads `meta-gaps.yaml` as an artifact or comments a summary on the PR.
    - You trigger the standard Cursor job (manually or via automation) with:
        - `meta-gaps.yaml`
        - The repo snapshot
4. Cursor runs the **“fix meta gaps”** GMP:
    - For each gap, use the relevant meta YAML to generate docs/tests.
    - Commit changes back to the branch (or open a PR).
5. CI runs again:
    - If meta gaps are resolved and tests pass, the PR can be merged.

## 4. Why meta YAML is key

The meta YAML gives both the CI script and Cursor:

- Clear expectations (which files must exist, what tests/sections they need).
- A uniform schema the CI script can parse and Cursor can act on.
- A way to keep the process **repeatable**: change the meta, and both CI and Cursor behavior change in lockstep.

So CI doesn’t directly “create” files; it **enforces the contracts from meta YAML** and uses failure as the trigger for your standard Cursor codegen workflow to generate the missing READMEs and tests.
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_28a5acba-b23e-4b01-9740-de9323d1c6c6/c3ad8924-7fa9-4b7f-afea-1b63dc9e1b8e/can-u-act-as-a-tutor-and-expla-kGNhGCDyQDWqsE9k2ujtjw.md

