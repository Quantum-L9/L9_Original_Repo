"""
L9 DORA Block Runtime
=====================

Provides the @l9_traced decorator and DORA block auto-update machinery.

The DORA Block is a machine-managed runtime trace that auto-updates at the
VERY END of every generated file on every execution.

Key components:
- @l9_traced decorator: Wraps functions to capture execution traces
- DoraTraceBlock: Data model for the L9_TRACE_TEMPLATE
- update_dora_block(): Writes trace data to file footer

LOCKED TERMINOLOGY (from codegen/sympy/phase 4/Dora-Block.md):
- Header Meta: TOP of file, static module identity
- Footer Meta: BOTTOM of file, extended metadata
- DORA Block: VERY END, after Footer Meta, auto-updates on every run

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Dora",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "dora",
    "type": "dataclass",
    "status": "draft",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["core.agents.executor", "runtime.__init__"],
    },
}
# ============================================================================

import functools
import inspect
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass, field, asdict

import structlog
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


# =============================================================================
# DORA Block Data Model
# =============================================================================


@dataclass
class DoraMetrics:
    """Metrics captured during execution."""

    confidence: str = ""
    errors_detected: List[str] = field(default_factory=list)
    stability_score: str = ""
    duration_ms: Optional[int] = None


@dataclass
class DoraGraph:
    """Execution graph (nodes/edges for call flow visualization)."""

    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DoraTraceBlock:
    """
    The DORA Block schema (L9_TRACE_TEMPLATE).

    This is the runtime trace block that auto-updates on every execution.
    Located at VERY END of file, after Footer Meta.
    """

    trace_id: str = ""
    task: str = ""
    timestamp: str = ""
    patterns_used: List[str] = field(default_factory=list)
    graph: DoraGraph = field(default_factory=DoraGraph)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    metrics: DoraMetrics = field(default_factory=DoraMetrics)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "trace_id": self.trace_id,
            "task": self.task,
            "timestamp": self.timestamp,
            "patterns_used": self.patterns_used,
            "graph": asdict(self.graph),
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metrics": asdict(self.metrics),
        }

    @classmethod
    def create(
        cls,
        task: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        patterns_used: Optional[List[str]] = None,
        duration_ms: Optional[int] = None,
        errors: Optional[List[str]] = None,
    ) -> "DoraTraceBlock":
        """Factory method to create a new trace block."""
        return cls(
            trace_id=str(uuid.uuid4())[:8],
            task=task,
            timestamp=datetime.now(timezone.utc).isoformat(),
            patterns_used=patterns_used or [],
            graph=DoraGraph(),
            inputs=cls._sanitize_for_json(inputs),
            outputs=cls._sanitize_for_json(outputs),
            metrics=DoraMetrics(
                duration_ms=duration_ms,
                errors_detected=errors or [],
                stability_score="1.0" if not errors else "0.5",
                confidence="0.95" if not errors else "0.7",
            ),
        )

    @staticmethod
    def _sanitize_for_json(data: Any) -> Any:
        """Recursively sanitize data for JSON serialization."""
        if data is None:
            return None
        if isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, (list, tuple)):
            return [
                DoraTraceBlock._sanitize_for_json(item) for item in data[:10]
            ]  # Limit list size
        if isinstance(data, dict):
            return {
                str(k): DoraTraceBlock._sanitize_for_json(v)
                for k, v in list(data.items())[:20]  # Limit dict size
            }
        # For complex objects, return string representation
        try:
            return str(data)[:200]  # Limit string length
        except Exception:
            return "<non-serializable>"


# =============================================================================
# DORA Block File Operations
# =============================================================================


# Regex patterns to find existing DORA blocks
DORA_BLOCK_START_PY = re.compile(
    r"^# ={10,}\n# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT\n# ={10,}\n", re.MULTILINE
)
DORA_BLOCK_END_PY = re.compile(
    r"^# ={10,}\n# END L9 DORA BLOCK\n# ={10,}\s*$", re.MULTILINE
)

DORA_BLOCK_PATTERN_PY = re.compile(
    r"(# ={10,}\n# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT\n# ={10,}\n)"
    r"(__l9_trace__\s*=\s*\{.*?\})\n"
    r"(# ={10,}\n# END L9 DORA BLOCK\n# ={10,})",
    re.DOTALL,
)


def format_dora_block_python(trace: DoraTraceBlock) -> str:
    """Format DORA block for Python files."""
    trace_dict = trace.to_dict()
    # Pretty print the dict as valid Python
    lines = ["# " + "=" * 76]
    lines.append("# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT")
    lines.append("# " + "=" * 76)
    lines.append("__l9_trace__ = {")

    for key, value in trace_dict.items():
        if isinstance(value, dict):
            lines.append(f'    "{key}": {json.dumps(value, default=str)},')
        elif isinstance(value, list):
            lines.append(f'    "{key}": {json.dumps(value, default=str)},')
        elif isinstance(value, str):
            lines.append(f'    "{key}": {json.dumps(value)},')
        else:
            lines.append(f'    "{key}": {json.dumps(value, default=str)},')

    lines.append("}")
    lines.append("# " + "=" * 76)
    lines.append("# END L9 DORA BLOCK")
    lines.append("# " + "=" * 76)

    return "\n".join(lines)


def update_dora_block_in_file(
    file_path: Union[str, Path],
    trace: DoraTraceBlock,
) -> bool:
    """
    Update the DORA block at the end of a file.

    If no DORA block exists, appends one at the very end.
    If one exists, replaces it with the new trace.

    Args:
        file_path: Path to the file to update
        trace: The DoraTraceBlock to write

    Returns:
        True if update succeeded, False otherwise
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.warning(f"dora.update_block: file not found: {file_path}")
        return False

    # Determine file type and format
    suffix = file_path.suffix.lower()
    if suffix not in (".py", ".yaml", ".yml", ".json"):
        logger.debug(f"dora.update_block: unsupported file type: {suffix}")
        return False

    try:
        content = file_path.read_text(encoding="utf-8")

        if suffix == ".py":
            new_block = format_dora_block_python(trace)

            # Check if DORA block already exists
            if DORA_BLOCK_PATTERN_PY.search(content):
                # Replace existing block
                new_content = DORA_BLOCK_PATTERN_PY.sub(new_block, content)
            else:
                # Append new block at very end
                # Ensure proper spacing
                if not content.endswith("\n"):
                    content += "\n"
                if not content.endswith("\n\n"):
                    content += "\n"
                new_content = content + new_block + "\n"

            file_path.write_text(new_content, encoding="utf-8")
            logger.info(f"dora.update_block: updated {file_path}")
            return True

        # TODO(GMP-117): Add YAML and JSON support
        logger.debug(f"dora.update_block: {suffix} support not yet implemented")
        return False

    except Exception as e:
        logger.exception(f"dora.update_block: error updating {file_path}: {e}")
        return False


# =============================================================================
# @l9_traced Decorator
# =============================================================================


# Type variable for preserving function signature
F = TypeVar("F", bound=Callable[..., Any])


def l9_traced(
    func: Optional[F] = None,
    *,
    task_name: Optional[str] = None,
    patterns: Optional[List[str]] = None,
    update_source: bool = False,
    source_file: Optional[Union[str, Path]] = None,
) -> Union[F, Callable[[F], F]]:
    """
    Decorator to trace function execution for DORA Block.

    Captures:
    - Function inputs (args/kwargs)
    - Function outputs (return value)
    - Execution time
    - Errors (if any)
    - Patterns used (optional)

    Optionally updates the DORA block at the end of the source file.

    Args:
        func: The function to decorate (if used without parentheses)
        task_name: Override the task name (defaults to function name)
        patterns: List of pattern names used by this function
        update_source: If True, update the DORA block in the source file
        source_file: Override the source file path (auto-detected if None)

    Returns:
        Decorated function that logs execution traces

    Example:
        @l9_traced
        def my_function(x: int) -> int:
            return x * 2

        @l9_traced(patterns=["safety_check", "symbolic_eval"], update_source=True)
        def process_expression(expr: str) -> dict:
            ...
    """

    def decorator(fn: F) -> F:
        # Determine source file for DORA block updates
        _source_file = source_file
        if _source_file is None and update_source:
            try:
                _source_file = Path(inspect.getfile(fn))
            except (TypeError, OSError):
                _source_file = None

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Capture inputs
            sig = inspect.signature(fn)
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            inputs = dict(bound.arguments)

            # Track execution
            start_time = datetime.now(timezone.utc)
            errors: List[str] = []
            output: Any = None

            try:
                output = fn(*args, **kwargs)
                return output
            except Exception as e:
                errors.append(f"{type(e).__name__}: {str(e)}")
                raise
            finally:
                # Calculate duration
                end_time = datetime.now(timezone.utc)
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                # Create trace block
                trace = DoraTraceBlock.create(
                    task=task_name or fn.__name__,
                    inputs=inputs,
                    outputs={"output": output} if output is not None else {},
                    patterns_used=patterns or [],
                    duration_ms=duration_ms,
                    errors=errors if errors else None,
                )

                # Log trace
                logger.info(
                    "dora.trace",
                    task=trace.task,
                    trace_id=trace.trace_id,
                    duration_ms=duration_ms,
                    has_errors=bool(errors),
                )

                # Optionally update source file
                if update_source and _source_file:
                    update_dora_block_in_file(_source_file, trace)

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Capture inputs
            sig = inspect.signature(fn)
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            inputs = dict(bound.arguments)

            # Track execution
            start_time = datetime.now(timezone.utc)
            errors: List[str] = []
            output: Any = None

            try:
                output = await fn(*args, **kwargs)
                return output
            except Exception as e:
                errors.append(f"{type(e).__name__}: {str(e)}")
                raise
            finally:
                # Calculate duration
                end_time = datetime.now(timezone.utc)
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                # Create trace block
                trace = DoraTraceBlock.create(
                    task=task_name or fn.__name__,
                    inputs=inputs,
                    outputs={"output": output} if output is not None else {},
                    patterns_used=patterns or [],
                    duration_ms=duration_ms,
                    errors=errors if errors else None,
                )

                # Log trace
                logger.info(
                    "dora.trace",
                    task=trace.task,
                    trace_id=trace.trace_id,
                    duration_ms=duration_ms,
                    has_errors=bool(errors),
                )

                # Optionally update source file
                if update_source and _source_file:
                    update_dora_block_in_file(_source_file, trace)

        # Return appropriate wrapper
        if inspect.iscoroutinefunction(fn):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    # Handle both @l9_traced and @l9_traced() syntax
    if func is not None:
        return decorator(func)
    return decorator


# =============================================================================
# Executor Integration Hook
# =============================================================================


@must_stay_async("callers use await")
async def emit_executor_trace(
    task_id: str,
    task_name: str,
    agent_id: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    duration_ms: int,
    errors: Optional[List[str]] = None,
    patterns: Optional[List[str]] = None,
) -> DoraTraceBlock:
    """
    Create and emit a DORA trace from the executor.

    Called by AgentExecutorService after task completion to record
    the execution trace. This is the primary integration point for
    the DORA Block system with the executor loop.

    Args:
        task_id: Unique task identifier
        task_name: Human-readable task name
        agent_id: Agent that executed the task
        inputs: Task inputs
        outputs: Task outputs
        duration_ms: Execution duration in milliseconds
        errors: List of error messages (if any)
        patterns: Patterns/strategies used during execution

    Returns:
        The created DoraTraceBlock
    """
    trace = DoraTraceBlock.create(
        task=f"{agent_id}:{task_name}",
        inputs={
            "task_id": task_id,
            "agent_id": agent_id,
            **inputs,
        },
        outputs=outputs,
        patterns_used=patterns or ["agent_execution"],
        duration_ms=duration_ms,
        errors=errors,
    )

    logger.info(
        "dora.executor_trace",
        trace_id=trace.trace_id,
        task=trace.task,
        duration_ms=duration_ms,
        status="error" if errors else "success",
    )

    return trace


# =============================================================================
# DORA Block Template for Codegen
# =============================================================================


def get_empty_dora_block_python() -> str:
    """
    Get an empty DORA block template for Python files.

    Used by codegen to inject the initial DORA block at generation time.
    The block will be auto-updated on first execution.
    """
    empty_trace = DoraTraceBlock(
        trace_id="<pending>",
        task="<pending_first_run>",
        timestamp="<auto-updates on execution>",
    )
    return format_dora_block_python(empty_trace)


# =============================================================================
# END MODULE
# =============================================================================

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "async",
        "dataclass",
        "debugging",
        "filesystem",
        "logging",
        "messaging",
        "metrics",
        "operations",
        "runtime-operations",
        "serialization",
    ],
    "keywords": [
        "async",
        "auto",
        "block",
        "create",
        "decorator",
        "dora",
        "emit",
        "empty",
    ],
    "business_value": "Provides the @l9_traced decorator and DORA block auto-update machinery.",
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
