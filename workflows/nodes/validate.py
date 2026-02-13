"""
Validate Node — Run validation checks on deployed files.

Supports: py_compile, exists, grep, shell, import checks.
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Validate",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:45:56Z",
    "updated_at": "2026-01-31T22:21:53Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "validate",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workflows.nodes.__init__"],
    },
}
# ============================================================================

import asyncio
import time
from datetime import datetime
from pathlib import Path

import structlog

from workflows.state import StepResult, ValidationCheck, WorkflowState

logger = structlog.get_logger(__name__)


async def _run_shell(cmd: str, cwd: str) -> tuple[int, str, str]:
    """Run shell command asynchronously."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode(), stderr.decode()


@must_stay_async("callers use await")
async def validate_node(state: WorkflowState) -> dict:
    """
    Run validation checks on deployed files.

    Check types:
        - py_compile: Python syntax validation
        - exists: File existence check
        - grep: Pattern presence check
        - shell: Custom shell command
        - import: Python import check

    Args:
        state: Current workflow state with validation_checks

    Returns:
        State update with validation_passed, results
    """
    start_time = time.time()
    step_id = "validate"

    checks = state.get("validation_checks", [])
    working_dir = state.get("working_directory", str(Path.cwd()))

    # If no explicit checks, auto-generate from deployed files
    if not checks:
        checks = _auto_generate_checks(state)

    logger.info("validate.start", check_count=len(checks))

    outputs: list[str] = []
    errors: list[str] = []

    for check in checks:
        check_type = check.get("check_type", "exists")
        files = check.get("files", [])

        if check_type == "py_compile":
            # Python syntax check
            py_files = [f for f in files if f.endswith(".py")]
            if py_files:
                cmd = f"python3 -m py_compile {' '.join(py_files)}"
                code, _, stderr = await _run_shell(cmd, working_dir)

                if code != 0:
                    errors.append(f"py_compile failed: {stderr}")
                    logger.error("validate.py_compile_failed", error=stderr)
                else:
                    outputs.append(f"✓ py_compile passed ({len(py_files)} files)")
                    logger.info("validate.py_compile_passed", count=len(py_files))

        elif check_type == "exists":
            # File existence check
            missing = []
            for f in files:
                path = Path(working_dir) / f
                if not path.exists():
                    missing.append(f)

            if missing:
                errors.append(f"Files missing: {', '.join(missing)}")
                logger.error("validate.files_missing", files=missing)
            else:
                outputs.append(f"✓ All {len(files)} files exist")
                logger.info("validate.files_exist", count=len(files))

        elif check_type == "grep":
            # Pattern presence check
            pattern = check.get("pattern", "")
            for f in files:
                cmd = f'grep -q "{pattern}" "{f}"'
                code, _, _ = await _run_shell(cmd, working_dir)

                if code != 0:
                    errors.append(f"Pattern '{pattern}' not found in {f}")
                    logger.error("validate.grep_failed", pattern=pattern, file=f)

            if not errors:
                outputs.append(f"✓ Pattern '{pattern}' found in all files")

        elif check_type == "shell":
            # Custom shell command
            command = check.get("command", "")
            code, _, stderr = await _run_shell(command, working_dir)

            if code != 0:
                errors.append(
                    f"Shell check failed: {stderr or 'exit code ' + str(code)}"
                )
                logger.error(
                    "validate.shell_failed", command=command[:50], error=stderr
                )
            else:
                outputs.append(f"✓ Shell check passed: {command[:50]}...")
                logger.info("validate.shell_passed", command=command[:50])

        elif check_type == "import":
            # Python import check
            for f in files:
                if f.endswith(".py"):
                    # Convert path to module: services/foo.py → services.foo
                    module = f.replace("/", ".").replace(".py", "")
                    cmd = f'python3 -c "import {module}"'
                    code, _stdout, stderr = await _run_shell(cmd, working_dir)

                    if code != 0:
                        errors.append(f"Import failed: {module}: {stderr}")
                        logger.error(
                            "validate.import_failed", module=module, error=stderr
                        )
                    else:
                        outputs.append(f"✓ Import passed: {module}")

    duration_ms = (time.time() - start_time) * 1000
    success = len(errors) == 0

    result = StepResult(
        step_id=step_id,
        success=success,
        output="\n".join(outputs),
        error="; ".join(errors) if errors else None,
        duration_ms=duration_ms,
        artifacts={"checks_passed": len(outputs), "checks_failed": len(errors)},
        timestamp=datetime.now().isoformat(),
    )

    logger.info(
        "validate.complete",
        success=success,
        passed=len(outputs),
        failed=len(errors),
        duration_ms=duration_ms,
    )

    return {
        "validation_passed": success,
        "results": [result],
        "current_phase": "report" if success else "done",
        "should_continue": success,
        "error": result["error"],
        "messages": [
            {
                "role": "assistant",
                "content": f"Validation {'passed' if success else 'failed'}",
            }
        ],
    }


def _auto_generate_checks(state: WorkflowState) -> list[ValidationCheck]:
    """Auto-generate validation checks from deployed files."""
    checks: list[ValidationCheck] = []

    all_files = state.get("files_copied", []) + state.get("files_modified", [])

    py_files = [f for f in all_files if f.endswith(".py")]
    sql_files = [f for f in all_files if f.endswith(".sql")]

    if py_files:
        # py_compile check
        checks.append(
            ValidationCheck(
                check_type="py_compile",
                files=py_files,
                pattern=None,
                command=None,
            )
        )

        # Existence check
        checks.append(
            ValidationCheck(
                check_type="exists",
                files=py_files,
                pattern=None,
                command=None,
            )
        )

    if sql_files:
        checks.append(
            ValidationCheck(
                check_type="exists",
                files=sql_files,
                pattern=None,
                command=None,
            )
        )

    return checks


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-019",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "filesystem",
        "logging",
        "messaging",
        "operations",
        "service",
        "workflows",
    ],
    "keywords": ["checks", "validate"],
    "business_value": "Utility module for validate",
    "last_modified": "2026-01-31T22:21:53Z",
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
