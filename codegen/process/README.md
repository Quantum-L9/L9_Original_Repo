# CodeGen Process Pipeline

This folder contains the YAML definitions that orchestrate the code generation pipeline.

## Files

| File | Purpose |
|------|---------|
| `meta.codegen.schema.yaml` | **Master schema** - Source of truth for codegen, defines 6-phase extraction process |
| `meta.extraction.sequence.yaml` | **Ordering algorithm** - Dependency resolution and extraction ordering |
| `meta.validation.checklist.yaml` | **Quality gates** - Production-grade validation applied to every extracted agent |
| `meta.dependency.integration.yaml` | **Integration map** - Cross-module dependency wiring |

## Pipeline Flow

```
1. Load spec (Module-Spec-v2.4 format)
       ↓
2. Resolve dependencies (meta.extraction.sequence.yaml)
       ↓
3. Generate code (meta.codegen.schema.yaml phases 1-6)
       ↓
4. Validate output (meta.validation.checklist.yaml)
       ↓
5. Wire integrations (meta.dependency.integration.yaml)
       ↓
6. Emit files with DORA compliance
```

## Usage

These YAMLs are consumed by the CodeGenAgent (`agents/codegenagent/`) and IR Engine (`ir_engine/`).

They are not executed directly - they define the process that code follows.

## Related

- `codegen/schemas/` - Schema definitions (Module-Spec, DORA contract)
- `codegen/templates/` - Output templates (Python, README)
- `codegen/docs/` - Usage guides and references




