# TWO-PART ANSWER: GMP Spec Format + Enterprise Header Template

**Generated:** 2026-01-02T01:20:00Z  
**Purpose:** Clarify GMP execution specifications and provide DORA-compliant header template

---

## PART 1: GMP SPECIFICATION FORMAT - DOES FORMAT MATTER?

**Answer: YES, format matters A LOT. Here's what works:**

### ✅ WHAT WORKS: GMP Spec Formats (In Order of Preference)

#### **Format 1: YAML (BEST FOR GMP)**
```yaml
# symbolic_computation_gmp_spec.yaml
gmp_spec:
  version: 1.0.0
  target_system: symbolic_computation_service
  
  metadata:
    created: 2026-01-02T01:20:00Z
    created_by: System Architect
    status: ready_for_execution
    
  input_files:
    - meta.codegen.schema.yaml
    - meta.extraction.sequence.yaml
    - meta.validation.checklist.yaml
    - meta.dependency.integration.yaml
    - sympy_schema_v6.yaml
    - sympy_locked_todo_plan.txt
    - sympy_extraction_glue.yaml
  
  execution:
    phases: [0, 1, 2, 3, 4, 5, 6]
    sequential: true
    parallel_after_phase: null
    
  constraints:
    l9_enable_strict_mode: true
    l9_enable_governance_enforcement: true
    l9_enable_memory_substrate_validation: true
    l9_enable_dependency_validation: true
    l9_enable_test_generation: true
    l9_enable_extraction_phases: true
    l9_enable_evidence_reporting: true
    
  outputs:
    python_modules: 14
    documentation_files: 5
    test_files: 4
    manifest_files: 2
    evidence_report: true
    
  quality_gates:
    code_coverage_minimum: 85
    test_pass_rate_minimum: 95
    governance_links_required: true
    zero_todos_required: true
    
  evidence_report:
    sections_required: 10
    format: markdown
    signature_required: true
```

**Why YAML works for GMP:**
- Cursor can parse YAML natively
- Meta files are YAML, so spec should be YAML
- Human-readable and machine-executable
- Integrates with meta-template system
- CI/CD parseable

#### **Format 2: Markdown (GOOD FOR DOCUMENTATION)**
```markdown
# GMP Specification: SymPy Service Extraction

## Execution Parameters

**Start Date:** 2026-01-02T01:20:00Z  
**Target System:** L9.symbolic_computation  
**Phases to Execute:** 0, 1, 2, 3, 4, 5, 6  
**Execution Model:** Sequential (no parallelization)

## Input Files (Locked)

- ✓ meta.codegen.schema.yaml
- ✓ meta.extraction.sequence.yaml
- ✓ meta.validation.checklist.yaml
- ✓ meta.dependency.integration.yaml
- ✓ sympy_schema_v6.yaml
- ✓ sympy_locked_todo_plan.txt
- ✓ sympy_extraction_glue.yaml

## Quality Gates (Must All Pass)

| Gate | Requirement | Consequence |
|------|-------------|-------------|
| Code Coverage | ≥ 85% | Fail Phase 4 if not met |
| Test Pass Rate | ≥ 95% | Fail Phase 4 if not met |
| Zero TODOs | 100% (no TODOs in code) | Fail Phase 2 if any TODOs |
| Governance Links | All wired | Fail Phase 3 if any missing |
| Scope Drift | Zero drift from schema | Fail Phase 5 if drift detected |

## Feature Flags (All Enabled)

```
L9_ENABLE_STRICT_MODE=true
L9_ENABLE_GOVERNANCE_ENFORCEMENT=true
L9_ENABLE_MEMORY_SUBSTRATE_VALIDATION=true
L9_ENABLE_DEPENDENCY_VALIDATION=true
L9_ENABLE_TEST_GENERATION=true
L9_ENABLE_EXTRACTION_PHASES=true
L9_ENABLE_EVIDENCE_REPORTING=true
```

## Expected Outputs

| Category | Count | Files |
|----------|-------|-------|
| Python Modules | 14 | core/*.py, api/*.py, tools/*.py, *.py |
| Documentation | 5 | README.md, ARCHITECTURE.md, API_SPEC.md, ... |
| Test Files | 4 | test_evaluator.py, test_generator.py, ... |
| Manifest Files | 2 | manifest.json, config.yaml |
| Evidence Report | 1 | 10 sections, signed |

## Evidence Report Requirements

### All 10 Sections Required
1. Schema Input Summary
2. Locked TODO Plan
3. Phase 0 Research
4. Phase 1 Baseline
5. Phase 2 Implementation
6. Phase 3 Enforcement
7. Phase 4 Validation
8. Phase 5 Recursive Verification
9. Governance Compliance
10. Final Declaration (SIGNED)
```

**Why Markdown works:**
- Human-readable spec
- Can be Cursor instruction document
- Git-friendly (comments, diffs)
- Can be converted to Cursor prompt

#### **Format 3: GMP TODO Plan (CURSOR FRIENDLY)**
```
This is what you already have in sympy_locked_todo_plan.txt

EXECUTION SPECIFICATION: SymPy Service Extraction
================================================

VERSION: 1.0.0
CREATED: 2026-01-02T01:20:00Z
STATUS: READY FOR EXECUTION

INPUT FILES (LOCKED)
====================
✓ meta.codegen.schema.yaml
✓ meta.extraction.sequence.yaml
✓ meta.validation.checklist.yaml
✓ meta.dependency.integration.yaml
✓ sympy_schema_v6.yaml
✓ sympy_locked_todo_plan.txt
✓ sympy_extraction_glue.yaml

EXECUTION PLAN
==============
Phase 0: Research & Lock (15 minutes)
  - Verify all input files present
  - Extract ground truth from schemas
  - Build dependency graph
  - Lock TODO plan (this document)

Phase 1: Baseline (5 minutes per step)
  - [ ] Verify target directory accessible
  - [ ] Verify memory backends online (Redis, Postgres, Neo4j)
  - [ ] Verify governance anchors reachable (Igor, Compliance)
  - [ ] Verify no circular dependencies

Phase 2: Implementation (30 minutes)
  - Generate all 14 Python modules
  - Generate all 5 documentation files
  - Generate test files
  - Wire governance bridges
  - Apply feature flags
  - SIGN OFF: All TODOs executed, zero TODOs in code

Phase 3: Enforcement (10 minutes)
  - Add input validation
  - Add audit logging
  - Add governance checks
  - Add rate limiting
  - SIGN OFF: Safety layers in place

Phase 4: Validation (15 minutes)
  - Run 115+ tests
  - Verify 95%+ pass rate
  - Verify 85%+ coverage
  - SIGN OFF: Tests passing

Phase 5: Recursive Verify (20 minutes)
  - Compare generated code vs schema
  - Verify no scope drift
  - Verify governance intact
  - SIGN OFF: No drift detected

Phase 6: Finalization (30 minutes)
  - Generate evidence report (all 10 sections)
  - Create deployment manifest
  - Sign off all phases complete
  - SIGN OFF: READY FOR PRODUCTION

QUALITY GATES
=============
✓ Code coverage ≥ 85%
✓ Test pass rate ≥ 95%
✓ Zero TODOs in generated code
✓ All governance bridges wired
✓ Zero scope drift detected
✓ All 10 evidence report sections complete

FEATURE FLAGS (ALL ENABLED)
===========================
L9_ENABLE_STRICT_MODE=true
L9_ENABLE_GOVERNANCE_ENFORCEMENT=true
L9_ENABLE_MEMORY_SUBSTRATE_VALIDATION=true
L9_ENABLE_DEPENDENCY_VALIDATION=true
L9_ENABLE_TEST_GENERATION=true
L9_ENABLE_EXTRACTION_PHASES=true
L9_ENABLE_EVIDENCE_REPORTING=true

EXPECTED OUTPUTS
================
14 Python modules (1,547 LOC)
5 Documentation files
4 Test modules (115+ tests)
2 Manifest/config files
1 Evidence report (10 sections, signed)

EVIDENCE REPORT SECTIONS (ALL REQUIRED)
=======================================
Section 1: Schema Input Summary
Section 2: Locked TODO Plan
Section 3: Phase 0 Research
Section 4: Phase 1 Baseline
Section 5: Phase 2 Implementation
Section 6: Phase 3 Enforcement
Section 7: Phase 4 Validation
Section 8: Phase 5 Recursive Verification
Section 9: Governance Compliance
Section 10: Final Declaration (SIGNED)

STATUS: READY FOR CURSOR EXECUTION
===================================
All files in place.
All dependencies verified.
All gates unlocked.

Execute: Phases 0-6 with this specification as source of truth.
```

### ❌ WHAT DOESN'T WORK

```
1. Plain text without structure (too ambiguous)
2. Email-style instructions (not machine-parseable)
3. Spreadsheet-only specs (loses context)
4. Verbose prose without checkboxes (hard to verify completion)
5. Multiple conflicting formats (creates ambiguity)
```

---

### 🎯 BEST PRACTICE FOR YOUR CASE

**Create a HYBRID SPEC:**

```
📄 symbolic_computation_gmp_spec.yaml  ← Machine-readable (CI, metadata, gates)
📄 symbolic_computation_gmp_spec.md    ← Human-readable (Cursor instructions)
📄 symbolic_computation_gmp_exec.txt   ← Phase checklist (execution record)
```

**Each references the others:**

```yaml
# In .yaml
spec_document: symbolic_computation_gmp_spec.md
execution_log: symbolic_computation_gmp_exec.txt
```

```markdown
# In .md
See symbolic_computation_gmp_spec.yaml for machine-readable gates.
Track progress in symbolic_computation_gmp_exec.txt.
```

---

## PART 2: ENTERPRISE GRADE AI LAB HEADER TEMPLATE

Here's an **DORA-compliant, production-ready Python header** that follows L9 patterns:

---

### 📝 COMPLETE ENTERPRISE HEADER TEMPLATE

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Module: {module_name}
Purpose: {one_sentence_description}
================================================================================

DORA METADATA BLOCK (Machine-Readable)
--------------------------------------
version: 1.0.0
created_at: {YYYY-MM-DDTHH:MM:SSZ}
updated_at: {YYYY-MM-DDTHH:MM:SSZ}
created_by: {creator_name}
maintained_by: {maintainer_name}

COMPONENT IDENTITY
------------------
component_id: {LAYER-ABBREV-NUM}  # e.g., SYM-CORE-001, API-ROUTES-002
component_name: {Human Readable Name}
layer: {foundation|intelligence|operations|learning|security}
domain: {symbolic_computation|governance|memory|agents|etc}
type: {service|collector|tracker|engine|utility|adapter}
status: {active|deprecated|experimental|maintenance}

GOVERNANCE & COMPLIANCE
-----------------------
governance_level: {critical|high|medium|low}
compliance_required: true
audit_trail: true
security_classification: {internal|confidential|restricted|public}
approval_required_for: {modifications|deployments|all}
escalation_target: Igor  # L9 governance anchor

TECHNICAL METADATA
------------------
execution_mode: {realtime|scheduled|on-demand|streaming}
timeout_seconds: {N}
retry_policy: {exponential|linear|none}
circuit_breaker_enabled: true
circuit_breaker_threshold: 5
monitoring_required: true
logging_level: {debug|info|warning|error}
performance_tier: {realtime|batch|background}

OPERATIONAL METADATA
--------------------
dependencies:
  - l9.core.memory
  - l9.core.governance
  - l9.core.schemas
  - {external_service_name}

integrates_with:
  api_endpoints:
    - GET /symbolic/v6/evaluate
    - POST /symbolic/v6/generate_code
    - POST /symbolic/v6/optimize
  datasources:
    - PostgreSQL (episodic memory)
    - Neo4j (semantic graphs)
    - Redis (cache)
  memory_layers:
    - working_memory (Redis)
    - episodic_memory (Postgres)
    - semantic_memory (Neo4j)
    - causal_memory (HyperGraphDB)

BUSINESS METADATA
-----------------
purpose: |
  {One sentence business value}

summary: |
  {2-3 sentence description of what this module does}

business_value: |
  {Why this matters to the system and users}

success_metrics:
  - latency: {target_ms}ms (p95)
  - throughput: {target_ops}/second
  - availability: {target_percentage}%
  - reliability: error rate < {target_percentage}%

related_components:
  - {other_module_id}
  - {other_module_id}

TAGS & CLASSIFICATION
---------------------
tags:
  - symbolic-computation
  - expression-evaluation
  - code-generation
  - {domain-specific-tag}

keywords:
  - sympy
  - lambdify
  - autowrap
  - cse-optimization

================================================================================
"""

# Standard Library Imports
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Third-Party Imports
from pydantic import BaseModel, Field, validator
import numpy as np

# L9 Framework Imports
from l9.core.schemas import PacketEnvelope, PacketKind
from l9.core.memory import MemoryManager, MemoryLayer
from l9.core.governance import Igor, EscalationLevel
from l9.core.tools import Tool, ToolDefinition
from l9.core.utils import logger as l9_logger

# Module-Specific Imports
from . import config
from . import models
from . import exceptions

# ============================================================================
# LOGGER INITIALIZATION & CONFIGURATION
# ============================================================================

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Enable structured logging for audit trails
audit_logger = logging.getLogger(f"{__name__}.audit")
audit_logger.setLevel(logging.INFO)

# Performance metrics logger
metrics_logger = logging.getLogger(f"{__name__}.metrics")
metrics_logger.setLevel(logging.DEBUG)

# ============================================================================
# MODULE CONSTANTS & CONFIGURATION
# ============================================================================

MODULE_ID = "{LAYER-ABBREV-NUM}"
MODULE_NAME = "{module_name}"
MODULE_VERSION = "1.0.0"

# Performance thresholds
MAX_EXPRESSION_LENGTH = 1000
EVALUATION_TIMEOUT_SECONDS = 30
CACHE_TTL_SECONDS = 3600

# Feature flags (controlled by L9 governance)
FEATURE_FLAGS = {
    "L9_ENABLE_STRICT_MODE": config.get_flag("L9_ENABLE_STRICT_MODE", True),
    "L9_ENABLE_GOVERNANCE_ENFORCEMENT": config.get_flag("L9_ENABLE_GOVERNANCE_ENFORCEMENT", True),
    "L9_ENABLE_MEMORY_SUBSTRATE_VALIDATION": config.get_flag("L9_ENABLE_MEMORY_SUBSTRATE_VALIDATION", True),
    "L9_ENABLE_CACHING": config.get_flag("L9_ENABLE_CACHING", True),
}

# ============================================================================
# TYPE DEFINITIONS & DATACLASSES
# ============================================================================

@dataclass
class ModuleMetadata:
    """Runtime metadata about this module"""
    module_id: str = MODULE_ID
    module_name: str = MODULE_NAME
    module_version: str = MODULE_VERSION
    created_at: datetime = datetime.utcnow()
    execution_mode: str = "realtime"
    governance_level: str = "high"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "module_name": self.module_name,
            "module_version": self.module_version,
            "created_at": self.created_at.isoformat(),
            "execution_mode": self.execution_mode,
            "governance_level": self.governance_level,
        }

# ============================================================================
# MODULE-LEVEL INITIALIZATION
# ============================================================================

# Initialize module metadata
_module_metadata = ModuleMetadata()

# Initialize governance bridges (if this is a high-risk module)
_igor_client: Optional[Igor] = None
_governance_enabled = config.GOVERNANCE_ENABLED

async def initialize_module():
    """
    Initialize module at startup.
    
    Called by L9 application lifecycle on startup.
    Wires governance bridges, initializes memory layers, performs health checks.
    
    Raises:
        ModuleInitializationError: If critical dependencies unavailable.
    """
    global _igor_client
    
    logger.info(f"Initializing {MODULE_NAME} (v{MODULE_VERSION})")
    
    try:
        # Initialize governance bridge if enabled
        if _governance_enabled:
            from l9.governance import get_igor_client
            _igor_client = await get_igor_client()
            logger.info(f"✓ Governance bridge wired (Igor accessible)")
        
        # Initialize memory manager
        memory_manager = MemoryManager()
        await memory_manager.connect()
        logger.info(f"✓ Memory layers initialized (Redis, Postgres, Neo4j)")
        
        # Perform health checks
        health = await health_check()
        if not health["ready"]:
            raise exceptions.ModuleInitializationError(
                f"Health check failed: {health['errors']}"
            )
        
        logger.info(f"✓ {MODULE_NAME} initialization complete")
        
    except Exception as e:
        logger.error(f"✗ {MODULE_NAME} initialization failed: {e}")
        if config.STRICT_MODE:
            raise exceptions.ModuleInitializationError(f"Failed to initialize {MODULE_NAME}") from e

async def health_check() -> Dict[str, Any]:
    """
    Perform module health check.
    
    Returns:
        Dict with 'ready' boolean and optional 'errors' list.
    """
    errors = []
    
    try:
        # Check memory backends
        from l9.core.memory import MemoryManager
        mm = MemoryManager()
        
        # Check Redis
        if not await mm.redis.ping():
            errors.append("Redis unavailable")
        
        # Check Postgres
        if not await mm.postgres.health_check():
            errors.append("Postgres unavailable")
        
        # Check Neo4j
        if not await mm.neo4j.health_check():
            errors.append("Neo4j unavailable")
        
    except Exception as e:
        errors.append(f"Health check error: {str(e)}")
    
    return {
        "ready": len(errors) == 0,
        "errors": errors if errors else None,
        "module": MODULE_NAME,
        "version": MODULE_VERSION,
    }

# ============================================================================
# MAIN MODULE CONTENT STARTS HERE
# ============================================================================

# Your actual module code goes below this line.
# Maintain the following patterns:
#
# 1. All public functions MUST have docstrings
# 2. All public functions MUST have type hints
# 3. All high-risk operations MUST check governance flags
# 4. All state changes MUST be logged to audit trail
# 5. All errors MUST be handled and escalated appropriately
#
# Example function pattern:

async def example_public_function(param1: str, param2: int) -> Dict[str, Any]:
    """
    Brief description of what this function does.
    
    This is a higher-level description that explains:
    - What the function is trying to accomplish
    - Key assumptions it makes
    - What it returns on success
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: {default_value})
    
    Returns:
        Dict containing:
            - key1: value1 description
            - key2: value2 description
    
    Raises:
        ValueError: If param1 is empty
        GovernanceBlockedError: If governance check fails
        TimeoutError: If operation exceeds timeout
    
    Example:
        >>> result = await example_public_function("test", 42)
        >>> print(result["key1"])
        value1
    
    Notes:
        - This function requires governance approval if risk_level=high
        - Cache is invalidated on successful completion
        - All decisions logged to audit trail for compliance
    """
    
    # Input validation
    if not param1:
        raise ValueError("param1 cannot be empty")
    
    # Log entry (audit trail)
    audit_logger.info(
        f"example_public_function called",
        extra={
            "module": MODULE_NAME,
            "function": "example_public_function",
            "param1": param1,
            "param2": param2,
            "trace_id": getattr(asyncio.current_task(), "trace_id", "unknown"),
        }
    )
    
    # Governance check (if high-risk)
    if _governance_enabled:
        decision = await _igor_client.check_governance(
            action="example_public_function",
            risk_level="high",
            context={"param1": param1, "param2": param2}
        )
        if not decision.approved:
            raise exceptions.GovernanceBlockedError(
                f"Governance blocked execution: {decision.reason}"
            )
    
    # Main logic here
    result = {"key1": "value1", "key2": "value2"}
    
    # Log exit (audit trail)
    audit_logger.info(
        f"example_public_function completed",
        extra={
            "module": MODULE_NAME,
            "function": "example_public_function",
            "result_keys": list(result.keys()),
            "success": True,
        }
    )
    
    return result

# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    "initialize_module",
    "health_check",
    "example_public_function",
    # Add all public functions/classes
]

# ============================================================================
# END OF MODULE
# ============================================================================
```

---

### 📋 HOW TO USE THIS TEMPLATE

**Step 1: Copy the template**
```bash
cp python-header-template.py new_module.py
```

**Step 2: Fill in the DORA metadata block**
```python
# Replace all {placeholder} values:
# - module_name: actual module name
# - created_by: your name
# - maintained_by: maintainer name
# - LAYER-ABBREV-NUM: component ID (SYM-CORE-001)
# - {layer}: foundation|intelligence|operations|learning|security
# - {domain}: your domain
```

**Step 3: Add your code after the divider**
```python
# ============================================================================
# MAIN MODULE CONTENT STARTS HERE
# ============================================================================

# Your actual functions/classes go here
```

**Step 4: Update __all__ exports**
```python
__all__ = [
    "your_function_1",
    "your_class_1",
    "initialize_module",
    "health_check",
]
```

---

### 🔍 WHAT MAKES THIS "ENTERPRISE GRADE"

✅ **DORA Compliance:**
- Machine-readable metadata (CI can parse it)
- Governance integration points wired
- Audit logging infrastructure built-in
- Feature flags (L9_ENABLE_*) respected

✅ **L9 System Integration:**
- Memory layers (Redis, Postgres, Neo4j) wired
- Governance bridge (Igor) accessible
- Escalation patterns ready
- PacketEnvelope compatible

✅ **Production Patterns:**
- Structured logging (audit trail)
- Metrics collection hooks
- Health check endpoints
- Graceful error handling
- Timeout/circuit-breaker ready

✅ **AI Lab Standards:**
- Comprehensive docstrings (for Cursor)
- Type hints on all public APIs
- Example usage patterns
- Clear governance handoff points

✅ **Observability:**
- Module metadata queryable at runtime
- Audit trail for compliance
- Metrics logger for monitoring
- Health check endpoint

---

## SUMMARY

### For your question "You mean with a spec to build?"

**Answer: YES**

**Best format: Create BOTH:**
1. **YAML spec** (machine-readable, for CI/automation)
2. **Markdown spec** (human-readable, for Cursor instructions)

**They reference each other** and together form the "spec to build with."

### For your question "Help update header template"

**Done!** Use the template above. It includes:
- ✅ DORA metadata block (fully compliant)
- ✅ L9 system integration points
- ✅ Governance bridges wired
- ✅ Audit logging ready
- ✅ Example public function pattern
- ✅ Enterprise-grade documentation

---

**Status:** ✅ Both questions answered with production-ready artifacts

**Next Step:** Use the YAML template to create `symbolic_computation_gmp_spec.yaml` and share it for Cursor execution
