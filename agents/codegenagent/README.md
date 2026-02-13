# CodeGenAgent

Central orchestrator for L9's meta-driven code generation pipeline.

## Overview

CodeGenAgent transforms YAML specifications into executable Python modules through a phased pipeline:

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐    ┌─────────────┐
│ MetaLoader  │───▶│ IR Compiler  │───▶│ Py Compiler   │───▶│ FileEmitter │
└─────────────┘    └──────────────┘    └───────────────┘    └─────────────┘
       │                                                            │
       ▼                                                            ▼
┌─────────────────┐                                    ┌────────────────────┐
│ PipelineValidator│                                   │   RollbackHook     │
└─────────────────┘                                    └────────────────────┘
       │                                                            │
       ▼                                                            ▼
┌─────────────────┐                                    ┌────────────────────┐
│ComplianceAuditor│                                    │ CodeGenTelemetry   │
└─────────────────┘                                    └────────────────────┘
       │
       ▼
┌─────────────────────────┐
│ CursorContextSyncEngine │
└─────────────────────────┘
```

## Modules

| Module | Purpose |
|--------|---------|
| `codegen_agent.py` | Main orchestrator (679 lines) |
| `meta_loader.py` | YAML loading and validation (337 lines) |
| `file_emitter.py` | File writing with rollback support (456 lines) |
| `c_gmp_engine.py` | Code expansion with SymPy (443 lines) |
| `ap_generator.py` | GMP prompt generation |
| `compliance_auditor.py` | Governance compliance checking |
| `pipeline_validator.py` | Meta specification validation |
| `telemetry_codegen.py` | Generation metrics and telemetry |
| `rollback_hook.py` | Snapshot and reversion support |
| `cursor_sync.py` | Simplified Cursor context sync |
| `cursor_context_sync_engine.py` | Full bi-directional sync |

## Quick Start

### Generate from YAML Spec

```python
from agents.codegenagent.codegen_agent import CodeGenAgent

agent = CodeGenAgent()

# Generate from a single spec
result = await agent.generate_from_meta("path/to/spec.yaml")

if result.success:
    print(f"Generated {len(result.files_created)} files")
else:
    print(f"Errors: {result.errors}")
```

### Preview (Dry Run)

```python
# Preview without writing files
preview = await agent.preview("path/to/spec.yaml")

print(f"Would create {preview.would_create} files")
print(f"Would modify {preview.would_modify} files")
print(f"Generated code preview:")
for path, code in preview.generated_code.items():
    print(f"  {path}: {len(code)} chars")
```

### Batch Generation

```python
# Generate from all specs in a directory
result = await agent.generate_batch(
    pattern="*.yaml",
    directory="codegen/specs/",
    dry_run=False,
    stop_on_error=True,
)

print(f"Generated {result.successful} of {result.total_specs}")
```

### Validate Spec

```python
# Validate without generating
validation = agent.validate_spec("path/to/spec.yaml")

if validation.valid:
    print("Spec is valid")
else:
    for error in validation.errors:
        print(f"  - {error}")
```

## API Reference

### CodeGenAgent

```python
class CodeGenAgent:
    def __init__(
        self,
        repo_root: str = "/Users/ib-mac/Projects/L9",
        specs_dir: Optional[str] = None,
        strict_validation: bool = False,
    )
    
    async def generate_from_meta(
        self,
        meta_path: str,
        dry_run: bool = False,
    ) -> GenerationResult
    
    async def generate_from_contract(
        self,
        contract: MetaContract,
        dry_run: bool = False,
    ) -> GenerationResult
    
    async def preview(self, meta_path: str) -> DryRunResult
    
    async def generate_batch(
        self,
        pattern: str = "*.yaml",
        directory: Optional[str] = None,
        dry_run: bool = False,
        stop_on_error: bool = False,
    ) -> BatchResult
    
    def validate_spec(self, meta_path: str) -> MetaContractValidationResult
    
    def list_available_specs(
        self,
        pattern: str = "*.yaml",
        format_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]
```

### Result Types

```python
@dataclass
class GenerationResult:
    success: bool
    module_id: str
    source_path: str
    files_created: List[str]
    files_modified: List[str]
    ir: Optional[ModuleIR]
    generated_code: Dict[str, str]
    errors: List[str]
    warnings: List[str]
    duration_ms: Optional[float]

@dataclass
class DryRunResult:
    module_id: str
    source_path: str
    new_files: List[Dict[str, Any]]
    modified_files: List[Dict[str, Any]]
    directories_to_create: List[str]
    validation_result: Optional[MetaContractValidationResult]
    generated_code: Dict[str, str]

@dataclass
class BatchResult:
    total_specs: int
    successful: int
    failed: int
    skipped: int
    results: List[GenerationResult]
```

## Supported Schema Formats

1. **Module-Spec-v2.4** - Full operational/enterprise grade specs
2. **Research-Factory-v6.0** - Agent/adapter schemas
3. **Glue-Layer-v6** - Integration layer specs

## Configuration

### Feature Flags

```python
L9_ENABLE_SYMBOLIC_PIPELINE=true    # Enable SymPy symbolic verification
L9_ENABLE_STRICT_VALIDATION=false   # Treat warnings as errors
L9_ENABLE_COMPLIANCE_AUDIT=true     # Run compliance checks
L9_ENABLE_TELEMETRY=true            # Emit generation metrics
```

### Environment Variables

```bash
L9_CODEGEN_REPO_ROOT=/path/to/l9
L9_CODEGEN_SPECS_DIR=/path/to/specs
L9_CODEGEN_STRICT=false
```

## Compliance and Governance

CodeGenAgent includes built-in compliance auditing:

```python
from agents.codegenagent.compliance_auditor import ComplianceAuditor

auditor = ComplianceAuditor(strict_mode=True)
result = auditor.audit_compliance(meta, generated_files)

if result.escalation_needed:
    # Escalate to Igor for approval
    print(f"Escalation reasons: {result.escalation_reasons}")
```

### Compliance Checks

- **Policy Zone**: Code includes governance markers
- **Rollback Handler**: Reversion support present
- **Trace Hooks**: Logging and audit trail
- **Memory Recovery**: PacketEnvelope integration
- **Dangerous Patterns**: No exec(), eval(), etc.

## Telemetry

CodeGenAgent emits Prometheus-compatible metrics:

```python
from agents.codegenagent.telemetry_codegen import get_telemetry

telemetry = get_telemetry()
telemetry.start_generation("my_module")

# ... generation ...

telemetry.record_generation(meta, files, success=True)

# Get Prometheus output
print(telemetry.get_prometheus_output())
```

### Metrics

- `codegen_generations_total` - Total generation runs
- `codegen_files_total` - Total files generated
- `codegen_lines_total` - Total lines generated
- `codegen_failures_total` - Total failures
- `codegen_latency_avg_ms` - Average generation latency

## Rollback Support

```python
from agents.codegenagent.rollback_hook import RollbackHook

hook = RollbackHook()

# Before generation
snapshot_id = hook.setup_reversion(files, "my_module")

# If something goes wrong
result = hook.execute_rollback(snapshot_id)

if result.success:
    print(f"Rolled back {result.files_restored} files")
```

## Cursor Integration

CodeGenAgent syncs with Cursor IDE context:

```python
from agents.codegenagent.cursor_sync import sync_with_cursor

# After generation
envelope = sync_with_cursor(meta, output_files)
```

For full bi-directional sync with Redis:

```python
from agents.codegenagent.cursor_context_sync_engine import CursorContextSyncEngine

engine = CursorContextSyncEngine(redis_client=redis)
result = await engine.sync_cursor_context(agent_id, files)
```

## Testing

```bash
# Run all CodeGenAgent tests
pytest tests/agents/codegenagent/ -v

# Run with coverage
pytest tests/agents/codegenagent/ --cov=agents.codegenagent --cov-report=html
```

## Architecture

### Pipeline Flow

1. **MetaLoader**: Parses YAML, detects schema format, validates structure
2. **PipelineValidator**: Checks required fields, types, wiring
3. **IR Compiler**: Transforms MetaContract to ModuleIR
4. **Python Compiler**: Generates Python code from IR
5. **ComplianceAuditor**: Checks governance compliance
6. **FileEmitter**: Writes files, auto-wires routes
7. **RollbackHook**: Registers snapshots for reversion
8. **Telemetry**: Records metrics
9. **CursorSync**: Updates Cursor context

### Integration Points

- **API**: `/api/codegen/meta` endpoint
- **Agents**: CTOAgent, ReflectionAgent, QAAgent
- **Memory**: PacketEnvelope for audit trail
- **Governance**: Igor escalation path

## License

Part of L9 AI Operating System. Internal use only.
