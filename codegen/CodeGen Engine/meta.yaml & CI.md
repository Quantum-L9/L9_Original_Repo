<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# What other meta.yaml’s should I have and use both in ci and in codegen that is compatible with packs like this

You already have two powerful “meta” layers: the **canonical schema** and the **L9 glue**. Additional meta YAMLs should sit beside them and do three things: declare contracts, drive CI, and feed your extractor/codegen packs.[^1][^2]

Here are the most useful ones to add.

## Repo-level contracts

These describe the repo as a whole, similar in spirit to `l9_repo_contract` in your glue.[^2]

```yaml
# .l9_repo.meta.yaml
type: "l9_repo_contract"  # High-level repo contract for CI + codegen

root_package: "l9"  # Actual Python package root for this repo

paths:
  core: "l9/core"
  agents: "l9/agents"
  memory: "l9/memory"
  tools: "l9/tools"
  tests: "tests"
  docs: "docs"

naming:
  test_module_pattern: "test_*.py"  # For CI/test discovery
  package_init_required: true       # Enforce __init__.py presence

ci_contracts:
  require_meta_docs: true           # CI must enforce README.meta.yaml presence
  require_meta_tests: true          # CI must enforce tests.meta.yaml presence
  min_unit_coverage: 0.8
  min_integration_coverage: 0.5
```

- **CI use:** Your `ci_meta_check_and_tests.py` can read this and know where to look for docs/tests, and what coverage thresholds to enforce.[^3]
- **Codegen use:** Packs know which root package and directories to target when creating new modules/tests.


## Per-agent/module meta (schema instances)

These are **instances** of `Canonical-Schema-Template-v6.0.yaml` for each agent or domain module, not new types.[^1]

Example:

```yaml
# l9/agents/emma/Emma_v6.schema.yaml
$schema: "L9.CanonicalSchema.v6"
system: L9
module: cognitive_agent
name: emma
role: "Executive Cognitive Node for MortgageOS"
root_path: "l9/agents/emma/"

cursor_instructions:
  create_if_missing:
    - "l9/agents/emma/"
    - "logs/"
    - "manifests/"
  generate_all_required: true
  auto_integrate: true
  generate_files:
    - "cognitive_kernel.py"
    - "agent_controller.py"
    - "memory_bridge.py"
  generate_docs:
    - "l9/agents/emma/README.md"
    - "l9/agents/emma/CONFIG.md"
  logging:
    - "logs/emma_cognition.log"
  post_generation:
    manifest: "manifests/emma_v6_manifest.json"
```

- **CI use:** Optional; you can assert each schema has a valid `root_path` and at least one `generate_files` entry.
- **Codegen use:** Your Universal Schema Extractor + Glue already expect this; packs can read this to generate code, docs, logs, and manifests deterministically.[^2]


## Per-subsystem test meta (you already have the shape)

You already have a good pattern (`subsystem_test_spec`); standardize it per major subsystem.[^3][^2]

```yaml
# l9/core/agents/tests.meta.yaml
type: "subsystem_test_spec"

subsystem:
  name: "Agents Core"
  code_paths:
    - "l9/core/agents/"

unit_tests:
  modules:
    - path: "l9/core/agents/engine.py"
      file: "tests/unit/test_agents_engine.py"
      must_cover:
        - "AgentExecutorService basic happy path."
        - "Tool failure handling."

integration_tests:
  flows:
    - id: "agent_uses_memory"
      file: "tests/integration/test_agent_memory.py"
      description: "Agent run with real memory substrate."
```

- **CI use:** Check that referenced test files exist; optionally verify minimal content (e.g. at least one test function).[^3]
- **Codegen use:** When `meta-gaps.yaml` says a test file is missing, packs read this to create the correct `test_*.py` with required behaviors.


## Per-subsystem docs meta (parallel to tests.meta)

Mirror `tests.meta.yaml` with `docs.meta.yaml` so codegen knows exactly which docs to maintain.

```yaml
# l9/core/agents/docs.meta.yaml
type: "subsystem_docs_spec"

subsystem:
  name: "Agents Core"
  code_paths:
    - "l9/core/agents/"

docs:
  - path: "l9/core/agents/README.md"
    source: "l9/core/agents/README.meta.yaml"  # The structure contract
    required_sections:
      - "Subsystem overview"
      - "Responsibilities and boundaries"
      - "Key components"
      - "Working with AI on this subsystem"
```

- **CI use:** Require the `README.md` to exist; optionally check for required section headings.
- **Codegen use:** Packs read `README.meta.yaml` + `docs.meta.yaml` to regenerate sections safely.


## CI/codegen meta for schema extraction

Slotting into your existing extractor stack:[^4][^2]

```yaml
# .l9_schema_extraction.meta.yaml
type: "schema_extraction_contract"

canonical_schema_template: "Canonical-Schema-Template-v6.0.yaml"
glue_contract: "L9_Universal_Schema_Extractor_Glue_v6.yaml"
extractor_prompt: "Universal-Schema-Extractor-v6.0.md"
extractor_runner: "Universal-Extractor-Prompt.md"

targets:
  - name: "emma"
    schema_file: "l9/agents/emma/Emma_v6.schema.yaml"
  - name: "mortgageos_world"
    schema_file: "l9/domains/mortgageos/MortgageOS_WorldModel_v6.yaml"

ci_enforcement:
  require_manifest: true  # e.g. manifests/*_manifest.json must exist
  require_tests: true     # tests under glue.tests_and_validation patterns
```

- **CI use:** Validate that for each target schema:
    - The manifest exists.
    - The tests under `tests_and_validation` glue section exist (like `test_agent_controller.py`).[^2]
- **Codegen use:** Packs know which schemas to feed into the extractor and which glue file to use.


## Where to put them and how CI/codegen uses them

- Repo contract: `.l9_repo.meta.yaml` (root).

```
- Schema instances: under each agent/domain, e.g. `l9/agents/<agent>/<Agent>_v6.schema.yaml`.  
```

- Subsystem tests/docs meta: beside code folders (`l9/core/<subsystem>/tests.meta.yaml`, `docs.meta.yaml`).
- Schema extraction contract: `.l9_schema_extraction.meta.yaml` (root).

Your CI script expands to:

- Load `.l9_repo.meta.yaml` and `.l9_schema_extraction.meta.yaml`.
- Walk all `*tests.meta.yaml` and `*docs.meta.yaml` to build gap list.
- Optionally validate each `*_v6.schema.yaml` has a valid `root_path` and `cursor_instructions`.

Your codegen packs:

- Use `.l9_repo.meta.yaml` to understand layout and naming.
- Use `*_v6.schema.yaml` + `L9_Universal_Schema_Extractor_Glue_v6.yaml` to generate code/docs/tests per agent/module.[^1][^2]
- Use `tests.meta.yaml` / `docs.meta.yaml` to know which files to create or update when CI reports gaps.

If you want, next step can be: a concrete `meta-gaps.yaml` schema that ties directly into these meta files so your Cursor GMP can consume it with zero guessing.
<span style="display:none">[^5][^6]</span>

<div align="center">⁂</div>

[^1]: Canonical-Schema-Template-v6.0.yaml

[^2]: L9_Universal_Schema_Extractor_Glue_v6.yaml

[^3]: https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_28a5acba-b23e-4b01-9740-de9323d1c6c6/c3ad8924-7fa9-4b7f-afea-1b63dc9e1b8e/can-u-act-as-a-tutor-and-expla-kGNhGCDyQDWqsE9k2ujtjw.md

[^4]: https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/0a751a8d-bf09-454f-973e-94a39eec2c17/Universal-Schema-Extractor-v6.0.md

[^5]: https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/0f8a2262-173e-4bc2-aebe-94d592cfc824/Universal-Extractor-Prompt.md

[^6]: https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/3cf12fd9-9cf2-4f93-8e52-8768cd85ffa8/Canonical-Schema-Population-Guide.md

