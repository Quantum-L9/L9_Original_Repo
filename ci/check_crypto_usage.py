#!/usr/bin/env python3
"""
Check for banned/weak cryptography usage.

Checks:
- MD5 (banned except for protocol requirements)
- SHA1 (weak, review required)
- Deprecated TaskKind usage

Usage:
    python3 ci/check_crypto_usage.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__dora_meta__ = {
    "component_name": "CheckCryptoUsage",
    "module_version": "1.0.0",
    "status": "active",
}


def check_md5() -> tuple[bool, str]:
    """Check for banned MD5 usage."""
    result = subprocess.run(
        ["grep", "-r", "hashlib.md5",
         "--exclude-dir=.venv", "--exclude-dir=venv", "--exclude-dir=__pycache__",
         "--include=*.py", "."],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent
    )

    excludes = ["# MD5 required by protocol", "ci/check_", "# noqa", "current_work/", "tools/"]

    violations = []
    for line in result.stdout.splitlines():
        if not any(exc in line for exc in excludes):
            violations.append(line)

    if violations:
        msg = "❌ BANNED: MD5 usage detected!\n\n"
        msg += "\n".join(violations)
        msg += "\n\nUse hashlib.sha256() instead."
        msg += "\nIf MD5 is required by external protocol, add comment: # MD5 required by protocol"
        return False, msg

    return True, "✅ No banned MD5 usage found"


def check_sha1() -> tuple[bool, str]:
    """Check for weak SHA1 usage (warning only)."""
    result = subprocess.run(
        ["grep", "-r", "hashlib.sha1",
         "--exclude-dir=.venv", "--exclude-dir=venv", "--exclude-dir=__pycache__",
         "--include=*.py", "."],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent
    )

    excludes = ["hmac", "# SHA1 required by protocol", "ci/check_", "# noqa"]

    warnings = []
    for line in result.stdout.splitlines():
        if not any(exc in line for exc in excludes):
            warnings.append(line)

    if warnings:
        msg = "⚠️ WARNING: SHA1 usage detected (review required)\n\n"
        msg += "\n".join(warnings)
        msg += "\n\nConsider using SHA256 unless required by external protocol."
        return True, msg  # Warning only, don't fail

    return True, "✅ SHA1 check complete"


def check_deprecated_task_kind() -> tuple[bool, str]:
    """Check for deprecated TaskKind usage."""
    repo_root = Path(__file__).parent.parent

    # Check 1: Import of TaskKind from core.agents.schemas (DEPRECATED)
    result1 = subprocess.run(
        ["grep", "-rE", r"from core\.agents\.schemas import.*TaskKind",
         "--exclude-dir=.venv", "--exclude-dir=venv", "--exclude-dir=__pycache__", "--exclude-dir=current_work",
         "--include=*.py", "."],
        capture_output=True, text=True, cwd=repo_root
    )

    excludes = ["# TaskKind: backward compat", "ci/check_"]

    imports = []
    for line in result1.stdout.splitlines():
        if not any(exc in line for exc in excludes):
            imports.append(line)

    # Check 2: Usage of deprecated TaskKind enum values
    result2 = subprocess.run(
        ["grep", "-rE", r"TaskKind\.(CONVERSATION|QUERY|EXECUTION|RESEARCH)",
         "--exclude-dir=.venv", "--exclude-dir=venv", "--exclude-dir=__pycache__", "--exclude-dir=current_work",
         "--include=*.py", "."],
        capture_output=True, text=True, cwd=repo_root
    )

    excludes2 = excludes + ["core/agents/schemas.py", "tests/"]

    usage = []
    for line in result2.stdout.splitlines():
        if not any(exc in line for exc in excludes2):
            usage.append(line)

    failed = False
    msg = ""

    if imports:
        msg += "❌ DEPRECATED: TaskKind import from core.agents.schemas!\n\n"
        msg += "\n".join(imports)
        msg += "\n\n"
        failed = True

    if usage:
        msg += "❌ DEPRECATED: TaskKind enum values (CONVERSATION/QUERY/EXECUTION/RESEARCH)!\n\n"
        msg += "\n".join(usage)
        msg += "\n\n"
        failed = True

    if failed:
        msg += "=========================================\n"
        msg += "core.agents.schemas.TaskKind is DEPRECATED.\n"
        msg += "Use AgentType instead:\n"
        msg += "  from core.agents.schemas import AgentType\n\n"
        msg += "Migration mapping:\n"
        msg += "  TaskKind.CONVERSATION → AgentType.ASSISTANT\n"
        msg += "  TaskKind.QUERY        → AgentType.ANALYST\n"
        msg += "  TaskKind.EXECUTION    → AgentType.EXECUTOR\n"
        msg += "  TaskKind.RESEARCH     → AgentType.RESEARCHER\n"
        msg += "  TaskKind.COMMAND      → AgentType.OPERATOR\n\n"
        msg += "Parameter change:\n"
        msg += "  kind=TaskKind.X → agent_type=AgentType.Y\n\n"
        msg += "Note: core.schemas.tasks.TaskKind is NOT deprecated (internal routing)\n"
        msg += "      TaskKind.RESULT, TaskKind.ERROR, TaskKind.COMMAND from tasks.py are OK\n"
        msg += "Escape hatch: Add comment '# TaskKind: backward compat'"
        return False, msg

    return True, "✅ No deprecated TaskKind usage found"


def main() -> int:
    """Run all crypto checks."""
    print("🔐 Running crypto and deprecation checks...")
    print()

    exit_code = 0

    # MD5 check (fails on violation)
    ok, msg = check_md5()
    print(msg)
    if not ok:
        exit_code = 1
    print()

    # SHA1 check (warning only)
    ok, msg = check_sha1()
    print(msg)
    print()

    # TaskKind check (fails on violation)
    ok, msg = check_deprecated_task_kind()
    print(msg)
    if not ok:
        exit_code = 1

    return exit_code


__dora_footer__ = {
    "governance_level": "high",
    "compliance_required": True,
}

if __name__ == "__main__":
    sys.exit(main())
