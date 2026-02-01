"""
L9 CA Governance Module
========================
Governance layer for CA (Coding Agent) code changes.

This module provides:
- Diff generation for code changes
- Report generation explaining changes
- Constraint validation
- Code change orchestration

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "  Init  ",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T17:47:23Z",
    "updated_at": "2026-01-31T22:21:46Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from .ca_code_change import CACodeChange, ChangeProposal, ChangeStatus
from .constraint_validator import (
    ConstraintValidator,
    ValidationResult,
    Violation,
    ViolationSeverity,
)
from .diff_generator import BatchDiff, DiffGenerator, FileDiff
from .report_generator import ChangeReport, ChangeType, ReportGenerator

__all__ = [
    "BatchDiff",
    # Orchestration
    "CACodeChange",
    "ChangeProposal",
    "ChangeReport",
    "ChangeStatus",
    "ChangeType",
    # Constraint validation
    "ConstraintValidator",
    # Diff generation
    "DiffGenerator",
    "FileDiff",
    # Report generation
    "ReportGenerator",
    "ValidationResult",
    "Violation",
    "ViolationSeverity",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-076",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["auth", "batch-processing", "core", "foundation", "utility"],
    "keywords": ["agent", "changes", "generation", "governance", "module"],
    "business_value": "Diff generation for code changes Report generation explaining changes Constraint validation Code change orchestration Version: 1.0.0 Author: Manus AI Created: 2025-12-20",
    "last_modified": "2026-01-31T22:21:46Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
