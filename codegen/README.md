# L9 CodeGen System

Autonomous code generation from YAML specifications.

## Folder Structure

| Folder | Purpose |
|--------|---------|
| `schemas/` | Schema definitions (Module-Spec-v2.4, DORA contract, samples) |
| `templates/` | Code templates (Python, README, glue, prompts) |
| `process/` | Pipeline definitions (phases, validation, dependencies) |
| `docs/` | Usage guides, references, phase documentation |
| `specs/` | YAML specs to be converted to code |
| `scripts/` | Automation scripts (spec generation, validation) |
| `extractions/` | Generated output (gitignored) |

## Quick Start

### Option 1: Manual Spec Definition

1. Define spec using `schemas/Module-Spec-v2.4.yaml`
2. Run: `python -m agents.codegenagent generate specs/my_spec.yaml`
3. Review output in `extractions/`

### Option 2: AI-Generated Spec (NEW)

1. Generate spec from description:
   ```bash
   python scripts/generate_spec.py --topic "slack_webhook_adapter" \
     --description "Receives Slack webhooks, validates signatures, routes to AIOS"
   ```

2. Or from research synthesis:
   ```bash
   python scripts/generate_spec.py --from-synthesis synthesis_result.json \
     --topic "protocol_bridge"
   ```

3. Run codegen on generated spec:
   ```bash
   python -m agents.codegenagent generate specs/slack_webhook_adapter_*.yaml
   ```

### Option 3: Interactive Mode

```bash
python scripts/generate_spec.py --interactive
```

## Key Files

| File | Description |
|------|-------------|
| `schemas/Module-Spec-v2.4.yaml` | Canonical 26-section module spec schema |
| `schemas/dora-contract.yaml` | DORA block enforcement rules |
| `schemas/Module-Prompt-CURSOR-v2.0.yaml` | Cursor-optimized module prompts |
| `process/meta.codegen.schema.yaml` | Pipeline orchestration (phases 0-6) |
| `templates/prompts/Module-Spec-Generator-v1.0.md` | **Perplexity prompt for AI spec generation** |
| `scripts/generate_spec.py` | **Automated spec generation from research** |
| `templates/python/dora-template.py` | Python file template with DORA blocks |
| `templates/python/module-template.py` | Full L9 module template |

## Template Types

### Python Templates (`templates/python/`)
- `dora-template.py` - Minimal template with DORA header/footer/trace blocks
- `module-template.py` - Full L9 module with imports and initialization

### README Templates (`templates/readme/`)
- `root-readme-template.md` - Main repository README template
- `subsystem-template.md` - Subsystem README template
- `ai-super-prompt.md` - AI/Labs research prompt template

### Glue Templates (`templates/glue/`)
- Integration and wiring templates

## Process Flow

See `process/README.md` for detailed pipeline documentation.

```
YAML Spec → Dependency Resolution → Code Generation → Validation → DORA Compliance → File Emission
```

## Research → Code Pipeline

The codegen system integrates with the L9 research pipeline:

```
┌────────────────────────────────────────────────────────────────────┐
│                     RESEARCH → CODE PIPELINE                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  LAYER 1: Deep Workflows (Discovery)                              │
│  docs/Roadmap-Upgrades/Research - Perplexity Deep workflows/      │
│  → 5-stage literature review → gaps, hypotheses                   │
│                          │                                         │
│                          ▼                                         │
│  LAYER 2: Super-Prompt Pack (Fast Synthesis)                      │
│  docs/Roadmap-Upgrades/Research - Perplexity Super-Prompt Pack/   │
│  → 5 parallel variations → consensus, architecture                │
│                          │                                         │
│                          ▼                                         │
│  LAYER 3: Spec Generator (This System)                            │
│  scripts/generate_spec.py + templates/prompts/Module-Spec-*       │
│  → Module-Spec-v2.4 YAML                                          │
│                          │                                         │
│                          ▼                                         │
│  LAYER 4: CodeGen Pipeline (Production Code)                      │
│  agents/codegenagent/ + process/meta.codegen.schema.yaml          │
│  → Python modules, tests, docs (phases 0-6)                       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### End-to-End Example

```bash
# Step 1: Research synthesis (from Super-Prompt Pack output)
# Assumes you have synthesis_result.json from autonomous-research-agent.py

# Step 2: Generate spec from synthesis
python scripts/generate_spec.py \
  --from-synthesis synthesis_result.json \
  --topic "protocol_bridge"

# Step 3: Generate production code
python -m agents.codegenagent generate specs/protocol_bridge_*.yaml

# Step 4: Review output
ls extractions/protocol_bridge_*/
```

## Related Modules

- `agents/codegenagent/` - Python implementation of CodeGenAgent
- `ir_engine/` - Intermediate representation compiler
- `services/symbolic_computation/` - SymPy integration service
- `docs/Roadmap-Upgrades/Research - Perplexity Deep workflows/` - Literature review methodology
- `docs/Roadmap-Upgrades/Research - Perplexity Super-Prompt Pack/` - Fast synthesis with code generation

## Sample Schemas

Located in `schemas/samples/`:
- `simple_agent.yaml` - Basic agent example
- `domain_adapter.yaml` - Domain adapter pattern
- `orchestrator.yaml` - Orchestrator pattern
- `glue_layer.yaml` - Glue layer pattern
- `sympy_schema_v6.yaml` - SymPy service example

## Documentation

See `docs/` for:
- `USAGE_GUIDE.md` - Detailed usage instructions
- `QUICKSTART.md` - Quick start guide
- `INTEGRATION_GUIDE.md` - Integration and deployment
- `sympy-phases/` - SymPy development phase documentation

## GMP v2.0 Prompts

Located in `prompts/gmp-v2/`:
- `GMP-v2.0-Super-Prompt.md` - Main prompt for Perplexity/Claude code generation
- `GMP-v2.0-Quick-Start.md` - 5-phase implementation roadmap
- `README.md` - Usage instructions

**Python implementation:** `core/gmp/` (meta-learning engine, autonomy controller)

See `core/gmp/README.md` for full documentation on L2→L5 autonomy evolution.



