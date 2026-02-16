#!/usr/bin/env python3
"""
Check for hardcoded credentials (ADR-0090).

Scans for:
- PostgreSQL connection strings with real passwords
- AWS Access Keys (AKIA...)
- API keys (64-char hex strings)

Usage:
    python3 ci/check_hardcoded_credentials.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__dora_meta__ = {
    "component_name": "CheckHardcodedCredentials",
    "module_version": "1.0.0",
    "status": "active",
}


def run_grep(pattern: str, file_types: list[str], extra_excludes: list[str] | None = None) -> str:
    """Run grep with standard exclusions."""
    cmd = ["grep", "-r", pattern]
    # Exclude directories at grep level for performance
    cmd.extend(["--exclude-dir=.venv", "--exclude-dir=venv", "--exclude-dir=.git", "--exclude-dir=__pycache__"])
    for ft in file_types:
        cmd.extend(["--include", ft])
    cmd.append(".")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    output = result.stdout

    # Additional post-filter exclusions
    excludes = [".env"]
    if extra_excludes:
        excludes.extend(extra_excludes)

    lines = []
    for line in output.splitlines():
        skip = False
        for exc in excludes:
            if exc in line:
                skip = True
                break
        if not skip:
            lines.append(line)

    return "\n".join(lines)


def check_postgres_credentials() -> tuple[bool, str]:
    """Check for hardcoded PostgreSQL credentials."""
    # Find PostgreSQL URLs with passwords
    output = run_grep(
        r"postgresql://.*:.*@",
        ["*.py", "*.md", "*.sh", "*.yaml", "*.yml"],
    )

    # Filter out known safe patterns
    safe_patterns = [
        "user:pass@", "user:password@", "postgres:postgres@",
        "test:test@", "hypergraph:hypergraph@", "l9:l9test@",
        "$(", "${", "$[A-Z]", "YOUR_", "CHANGEME",
        "...", "***", ":PASSWORD@", ":password@",
        ":devpass@", ":l9_password@", "POSTGRES_PASSWORD@",
        "REAL_PASSWORD_HERE", "❌", "ci.yml",
        "ci/check_", "adr-enforcement.yaml", "current_work/",
        "test_user:test_pass", "scripts/vps/", "deploy/"
    ]

    violations = []
    for line in output.splitlines():
        if not line:
            continue
        is_safe = any(p in line for p in safe_patterns)
        if not is_safe:
            violations.append(line)

    if violations:
        return False, "❌ HARDCODED POSTGRES CREDENTIALS:\n" + "\n".join(violations)
    return True, ""


def check_aws_keys() -> tuple[bool, str]:
    """Check for AWS Access Keys."""
    result = subprocess.run(
        ["grep", "-rE", r"AKIA[0-9A-Z]{16}",
         "--exclude-dir=.venv", "--exclude-dir=venv", "--exclude-dir=.git", "--exclude-dir=__pycache__",
         "--include=*.py", "--include=*.sh", "--include=*.yaml", "."],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent
    )

    lines = []
    for line in result.stdout.splitlines():
        if ".env" not in line:
            lines.append(line)

    if lines:
        return False, "❌ AWS ACCESS KEYS:\n" + "\n".join(lines)
    return True, ""


def check_api_keys() -> tuple[bool, str]:
    """Check for hardcoded API keys (64-char hex strings)."""
    result = subprocess.run(
        ["grep", "-rE", r'(API_KEY|api_key|L9_API_KEY).*"[a-f0-9]{64}"',
         "--exclude-dir=.venv", "--exclude-dir=venv", "--exclude-dir=.git", "--exclude-dir=__pycache__",
         "--include=*.py", "--include=*.md", "--include=*.sh", "--include=*.yaml", "--include=*.yml", "."],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent
    )

    safe_patterns = [".env", "YOUR_", "❌", "checksum", "hash", "ci/check_", "current_work/", "scripts/development/"]

    lines = []
    for line in result.stdout.splitlines():
        if not any(p in line for p in safe_patterns):
            lines.append(line)

    if lines:
        return False, "❌ HARDCODED API KEYS:\n" + "\n".join(lines)
    return True, ""


def main() -> int:
    """Run all credential checks."""
    print("🔐 Checking for hardcoded credentials (ADR-0090)...")

    failed = False

    ok, msg = check_postgres_credentials()
    if not ok:
        print(msg)
        failed = True

    ok, msg = check_aws_keys()
    if not ok:
        print(msg)
        failed = True

    ok, msg = check_api_keys()
    if not ok:
        print(msg)
        failed = True

    if failed:
        print()
        print("=========================================")
        print("ADR-0090: No hardcoded credentials allowed")
        print("Use: ${VARIABLE} or $(VARIABLE) or placeholders")
        return 1

    print("✅ No hardcoded credentials found")
    return 0


__dora_footer__ = {
    "governance_level": "medium",
    "compliance_required": True,
}

if __name__ == "__main__":
    sys.exit(main())
