# PERPLEXITY SUPERPROMPT: CodeGenAgent Spec-to-Code Conversion
# ================================================================
# Use with Perplexity Research API (sonar-pro or sonar-reasoning)
# Generates production-ready Python implementations from YAML specs
# ================================================================

## EXECUTION INSTRUCTIONS

```
Model: sonar-pro (or sonar-reasoning for deeper analysis)
Temperature: 0.2 (consistent code generation)
Max Tokens: 8000+
Return Citations: true
```

---

# BEGIN SUPERPROMPT

You are an expert software architect and Python developer tasked with implementing a complete **CodeGenAgent module system** for the L9 AI Operating System. You must convert the following YAML specifications into production-ready Python code.

## CONTEXT: L9 CodeGenAgent System

The CodeGenAgent is the central orchestrator for L9's meta-driven code generation pipeline. It transforms YAML specifications into executable Python modules through a phased pipeline:

```
MetaLoader → C-GMP Engine → Pipeline Validator → File Emitter → Telemetry
                    ↓
           Compliance Auditor
                    ↓
         Cursor Context Sync
```

### EXISTING IMPLEMENTATIONS (DO NOT REGENERATE)

These files already exist and are integrated:
- `codegen_agent.py` (main orchestrator - 679 lines)
- `meta_loader.py` (YAML loading - 337 lines)
- `file_emitter.py` (file writing + rollback - 456 lines)
- `c_gmp_engine.py` (code expansion with SymPy - 443 lines)

### MODULES TO GENERATE (9 total)

Generate production Python code for these 9 missing modules:

---

## MODULE 1: ap_generator.py (GMP Prompt Generator)

**YAML Spec:**
```yaml
filename: agents/codegenagent/ap_generator.py
type: generation_module
language: python

description: |
  Generates GMP-ready prompts based on meta.yaml or schema contracts.
  Injects AI-CTO styles, capsule continuity, cursor-marked anchor prompts.

wiring:
  source: meta_contract.yaml
  styles: [ai_cto, capsule_continuity, godmode_feedback]
  output: GMPPromptBlock[]
  consumers:
    - cursor-agent
    - CodeGenAgent
    - ReflectionAgent
```

**Requirements:**
- Class `APGenerator` with methods: `generate_prompt(meta)`, `inject_style(prompt, style)`, `build_gmp_block(meta)`
- Support styles: AI-CTO, Capsule Continuity, GodMode Feedback
- Return structured `GMPPromptBlock` dataclass with sections: inputs, responsibilities, output
- Include template engine for prompt formatting
- ~200-300 lines

---

## MODULE 2: compliance_auditor.py (GMP Compliance Checker)

**YAML Spec:**
```yaml
filename: agents/codegenagent/compliance_auditor.py
type: audit_module
language: python

description: |
  Audits emitted GMP code blocks for:
  - Required policy zone inclusion
  - Patch registration
  - Trace hook presence
  - Memory recovery fallback

wiring:
  checks:
    - mainagent_policy.yaml
    - patch_injection
    - rollback presence
  escalates_if: missing_compliance_fields
```

**Requirements:**
- Class `ComplianceAuditor` with methods: `audit_compliance(meta, files)`, `check_policy_zone(code)`, `check_rollback_handler(code)`, `check_trace_hooks(code)`
- Return `ComplianceResult` dataclass with: passed, failures, warnings, escalation_needed
- Integration with governance escalation (Igor approval flow)
- Support policy YAML configuration
- ~250-350 lines

---

## MODULE 3: cursor_context_sync_engine.py (Bi-Directional Sync)

**YAML Spec:**
```yaml
filename: agents/codegenagent/cursor_context_sync_engine.py
type: sync_bridge
language: python

description: |
  Bi-directional synchronization between CodeGenAgent's generation memory
  and Cursor's visible prompt stack and YAML capsule context.

wiring:
  reads:
    - redis/agent_session/
    - cursor_context_stack.json
  writes:
    - memory_context.yaml
    - cursor_replay.json
    - sync_diff.patch.yaml
  triggers:
    - on_codegen_emit
    - cursor_session_start
    - packet_audit_loop
```

**Requirements:**
- Class `CursorContextSyncEngine` with async methods
- Methods: `sync_cursor_context(agent_id, files)`, `read_agent_state(agent_id)`, `generate_patch(agent_mem, cursor_stack)`, `write_sync_output(agent_id, patch)`
- Integration with Redis for session state
- JSON/YAML serialization for context files
- Event-driven triggers for sync operations
- ~300-400 lines

---

## MODULE 4: cursor_sync.py (Simplified Sync Bridge)

**YAML Spec:**
```yaml
filename: agents/codegenagent/cursor_sync.py
type: state_bridge
language: python

description: |
  Bi-directional sync between CodeGenAgent memory state
  and Cursor-visible session history or instruction stack.

wiring:
  reads: redis/session_state
  writes: cursor_context_envelope.json
  watch: YAML blocks + prompt stack
```

**Requirements:**
- Simpler version of cursor_context_sync_engine.py
- Function `sync_with_cursor(meta, output_files)` and `update_cursor_state(module_name, capsule)`
- Lightweight JSON envelope format
- ~100-150 lines

---

## MODULE 5: pipeline_validator.py (Meta Validation Module)

**YAML Spec:**
```yaml
filename: agents/codegenagent/pipeline_validator.py
type: validation_module
language: python

description: |
  Validates that meta.yaml contains all required fields before generation.

wiring:
  required_fields:
    - name
    - inputs
    - outputs
    - responsibilities
    - required_tests
```

**Requirements:**
- Class `PipelineValidator` with methods: `validate_meta(meta)`, `check_required_fields(meta)`, `validate_structure(meta)`, `validate_wiring(meta)`
- Return `ValidationResult` dataclass with: valid, missing_fields, errors, warnings
- Support configurable required field lists
- Schema-based validation with JSON Schema or Pydantic
- ~200-250 lines

---

## MODULE 6: telemetry_codegen.py (Generation Telemetry)

**YAML Spec:**
```yaml
filename: agents/codegenagent/telemetry_codegen.py
type: telemetry
language: python

description: |
  Emits telemetry from each CGA run:
  - File count
  - Line count
  - Time-to-generate
  - Failure conditions

wiring:
  output: Prometheus
  fields:
    - files_generated
    - generation_latency_ms
    - failure_type
```

**Requirements:**
- Class `CodeGenTelemetry` with methods: `record_generation(meta, files)`, `emit_metrics()`, `track_latency(start, end)`, `record_failure(error_type, details)`
- Prometheus-compatible metrics (Counter, Histogram, Gauge)
- Structured logging with structlog
- Support for OpenTelemetry export
- ~200-300 lines

---

## MODULE 7: rollback_hook.py (Reversion Support)

**YAML Spec (from file_emitter.yaml wiring):**
```yaml
rollback_support:
  hook: agents/codegenagent/rollback_hook.py
  triggers: on_success
  action: register_snapshot
  dependencies:
    - rollback_system.register_snapshot
```

**Requirements:**
- Class `RollbackHook` with methods: `setup_reversion(files)`, `register_snapshot(files)`, `execute_rollback(snapshot_id)`, `list_snapshots()`
- Integration with file_emitter.py rollback mechanism
- Snapshot storage (file-based or Redis-backed)
- ~150-200 lines

---

## MODULE 8: meta.yaml (Self-Declared MetaContract)

**YAML Spec:**
```yaml
filename: agents/codegenagent/meta.yaml
type: meta_contract
language: yaml

description: |
  Self-declared responsibilities and interface for CodeGenAgent v1.0
```

**Requirements:**
- Generate a complete meta.yaml contract file describing CodeGenAgent
- Include: name, version, description, inputs, outputs, responsibilities
- Include batch_generation hooks
- Module-Spec-v2.4 format compliant
- ~80-120 lines YAML

---

## MODULE 9: README.md (Documentation)

**YAML Spec:**
```yaml
filename: agents/codegenagent/README.md
type: documentation
language: markdown

description: |
  Describes CodeGenAgent design, orchestration flow, module structure, API interface.
```

**Requirements:**
- Complete README with: Overview, Architecture, Module descriptions, API reference, Usage examples
- Include ASCII architecture diagram
- Quick-start guide
- ~300-500 lines markdown

---

## QUALITY REQUIREMENTS (MANDATORY)

All generated Python code MUST:

1. **Type Hints**: 100% coverage on public APIs
2. **Docstrings**: Google-style docstrings on all classes and public methods
3. **Error Handling**: Explicit exception handling with custom exception classes
4. **Logging**: Use `structlog` for structured logging throughout
5. **Async Support**: Use `async/await` where I/O is involved
6. **Dataclasses**: Use `@dataclass` or Pydantic `BaseModel` for all data structures
7. **No External Dependencies**: Standard library + existing L9 deps only (structlog, pydantic, redis, yaml)
8. **Integration Ready**: All modules must import cleanly into existing codegen_agent.py

## CODE PATTERNS TO FOLLOW

```python
# Standard imports pattern
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)

# Exception pattern
class ModuleNameError(Exception):
    """Exception raised when [specific condition]."""
    pass

# Dataclass pattern
@dataclass
class ResultType:
    """Result of [operation]."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {...}

# Class pattern
class ModuleName:
    """
    [Description].
    
    Provides [functionality] for [purpose].
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize [module]."""
        self._config = config or {}
        logger.info("module_initialized", config=self._config)
    
    async def main_method(self, input: InputType) -> ResultType:
        """[Description]."""
        try:
            # Implementation
            logger.info("operation_complete", ...)
            return ResultType(success=True, ...)
        except Exception as e:
            logger.error("operation_failed", error=str(e))
            return ResultType(success=False, errors=[str(e)])
```

## INTEGRATION WIRING

All modules must integrate with existing `codegen_agent.py` orchestrator:

```python
# In codegen_agent.py, add imports:
from agents.codegenagent.ap_generator import APGenerator
from agents.codegenagent.compliance_auditor import ComplianceAuditor
from agents.codegenagent.cursor_context_sync_engine import CursorContextSyncEngine
from agents.codegenagent.pipeline_validator import PipelineValidator
from agents.codegenagent.telemetry_codegen import CodeGenTelemetry
from agents.codegenagent.rollback_hook import RollbackHook
```

## GMP PHASE REQUIREMENTS

This code generation follows GMP v1.7 phases:

- **Phase 0**: Schema locked (this spec)
- **Phase 1**: Baseline confirmation (imports work)
- **Phase 2**: Implementation (generate all 9 files)
- **Phase 3**: Enforcement (governance hooks, validation)
- **Phase 4**: Validation (tests pass, coverage ≥85%)
- **Phase 5**: Recursive verification (no drift from spec)
- **Phase 6**: Finalization (evidence report, sign-off)

## OUTPUT FORMAT

Structure your response as:

### 1. ARCHITECTURE OVERVIEW
- ASCII diagram showing module relationships
- Data flow description

### 2. MODULE IMPLEMENTATIONS (9 files)
For each module:
```
### MODULE N: filename.py
[Full Python code with all requirements met]
```

### 3. INTEGRATION PATCH
- Code to add to `codegen_agent.py` to wire new modules

### 4. TEST STUBS
- Pytest test file stubs for each module

### 5. EVIDENCE SUMMARY
- Checklist confirming all requirements met

---

## RESEARCH CONTEXT

Before generating code:
1. Research Python best practices for code generation systems
2. Research Cursor IDE integration patterns
3. Research GMP (Governance Managed Process) implementation patterns
4. Research telemetry/observability patterns for code generation

Include relevant citations where applicable.

---

# DELIVERABLES SUMMARY

| File | Type | Est. Lines | Priority |
|------|------|------------|----------|
| ap_generator.py | Python | 250 | HIGH |
| compliance_auditor.py | Python | 300 | HIGH |
| cursor_context_sync_engine.py | Python | 350 | MEDIUM |
| cursor_sync.py | Python | 125 | LOW |
| pipeline_validator.py | Python | 225 | HIGH |
| telemetry_codegen.py | Python | 250 | MEDIUM |
| rollback_hook.py | Python | 175 | MEDIUM |
| meta.yaml | YAML | 100 | LOW |
| README.md | Markdown | 400 | LOW |
| **TOTAL** | | **~2,175** | |

Generate ALL files as complete, production-ready implementations ready for immediate use in the L9 codebase.

# END SUPERPROMPT
