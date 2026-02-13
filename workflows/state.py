"""
Workflow State Definitions
==========================

TypedDict state schemas for LangGraph workflows.
State is the single source of truth that flows through all nodes.

Design principles:
- State is immutable (nodes return updates, not mutations)
- All fields have sensible defaults
- Reducers handle list accumulation (messages, results)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "State",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:45:56Z",
    "updated_at": "2026-01-25T14:45:51Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "state",
    "type": "enum",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "workflows.__init__",
            "workflows.harvest_deploy",
            "workflows.nodes.checkpoint",
            "workflows.nodes.deploy",
            "workflows.nodes.extract",
            "workflows.nodes.inject",
            "workflows.nodes.report",
            "workflows.nodes.validate",
        ],
    },
}
# ============================================================================

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, TypedDict

# LangGraph is optional - works without it for session DAGs
try:
    from langgraph.graph.message import add_messages
except ImportError:
    # Fallback for when LangGraph isn't installed
    def add_messages(existing: list, new: list) -> list:
        """Fallback message reducer."""
        return existing + new


# =============================================================================
# Enums
# =============================================================================


class StepStatus(str, Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PAUSED = "paused"


# =============================================================================
# Data Classes (as TypedDict for LangGraph compatibility)
# =============================================================================


class FileMapping(TypedDict):
    """Mapping from source to destination file."""

    source: str
    destination: str
    operation: Literal["copy", "inject", "replace"]
    # For inject/replace
    after_line: int | None
    after_pattern: str | None
    start_line: int | None
    end_line: int | None


class ExtractionPattern(TypedDict):
    """Pattern for extracting code from source document."""

    start_line: int
    end_line: int
    output_file: str
    strip_backticks: bool


class ValidationCheck(TypedDict):
    """A validation check to run."""

    check_type: Literal["py_compile", "exists", "grep", "shell", "import"]
    files: list[str]
    pattern: str | None
    command: str | None


class StepResult(TypedDict):
    """Result of executing a workflow step."""

    step_id: str
    success: bool
    output: str
    error: str | None
    duration_ms: float
    artifacts: dict[str, Any]
    timestamp: str


# =============================================================================
# Main Workflow State (LangGraph StateGraph state)
# =============================================================================


def merge_results(
    existing: list[StepResult], new: list[StepResult]
) -> list[StepResult]:
    """Reducer: Append new results to existing."""
    return existing + new


def merge_artifacts(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Reducer: Merge artifact dictionaries."""
    return {**existing, **new}


def merge_files(existing: list[str], new: list[str]) -> list[str]:
    """Reducer: Append files (deduplicated)."""
    return list(dict.fromkeys(existing + new))


class WorkflowState(TypedDict, total=False):
    """
    Central state for harvest-deploy workflows.

    This state flows through all nodes. Nodes read from state
    and return partial updates that get merged.

    Reducers:
        - messages: add_messages (LangGraph built-in)
        - results: merge_results (append)
        - artifacts: merge_artifacts (dict merge)
        - files_*: merge_files (append dedupe)
    """

    # === Workflow Identity ===
    workflow_id: str
    workflow_name: str
    started_at: str

    # === Configuration (set at start) ===
    source_document: str  # Path to source markdown
    plan_document: str  # Path to plan markdown
    harvest_directory: str  # Output dir for extracted files
    working_directory: str  # Project root

    # === Extraction Phase ===
    extraction_patterns: list[ExtractionPattern]
    files_extracted: Annotated[list[str], merge_files]

    # === Deployment Phase ===
    file_mappings: list[FileMapping]
    files_copied: Annotated[list[str], merge_files]
    files_modified: Annotated[list[str], merge_files]

    # === Validation Phase ===
    validation_checks: list[ValidationCheck]
    validation_passed: bool

    # === Results & Artifacts ===
    results: Annotated[list[StepResult], merge_results]
    artifacts: Annotated[dict[str, Any], merge_artifacts]

    # === Control Flow ===
    current_phase: Literal["extract", "deploy", "inject", "validate", "report", "done"]
    should_continue: bool
    error: str | None

    # === Human-in-the-loop ===
    awaiting_confirmation: bool
    confirmation_message: str | None
    user_confirmed: bool | None

    # === Messages (for LangGraph tracing) ===
    messages: Annotated[list[dict], add_messages]


# =============================================================================
# State Factories
# =============================================================================


def create_initial_state(
    workflow_id: str,
    source_document: str,
    harvest_directory: str,
    working_directory: str,
    extraction_patterns: list[ExtractionPattern] | None = None,
    file_mappings: list[FileMapping] | None = None,
    validation_checks: list[ValidationCheck] | None = None,
    plan_document: str | None = None,
) -> WorkflowState:
    """
    Create initial workflow state with sensible defaults.

    Args:
        workflow_id: Unique identifier for this run
        source_document: Path to source markdown with code blocks
        harvest_directory: Where to extract files
        working_directory: Project root
        extraction_patterns: Optional patterns (can be discovered)
        file_mappings: Optional mappings (can be from plan)
        validation_checks: Optional checks (can be inferred)
        plan_document: Optional path to plan document

    Returns:
        Initialized WorkflowState
    """
    return WorkflowState(
        workflow_id=workflow_id,
        workflow_name=f"harvest-deploy-{workflow_id}",
        started_at=datetime.now().isoformat(),
        source_document=source_document,
        plan_document=plan_document or "",
        harvest_directory=harvest_directory,
        working_directory=working_directory,
        extraction_patterns=extraction_patterns or [],
        files_extracted=[],
        file_mappings=file_mappings or [],
        files_copied=[],
        files_modified=[],
        validation_checks=validation_checks or [],
        validation_passed=False,
        results=[],
        artifacts={},
        current_phase="extract",
        should_continue=True,
        error=None,
        awaiting_confirmation=False,
        confirmation_message=None,
        user_confirmed=None,
        messages=[],
    )


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["data-models", "enum", "messaging", "operations"],
    "keywords": [
        "artifacts",
        "check",
        "create",
        "extraction",
        "files",
        "initial",
        "mapping",
        "merge",
    ],
    "business_value": "Provides state components including StepStatus, FileMapping, ExtractionPattern",
    "last_modified": "2026-01-25T14:45:51Z",
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
