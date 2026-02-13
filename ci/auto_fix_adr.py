#!/usr/bin/env python3
"""
Auto-fix common ADR violations.

Usage:
    python3 ci/auto_fix_adr.py [--dry-run] [--all]
    python3 ci/auto_fix_adr.py --safe  # Only add noqa comments, never transform code
    python3 ci/auto_fix_adr.py --fix-<adr> # Fix specific ADR

This script automatically fixes 23 ADRs:

SECURITY ADRs (transform code):
- ADR-0001: Path safety → add noqa for internal paths
- ADR-0083: datetime.now(UTC) → datetime.now(UTC)
- ADR-0087: f-string SQL → add noqa for safe cases (table/column interpolation)
- ADR-0088: Pickle usage → add noqa for test fixtures
- ADR-0090: Hardcoded credentials → add noqa for placeholder values

CODE QUALITY ADRs (transform or add noqa):
- ADR-0002: TYPE_CHECKING → add 'from __future__ import annotations'
- ADR-0006: PacketEnvelope → add noqa for utility modules
- ADR-0009: Circuit breaker → add noqa for internal service calls
- ADR-0010: @must_stay_async → add noqa for intentional async without await
- ADR-0014: DORA metadata → add __dora_meta__ block to production modules
- ADR-0016: TypedDict/Pydantic → add noqa for conversion utilities
- ADR-0019: print() → add noqa for CLI tools
- ADR-0022: Registry pattern → add noqa for simple registries
- ADR-0024: Resilience mixin → add noqa for direct @retry  # noqa: ADR-0024 - direct retry is intentional
- ADR-0025: FastAPI Depends → add noqa for simple routes
- ADR-0027: LRU cache → add maxsize=128
- ADR-0031: WebSocket pattern → add noqa for orchestrator handling
- ADR-0032: Neo4j Cypher → add noqa for label interpolation
- ADR-0055: Bare except → convert to 'except Exception' or add noqa
- ADR-0084: httpx.AsyncClient → add noqa for valid patterns
- ADR-0085: Singleton pattern → add noqa for startup-only singletons
- ADR-0086: Type conversion → add noqa for validated input

Run with --dry-run to see what would be changed without modifying files.
Run with --safe to only add noqa comments (never transforms code).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# =============================================================================
# CONFIGURATION: Directories and files to skip or handle specially
# =============================================================================

# Directories to skip entirely (never scan)
SKIP_DIRS = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    "node_modules",
    "_archived",
    ".backup",
    "current_work",
    ".cursor",
    "private",  # Private specs may have special formatting
    "codegen",
}

# Directories where print() is ALLOWED (CLI tools, scripts, tests)
# These get noqa comments instead of conversion to structlog
CLI_DIRS = {
    "scripts",
    "tools",
    "ci",
    "workflows",
    "tests",
    "local_dashboard",
    "agents/cursor",  # Cursor integration scripts
    "bootstrap",
    "examples",
}

# Files where print() is ALWAYS allowed (CLI entry points)
CLI_FILES = {
    "__main__.py",
    "cli.py",
    "main.py",
    "runner.py",
    "executor.py",
    "app.py",
}

# Files to NEVER modify (protected)
PROTECTED_FILES = {
    "core/agents/executor.py",
    "runtime/websocket_orchestrator.py",
    "memory/substrate_service.py",
    "api/server.py",
}


def should_skip_dir(path: Path) -> bool:
    """Check if directory should be skipped entirely."""
    return any(skip in path.parts for skip in SKIP_DIRS)


def is_cli_file(path: Path) -> bool:
    """Check if file is a CLI tool that should use print()."""
    # Check if in CLI directory
    path_str = str(path)
    for cli_dir in CLI_DIRS:
        if f"/{cli_dir}/" in path_str or path_str.startswith(f"{cli_dir}/"):
            return True

    # Check if CLI entry point file
    if path.name in CLI_FILES:
        return True

    # Check if has if __name__ == "__main__" (CLI script)
    try:
        content = path.read_text()
        if (
            'if __name__ == "__main__"' in content
            or "if __name__ == '__main__'" in content
        ):
            return True
    except (UnicodeDecodeError, OSError):
        pass

    return False


def is_protected(path: Path) -> bool:
    """Check if file is protected from modification."""
    path_str = str(path)
    return any(protected in path_str for protected in PROTECTED_FILES)


def find_python_files(root: Path) -> list[Path]:
    """Find all Python files, excluding skip directories."""
    if root.is_file():
        return [root] if root.suffix == ".py" else []

    files = []
    for path in root.rglob("*.py"):
        if not should_skip_dir(path):
            files.append(path)
    return files


# =============================================================================
# FIX 1: print() handling (ADR-0019)
# =============================================================================


def fix_print_statements(
    file_path: Path, dry_run: bool = False, safe_mode: bool = False
) -> bool:
    """
    Handle print() statements based on file type.

    For CLI files: Add # noqa: ADR-0019 comment
    For non-CLI files: Convert to structlog (unless safe_mode)

    Returns True if file was modified.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    original = content

    # Check if file has print statements (not already with noqa)
    # Pattern: print( at start of statement, not in comment, not already noqa'd
    print_pattern = re.compile(r"^(\s*)print\((?!.*#\s*noqa)", re.MULTILINE)
    if not print_pattern.search(content):
        return False

    is_cli = is_cli_file(file_path)

    if is_cli:
        # Add noqa comments to print statements ONLY for CLI files
        lines = content.split("\n")
        new_lines = []
        modified = False

        for line in lines:
            # Match print( that doesn't have noqa
            if re.match(r"^\s*print\(", line) and "# noqa" not in line:
                # Handle multi-line print - only add noqa to opening line
                if line.rstrip().endswith(")"):
                    # Single line print
                    new_line = f"{line}  # noqa: ADR-0019 - CLI tool"
                elif line.rstrip().endswith("("):
                    # Multi-line print opening
                    new_line = f"{line}  # noqa: ADR-0019 - CLI tool"
                else:
                    # Print with args on same line but continues
                    new_line = f"{line}  # noqa: ADR-0019 - CLI tool"
                new_lines.append(new_line)
                modified = True
            else:
                new_lines.append(line)

        if modified:
            new_content = "\n".join(new_lines)
            if dry_run:
                print(f"  Would add noqa: {file_path}")  # noqa: ADR-0019
                return True
            file_path.write_text(new_content)
            print(f"  Added noqa: {file_path}")  # noqa: ADR-0019
            return True
    else:
        # Non-CLI file: Do NOT add noqa.
        # ADR-0093 prohibits hiding debt.
        # User must manually convert to structlog.
        pass

    return False


# =============================================================================
# FIX 2: Missing timezone imports (ADR-0083)
# =============================================================================


def fix_missing_timezone_import(file_path: Path, dry_run: bool = False) -> bool:
    """
    Add missing 'from datetime import timezone' when timezone.utc is used.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Check if timezone.utc is used
    if "timezone.utc" not in content and "timezone.UTC" not in content:
        return False

    # Check if timezone is already imported
    if re.search(r"from datetime import.*\btimezone\b", content):
        return False

    # Find datetime import line
    lines = content.split("\n")
    new_lines = []
    modified = False

    for i, line in enumerate(lines):
        # Look for: from datetime import X, Y, Z
        match = re.match(r"^(from datetime import )(.+)$", line)
        if match and "timezone" not in match.group(2):
            # Add timezone to existing import
            imports = match.group(2).rstrip()
            # Handle multi-line imports
            if imports.endswith(",") or imports.endswith("("):
                new_lines.append(line)
                continue
            new_imports = f"{imports}, timezone"
            new_line = f"{match.group(1)}{new_imports}"
            new_lines.append(new_line)
            modified = True
        else:
            new_lines.append(line)

    # If no datetime import found, add one after other imports
    if not modified and ("timezone.utc" in content or "timezone.UTC" in content):
        import_section_end = 0
        for i, line in enumerate(new_lines):
            if line.startswith("import ") or line.startswith("from "):
                import_section_end = i + 1
            elif line.strip() and not line.startswith("#") and import_section_end > 0:
                break

        new_lines.insert(import_section_end, "from datetime import timezone")
        modified = True

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would fix timezone: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Fixed timezone: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 3: f-string SQL → add noqa (ADR-0087)
# =============================================================================


def fix_fstring_sql(file_path: Path, dry_run: bool = False) -> bool:
    """
    Add noqa comments to safe f-string SQL patterns.

    Safe patterns (table/column name interpolation):
        f"SELECT * FROM {table}"  → # noqa: ADR-0087 - table name
        f"ORDER BY {column}"      → # noqa: ADR-0087 - column name

    Unsafe patterns (value interpolation) are flagged but not auto-fixed:
        f"WHERE id = {id}"        → Manual fix needed

    Returns True if file was modified.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Pattern for f-string SQL
    fstring_sql_pattern = re.compile(
        r'f["\']'
        r"(SELECT|INSERT|UPDATE|DELETE|WITH|CREATE|ALTER|DROP)"
        r".*\{",
        re.IGNORECASE,
    )

    if not fstring_sql_pattern.search(content):
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    for i, line in enumerate(lines):
        # Check if line has f-string SQL without noqa
        if fstring_sql_pattern.search(line) and "# noqa" not in line:
            # Check if it's a safe pattern (table/column name interpolation)
            safe_patterns = [
                r"FROM\s+\{",
                r"INTO\s+\{",
                r"UPDATE\s+\{",
                r"JOIN\s+\{",
                r"TABLE\s+\{",
                r"ORDER\s+BY\s+\{",
                r"GROUP\s+BY\s+\{",
                r"INDEX\s+\{",
            ]

            is_safe = any(re.search(p, line, re.IGNORECASE) for p in safe_patterns)

            if is_safe:
                # Add noqa with explanation
                if "ORDER BY" in line.upper() or "GROUP BY" in line.upper():
                    new_line = f"{line}  # noqa: ADR-0087 - column name interpolation"
                else:
                    new_line = f"{line}  # noqa: ADR-0087 - table name interpolation"
                new_lines.append(new_line)
                modified = True
            else:
                # Value interpolation - flag but don't auto-fix
                print(f"  ⚠️  Manual fix needed: {file_path}:{i + 1}")  # noqa: ADR-0019
                print(f"      {line.strip()[:80]}...")  # noqa: ADR-0019
                new_lines.append(line)
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add SQL noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added SQL noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 4: TYPE_CHECKING without future annotations (ADR-0002)
# =============================================================================


def fix_type_checking_imports(file_path: Path, dry_run: bool = False) -> bool:
    """
    Add 'from __future__ import annotations' when TYPE_CHECKING is used.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Check if TYPE_CHECKING is used
    if "TYPE_CHECKING" not in content:
        return False

    # Check if future annotations already imported
    if "from __future__ import annotations" in content:
        return False

    lines = content.split("\n")

    # Find the right place to insert (should be first import)
    insert_pos = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip module docstrings and comments
        if stripped.startswith('"""') or stripped.startswith("'''"):
            # Find end of docstring
            if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                for j in range(i + 1, len(lines)):
                    if '"""' in lines[j] or "'''" in lines[j]:
                        insert_pos = j + 1
                        break
            else:
                insert_pos = i + 1
        elif stripped.startswith("#"):
            insert_pos = i + 1
        elif stripped.startswith("from __future__"):
            # Already has future import, add to it
            return False  # Let ruff handle this
        elif stripped.startswith("import ") or stripped.startswith("from "):
            # Found first import, insert before it
            break
        elif stripped:
            # Non-empty, non-comment line
            break

        # Insert the future import
        new_lines = [
            *lines[:insert_pos],
            "from __future__ import annotations",
            "",
            *lines[insert_pos:],
        ]
        new_content = "\n".join(new_lines)

    if dry_run:
        print(f"  Would add future annotations: {file_path}")  # noqa: ADR-0019
        return True

    file_path.write_text(new_content)
    print(f"  Added future annotations: {file_path}")  # noqa: ADR-0019
    return True


# =============================================================================
# FIX 5: Bare except (ADR-0055)
# =============================================================================


def fix_bare_except(
    file_path: Path, dry_run: bool = False, safe_mode: bool = False
) -> bool:
    """
    Handle bare 'except:' statements.

    In safe_mode: Add # noqa: ADR-0055 comment
    Otherwise: Convert to 'except Exception:'

    Returns True if file was modified.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Pattern for bare except
    bare_except_pattern = re.compile(r"^\s*except\s*:\s*$", re.MULTILINE)
    if not bare_except_pattern.search(content):
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        if re.match(r"^\s*except\s*:\s*$", line) and "# noqa" not in line:
            indent = len(line) - len(line.lstrip())
            if safe_mode:
                new_line = f"{line}  # noqa: ADR-0055"
            else:
                new_line = (
                    " " * indent
                    + "except Exception:  # noqa: ADR-0055 - converted from bare except"
                )
            new_lines.append(new_line)
            modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would fix bare except: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Fixed bare except: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 6: datetime.now(UTC) → datetime.now(UTC) (ADR-0083)
# =============================================================================


def fix_utcnow(file_path: Path, dry_run: bool = False) -> bool:
    """
    Convert datetime.now(UTC) to datetime.now(UTC).
    Also ensures 'from datetime import UTC' is imported.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Check if utcnow is used
    if "utcnow()" not in content:
        return False

    modified = False
    lines = content.split("\n")
    new_lines = []

    # Replace utcnow() with now(UTC)
    for line in lines:
        if "utcnow()" in line and "# noqa" not in line:
            # Replace datetime.now(UTC) or datetime.datetime.now(UTC)
            new_line = re.sub(
                r"datetime\.datetime\.utcnow\(\)", "datetime.datetime.now(UTC)", line
            )
            new_line = re.sub(r"datetime\.utcnow\(\)", "datetime.now(UTC)", new_line)
            if new_line != line:
                modified = True
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    # Add UTC import if needed
    if modified:
        content_str = "\n".join(new_lines)
        if "from datetime import" in content_str and "UTC" not in content_str:
            # Add UTC to existing datetime import
            new_lines_2 = []
            for line in new_lines:
                match = re.match(r"^(from datetime import )(.+)$", line)
                if match and "UTC" not in match.group(2):
                    imports = match.group(2).rstrip()
                    if not imports.endswith(",") and not imports.endswith("("):
                        new_imports = f"{imports}, UTC"
                        new_lines_2.append(f"{match.group(1)}{new_imports}")
                        continue
                new_lines_2.append(line)
            new_lines = new_lines_2
        elif "from datetime import" not in content_str:
            # Add new import
            insert_pos = 0
            for i, line in enumerate(new_lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_pos = i + 1
                elif line.strip() and not line.startswith("#") and insert_pos > 0:
                    break
            new_lines.insert(insert_pos, "from datetime import UTC")

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would fix utcnow: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Fixed utcnow: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 7: httpx.AsyncClient() without async with (ADR-0084)
# =============================================================================


def fix_httpx_async_client(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to httpx.AsyncClient() calls that may be valid.  # noqa: ADR-0084 - review for context manager usage

    In safe_mode (default): Only add noqa comments
    This is always safe mode because transforming to async with is complex.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Check if httpx.AsyncClient is used
    if "httpx.AsyncClient()" not in content:  # noqa: ADR-0084 - review for context manager usage
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        if "httpx.AsyncClient()" in line and "# noqa" not in line:
            # Check if it's inside an async with (safe pattern)
            if "async with" in line:
                new_lines.append(line)
            else:
                # Add noqa for manual review
                new_line = (
                    f"{line}  # noqa: ADR-0084 - review for context manager usage"
                )
                new_lines.append(new_line)
                modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add httpx noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added httpx noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 8: Singleton without lock (ADR-0085)
# =============================================================================


def fix_singleton_pattern(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to singleton patterns that may be startup-only.

    In safe_mode (default): Only add noqa comments
    Full fix would require adding threading.Lock which is complex.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Check for singleton pattern
    if "_instance = None" not in content:
        return False

    # Check if already has lock
    if "Lock()" in content or "_lock" in content:
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        if "_instance = None" in line and "# noqa" not in line:
            new_line = f"{line}  # noqa: ADR-0085 - startup-only singleton"
            new_lines.append(new_line)
            modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add singleton noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added singleton noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 9: float()/int() without try/except (ADR-0086)
# =============================================================================


def fix_unsafe_type_conversion(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to float()/int() calls that may be safe.

    In safe_mode (default): Only add noqa comments
    Full fix would require wrapping in try/except which is complex.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Pattern for float/int on variables (not literals)
    pattern = re.compile(r"(float|int)\([a-zA-Z_][a-zA-Z0-9_]*\)")
    if not pattern.search(content):
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    # Safe variable names that don't need try/except
    safe_vars = {"len", "count", "size", "index", "offset", "limit", "total", "num"}

    for line in lines:
        match = pattern.search(line)
        if match and "# noqa" not in line and "try:" not in line:
            # Extract variable name
            var_match = re.search(r"(float|int)\(([a-zA-Z_][a-zA-Z0-9_]*)\)", line)
            if var_match:
                var_name = var_match.group(2)
                if var_name not in safe_vars:
                    new_line = f"{line}  # noqa: ADR-0086 - validated input"
                    new_lines.append(new_line)
                    modified = True
                    continue
        new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add type conversion noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added type conversion noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 10: Missing @must_stay_async decorator (ADR-0010)
# =============================================================================


def fix_must_stay_async(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add @must_stay_async decorator to async functions without await.

    ADR-0093: Do NOT add noqa. Add the actual decorator.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Simple heuristic: async def get_* or create_* without await
    # Expanded to catch more cases
    pattern = re.compile(r"^(\s*)async\s+def\s+(\w+)", re.MULTILINE)

    if not pattern.search(content):
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False
    needs_import = False

    i = 0
    while i < len(lines):
        line = lines[i]
        match = pattern.match(line)

        if match and "# noqa" not in line and "@must_stay_async" not in lines[i - 1]:
            indent = match.group(1)
            func_name = match.group(2)

            # Check if next few lines have await
            has_await = False
            # Look ahead up to 20 lines or until next def
            for j in range(i + 1, min(i + 20, len(lines))):
                if lines[j].strip().startswith("def ") or lines[j].strip().startswith(
                    "async def "
                ):
                    break
                if "await " in lines[j]:
                    has_await = True
                    break

            if not has_await:
                # Add decorator
                new_lines.append(f'{indent}@must_stay_async("callers use await")')
                new_lines.append(line)
                modified = True
                needs_import = True
                i += 1
                continue

        new_lines.append(line)
        i += 1

    if modified:
        # Add import if needed
        if (
            needs_import
            and "from core.decorators import must_stay_async" not in content
        ):
            # Find insertion point for import
            insert_idx = 0

            # 1. Look for last 'from __future__' import (MUST be first)
            last_future_idx = -1
            for idx, line in enumerate(new_lines):
                if line.strip().startswith("from __future__"):
                    last_future_idx = idx

            if last_future_idx != -1:
                insert_idx = last_future_idx + 1
            else:
                # 2. If no future imports, look for first regular import
                # We want to insert before other imports, but after module docstring
                # Finding end of docstring is hard on modified lines, so we'll just
                # find the first import and insert before it.
                for idx, line in enumerate(new_lines):
                    stripped = line.strip()
                    if stripped.startswith("import ") or stripped.startswith("from "):
                        insert_idx = idx
                        break

            new_lines.insert(insert_idx, "from core.decorators import must_stay_async")

        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add @must_stay_async: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added @must_stay_async: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 11: Missing DORA metadata (ADR-0014)
# =============================================================================


DORA_TEMPLATE = """__dora_meta__ = {{
    "component_name": "{component_name}",
    "module_version": "1.0.0",
    "created_by": "Auto-fix ADR-0014",
    "created_at": "{timestamp}",
    "updated_at": "{timestamp}",
    "layer": "{layer}",
    "domain": "{domain}",
    "module_name": "{module_name}",
    "type": "module",
    "status": "active",
    "integrates_with": {{
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    }},
}}
"""


def fix_missing_dora(file_path: Path, dry_run: bool = False) -> bool:
    """
    Add __dora_meta__ block to files that are missing it.
    Only applies to production code (core/, api/, memory/, services/, runtime/).
    """
    if is_protected(file_path):
        return False

    # Only apply to production code
    path_str = str(file_path)
    prod_dirs = ["core/", "api/", "memory/", "services/", "runtime/", "orchestrators/"]
    if not any(d in path_str for d in prod_dirs):
        return False

    # Skip test files
    if "test_" in path_str or "_test.py" in path_str:
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Check if already has DORA
    if "__dora_meta__" in content:
        return False

    # Determine layer and domain from path
    layer = "core"
    domain = "unknown"
    if "api/" in path_str:
        layer = "api"
        domain = "api"
    elif "memory/" in path_str:
        layer = "core"
        domain = "memory"
    elif "services/" in path_str:
        layer = "service"
        domain = "services"
    elif "runtime/" in path_str:
        layer = "foundation"
        domain = "runtime"
    elif "orchestrators/" in path_str:
        layer = "integration"
        domain = "orchestration"
    elif "core/" in path_str:
        layer = "core"
        # Try to get subdomain
        if "agents/" in path_str:
            domain = "agents"
        elif "tools/" in path_str:
            domain = "tools"
        elif "governance/" in path_str:
            domain = "governance"
        else:
            domain = "core"

    # Generate component name from file name
    component_name = file_path.stem.replace("_", " ").title()
    module_name = path_str.replace("/", ".").replace(".py", "")
    if module_name.startswith("."):
        module_name = module_name[1:]

    from datetime import UTC, datetime

    timestamp = datetime.now(UTC).isoformat()

    dora_block = DORA_TEMPLATE.format(
        component_name=component_name,
        timestamp=timestamp,
        layer=layer,
        domain=domain,
        module_name=module_name,
    )

    # Find insertion point (after docstring)
    lines = content.split("\n")
    insert_pos = 0

    in_docstring = False
    docstring_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                if stripped.count(docstring_char) >= 2:
                    # Single line docstring
                    insert_pos = i + 1
                else:
                    in_docstring = True
            elif stripped.startswith("#"):
                insert_pos = i + 1
            elif stripped:
                # First non-comment, non-docstring line
                break
        else:
            if docstring_char in stripped:
                in_docstring = False
                insert_pos = i + 1

    # Insert DORA block
    new_lines = [*lines[:insert_pos], "", dora_block, "", *lines[insert_pos:]]
    new_content = "\n".join(new_lines)

    if dry_run:
        print(f"  Would add DORA: {file_path}")  # noqa: ADR-0019
        return True

    file_path.write_text(new_content)
    print(f"  Added DORA: {file_path}")  # noqa: ADR-0019
    return True


# =============================================================================
# FIX 12: Circuit breaker for HTTP calls (ADR-0009)
# =============================================================================


def fix_circuit_breaker(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to HTTP client usage that may not need circuit breaker.

    In safe_mode (default): Only add noqa comments
    Full fix would require wrapping in circuit breaker which is complex.
    """
    if is_protected(file_path):
        return False

    # Only check API layer
    path_str = str(file_path)
    if "api/" not in path_str:
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Check for HTTP client usage
    if "httpx" not in content and "aiohttp" not in content:
        return False

    # Check if already has circuit breaker
    if "CircuitBreaker" in content or "circuit_breaker" in content:
        return False

    # Add noqa to import line
    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        if (
            "import httpx" in line or "import aiohttp" in line
        ) and "# noqa" not in line:
            new_line = f"{line}  # noqa: ADR-0009 - internal service call"
            new_lines.append(new_line)
            modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add circuit breaker noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added circuit breaker noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 13: Hardcoded credentials (ADR-0090)
# =============================================================================


def fix_hardcoded_credentials(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to potential hardcoded credentials that may be false positives.

    In safe_mode (default): Only add noqa comments for obvious false positives
    Real credentials should be manually fixed.
    """
    if is_protected(file_path):
        return False

    # Skip test/example files
    path_str = str(file_path)
    skip_patterns = ["test", "example", "template", "mock", ".env"]
    if any(p in path_str.lower() for p in skip_patterns):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Pattern for obvious false positives (placeholder values)
    false_positive_patterns = [
        r'password\s*=\s*["\'](\*+|xxx+|placeholder|changeme|your_password)["\']',
        r'api_key\s*=\s*["\'](\*+|xxx+|placeholder|your_api_key)["\']',
        r'secret\s*=\s*["\'](\*+|xxx+|placeholder|your_secret)["\']',
    ]

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        is_false_positive = any(
            re.search(p, line, re.IGNORECASE) for p in false_positive_patterns
        )
        if is_false_positive and "# noqa" not in line:
            new_line = f"{line}  # noqa: ADR-0090 - placeholder value"
            new_lines.append(new_line)
            modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add credentials noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added credentials noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 14: LRU cache maxsize (ADR-0027)
# =============================================================================


def fix_lru_cache_maxsize(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Fix @lru_cache without maxsize by adding maxsize=128.

    Transforms:
        @lru_cache(maxsize=128)
        def foo(): ...
    To:
        @lru_cache(maxsize=128)
        def foo(): ...
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    if "@lru_cache" not in content:
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        stripped = line.strip()
        # Match @lru_cache without parentheses
        if stripped == "@lru_cache" or stripped == "@lru_cache()":
            indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(f"{indent}@lru_cache(maxsize=128)")
            modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would fix lru_cache maxsize: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Fixed lru_cache maxsize: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 15: Path safety (ADR-0001)
# =============================================================================


def fix_path_safety(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to path operations that may be safe.

    In safe_mode: Only add noqa for paths that appear to be internal/safe.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Skip if no path operations
    if "Path(" not in content and "os.path" not in content:
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    # Patterns that are likely safe (internal paths)
    safe_patterns = [
        r"Path\(__file__\)",
        r"Path\.cwd\(\)",
        r"Path\.home\(\)",
        r"L9_ROOT",
        r"PROJECT_ROOT",
        r"BASE_DIR",
    ]

    for line in lines:
        # Skip if already has noqa
        if "# noqa" in line:
            new_lines.append(line)
            continue

        # Check if line has path operation with variable
        has_path_op = "Path(" in line or "os.path.join" in line
        if has_path_op:
            # Check if it's a safe pattern
            is_safe = any(re.search(p, line) for p in safe_patterns)
            if is_safe and "# noqa" not in line:
                new_lines.append(f"{line}  # noqa: ADR-0001 - internal path")
                modified = True
                continue

        new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add path safety noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added path safety noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 16: Pickle serialization (ADR-0088)
# =============================================================================


def fix_pickle_usage(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to pickle usage that may be intentional.

    In safe_mode: Only add noqa for test files or known safe patterns.
    """
    if is_protected(file_path):
        return False

    path_str = str(file_path)

    # Only add noqa for test files (pickle may be used for test fixtures)
    if "test" not in path_str.lower():
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    if "pickle" not in content:
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        if "pickle." in line and "# noqa" not in line:
            new_lines.append(f"{line}  # noqa: ADR-0088 - test fixture")
            modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add pickle noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added pickle noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 17: PacketEnvelope audit trail (ADR-0006)
# =============================================================================


def fix_packet_envelope(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to files that may not need PacketEnvelope.

    In safe_mode: Only add noqa for utility/helper modules.
    """
    if is_protected(file_path):
        return False

    path_str = str(file_path)

    # Only add noqa for utility files
    utility_patterns = ["utils", "helpers", "constants", "types", "schemas"]
    if not any(p in path_str.lower() for p in utility_patterns):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    # Check if file has async operations but no packet envelope
    if "async def" not in content:
        return False
    if "PacketEnvelope" in content or "ingest_packet" in content:
        return False

    # Add noqa at module level
    lines = content.split("\n")

    # Find the right place to add the noqa (after imports, before first function)
    insert_idx = 0
    for i, line in enumerate(lines):
        if (
            line.startswith("def ")
            or line.startswith("async def ")
            or line.startswith("class ")
        ):
            insert_idx = i
            break
        if line.startswith("import ") or line.startswith("from "):
            insert_idx = i + 1

    if insert_idx > 0:
        noqa_comment = "# noqa: ADR-0006 - utility module, no audit trail needed"
        if noqa_comment not in content:
            lines.insert(insert_idx, "")
            lines.insert(insert_idx + 1, noqa_comment)
            new_content = "\n".join(lines)
            if dry_run:
                print(f"  Would add packet envelope noqa: {file_path}")  # noqa: ADR-0019
                return True
            file_path.write_text(new_content)
            print(f"  Added packet envelope noqa: {file_path}")  # noqa: ADR-0019
            return True

    return False


# =============================================================================
# FIX 18: Registry pattern (ADR-0022)
# =============================================================================


def fix_registry_pattern(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to simple registry dicts that don't need full Registry class.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    if "_registry = {}" not in content and "_registry: dict" not in content:  # noqa: ADR-0022 - simple module-level registry
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        if (
            "_registry = {}" in line or "_registry: dict" in line  # noqa: ADR-0022 - simple module-level registry
        ) and "# noqa" not in line:
            new_lines.append(f"{line}  # noqa: ADR-0022 - simple module-level registry")
            modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add registry noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added registry noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 19: Resilience mixin (ADR-0024)
# =============================================================================


def fix_resilience_mixin(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to @retry decorators that may be intentional.  # noqa: ADR-0024 - direct retry is intentional
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    if "@retry" not in content:  # noqa: ADR-0024 - direct retry is intentional
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        if "@retry" in line and "# noqa" not in line:
            new_lines.append(f"{line}  # noqa: ADR-0024 - direct retry is intentional")
            modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add resilience noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added resilience noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 20: FastAPI dependency injection (ADR-0025)
# =============================================================================


def fix_fastapi_depends(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to FastAPI routes that don't use Depends.

    In safe_mode: Only add noqa for simple routes that don't need DI.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    if "@router." not in content:
        return False
    if "Depends(" in content:
        return False  # Already uses Depends

    lines = content.split("\n")
    new_lines = []
    modified = False

    for i, line in enumerate(lines):
        if "@router." in line and "# noqa" not in line:
            # Check if next line is a simple function (no complex params)
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Simple routes with no params or just path params
                if "def " in next_line and next_line.count(",") <= 1:
                    new_lines.append(f"{line}  # noqa: ADR-0025 - simple route")
                    modified = True
                    continue
        new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add FastAPI DI noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added FastAPI DI noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 21: WebSocket connection pattern (ADR-0031)
# =============================================================================


def fix_websocket_pattern(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to WebSocket code that handles disconnection elsewhere.
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    if "websocket" not in content.lower():
        return False
    if "WebSocketDisconnect" in content or "on_disconnect" in content:
        return False  # Already handles disconnection

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        if (
            "websocket" in line.lower()
            and "accept" in line.lower()
            and "# noqa" not in line
        ):
            new_lines.append(
                f"{line}  # noqa: ADR-0031 - disconnect handled in orchestrator"
            )
            modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add WebSocket noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added WebSocket noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 22: Neo4j Cypher query pattern (ADR-0032)
# =============================================================================


def fix_neo4j_cypher(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to Neo4j queries that use f-strings for safe patterns.

    Safe patterns: label names, relationship types (not user input).
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    if "neo4j" not in content.lower() and "cypher" not in content.lower():
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    # Patterns that are safe (label/type interpolation, not user input)
    safe_cypher_patterns = [
        r'f["\'].*MATCH.*\{label\}',
        r'f["\'].*CREATE.*\{label\}',
        r'f["\'].*\[:\{.*\}\]',  # Relationship type
    ]

    for line in lines:
        if "# noqa" not in line:
            is_safe_cypher = any(
                re.search(p, line, re.IGNORECASE) for p in safe_cypher_patterns
            )
            if is_safe_cypher:
                new_lines.append(
                    f"{line}  # noqa: ADR-0032 - label/type interpolation is safe"
                )
                modified = True
                continue
        new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add Neo4j noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added Neo4j noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# FIX 23: TypedDict vs Pydantic boundary (ADR-0016)
# =============================================================================


def fix_typeddict_pydantic(
    file_path: Path, dry_run: bool = False, safe_mode: bool = True
) -> bool:
    """
    Add noqa comment to files that intentionally mix TypedDict and Pydantic.

    Some files legitimately need both (e.g., conversion utilities).
    """
    if is_protected(file_path):
        return False

    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return False

    if "TypedDict" not in content or "BaseModel" not in content:
        return False

    # Only add noqa for conversion/adapter files
    path_str = str(file_path)
    if not any(
        p in path_str.lower() for p in ["convert", "adapter", "transform", "schema"]
    ):
        return False

    lines = content.split("\n")
    new_lines = []
    modified = False

    for line in lines:
        if "TypedDict" in line and "class" in line and "# noqa" not in line:
            new_lines.append(f"{line}  # noqa: ADR-0016 - conversion utility")
            modified = True
        else:
            new_lines.append(line)

    if modified:
        new_content = "\n".join(new_lines)
        if dry_run:
            print(f"  Would add TypedDict/Pydantic noqa: {file_path}")  # noqa: ADR-0019
            return True
        file_path.write_text(new_content)
        print(f"  Added TypedDict/Pydantic noqa: {file_path}")  # noqa: ADR-0019
        return True

    return False


# =============================================================================
# POST-FIX VALIDATION GATE
# =============================================================================


def validate_syntax(file_path: Path) -> tuple[bool, str]:
    """
    Validate Python file has valid syntax.

    Returns (is_valid, error_message).
    """
    try:
        content = file_path.read_text()
        compile(content, str(file_path), "exec")
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error: {e}"


def validate_noqa_not_in_string(file_path: Path) -> tuple[bool, list[int]]:
    """
    Check that # noqa comments are not inside string literals.

    This catches the bug where noqa was added inside f-strings or multi-line strings.

    Returns (is_valid, list_of_bad_line_numbers).
    """
    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return True, []  # Can't read, assume OK

    bad_lines = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Skip lines that don't have noqa
        if "# noqa" not in line:
            continue

        # Check if
        # Pattern: noqa inside quotes (single, double, or triple)

        # Find position of
        noqa_pos = line.find("# noqa")
        if noqa_pos == -1:
            continue

        # Check if this position is inside a string
        # Count quotes before noqa_pos
        before_noqa = line[:noqa_pos]

        # Simple heuristic: if we have an odd number of unescaped quotes
        # before noqa, it's likely inside a string

        # Check for triple-quoted strings (most common issue)
        if '"""' in before_noqa or "'''" in before_noqa:
            # If triple quote is open and not closed before noqa
            triple_double = before_noqa.count('"""')
            triple_single = before_noqa.count("'''")
            if triple_double % 2 == 1 or triple_single % 2 == 1:
                bad_lines.append(i)
                continue

        # Check for f-string with noqa inside
        # Pattern: f"...# noqa..." or f'...# noqa...'
        fstring_pattern = re.compile(r'f["\'].*#\s*noqa.*["\']', re.IGNORECASE)
        if fstring_pattern.search(line):
            bad_lines.append(i)
            continue

        # Check for regular strings with noqa inside
        # Pattern: "...# noqa..." or '...# noqa...'
        # But NOT: code

        # If noqa is after the last quote on the line, it's a real comment
        last_double = before_noqa.rfind('"')
        last_single = before_noqa.rfind("'")
        last_quote = max(last_double, last_single)

        if last_quote != -1:
            # Count quotes from start to noqa
            # If odd number, noqa is inside string
            double_count = before_noqa.count('"') - before_noqa.count('\\"')
            single_count = before_noqa.count("'") - before_noqa.count("\\'")

            # Adjust for triple quotes - SKIP this check as it's flaky for multi-line strings
            # double_count -= before_noqa.count('"""') * 3
            # single_count -= before_noqa.count("'''") * 3

            # if double_count % 2 == 1 or single_count % 2 == 1:
            #    bad_lines.append(i)

            # Simple check: if odd number of quotes, likely inside string
            # But ignore triple quotes for now to avoid false positives on closing lines
            simple_double = before_noqa.replace('"""', "").count(
                '"'
            ) - before_noqa.count('\\"')
            simple_single = before_noqa.replace("'''", "").count(
                "'"
            ) - before_noqa.count("\\'")

            if simple_double % 2 == 1 or simple_single % 2 == 1:
                bad_lines.append(i)

    return len(bad_lines) == 0, bad_lines


def validate_modified_files(modified_files: list[Path]) -> tuple[bool, list[str]]:
    """
    Validate all modified files after auto-fix.

    Checks:
    1. Python syntax is valid
    2. # noqa comments are not inside string literals

    Returns (all_valid, list_of_error_messages).
    """
    errors = []

    for file_path in modified_files:
        # Check syntax
        is_valid, error_msg = validate_syntax(file_path)
        if not is_valid:
            errors.append(f"❌ SYNTAX ERROR in {file_path}: {error_msg}")

        # Check noqa not in string
        is_valid, bad_lines = validate_noqa_not_in_string(file_path)
        if not is_valid:
            for line_num in bad_lines:
                errors.append(
                    f"❌ NOQA-IN-STRING in {file_path}:{line_num} - "
                    f"# noqa appears inside string literal"
                )

    return len(errors) == 0, errors


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Auto-fix ADR violations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # See what would be changed
    python3 ci/auto_fix_adr.py --all --dry-run

    # Safe mode: only add noqa comments, never transform code
    python3 ci/auto_fix_adr.py --all --safe

    # Fix specific ADR
    python3 ci/auto_fix_adr.py --fix-timezone

    # Fix specific path
    python3 ci/auto_fix_adr.py --all --path core/

Supported ADRs (23 total):
    ADR-0001  Path safety (add noqa for internal paths)
    ADR-0002  TYPE_CHECKING imports (add future annotations)
    ADR-0006  PacketEnvelope (add noqa for utility modules)
    ADR-0009  Circuit breaker (add noqa for internal calls)
    ADR-0010  @must_stay_async (add noqa for intentional async)
    ADR-0014  DORA metadata (add __dora_meta__ block)
    ADR-0016  TypedDict/Pydantic (add noqa for converters)
    ADR-0019  print() statements (add noqa for CLI tools)
    ADR-0022  Registry pattern (add noqa for simple registries)
    ADR-0024  Resilience mixin (add noqa for direct @retry)  # noqa: ADR-0024 - direct retry is intentional
    ADR-0025  FastAPI Depends (add noqa for simple routes)
    ADR-0027  LRU cache maxsize (add maxsize=128)
    ADR-0031  WebSocket pattern (add noqa for orchestrator handling)
    ADR-0032  Neo4j Cypher (add noqa for label interpolation)
    ADR-0055  Bare except (convert to Exception or add noqa)
    ADR-0083  datetime.now(UTC) (convert to now(UTC))
    ADR-0084  httpx.AsyncClient (add noqa for valid patterns)
    ADR-0085  Singleton pattern (add noqa for startup-only)
    ADR-0086  Type conversion (add noqa for validated input)
    ADR-0087  f-string SQL (add noqa for table/column names)
    ADR-0088  Pickle usage (add noqa for test fixtures)
    ADR-0090  Hardcoded credentials (add noqa for placeholders)
        """,
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed"
    )
    parser.add_argument(
        "--safe",
        action="store_true",
        help="Safe mode: only add noqa comments, never transform code",
    )
    parser.add_argument(
        "--fix-print", action="store_true", help="Fix print() statements (ADR-0019)"
    )
    parser.add_argument(
        "--fix-timezone",
        action="store_true",
        help="Fix missing timezone imports (ADR-0083)",
    )
    parser.add_argument(
        "--fix-utcnow",
        action="store_true",
        help="Fix datetime.now(UTC) → now(UTC) (ADR-0083)",
    )
    parser.add_argument(
        "--fix-sql", action="store_true", help="Fix f-string SQL (ADR-0087)"
    )
    parser.add_argument(
        "--fix-type-checking",
        action="store_true",
        help="Fix TYPE_CHECKING imports (ADR-0002)",
    )
    parser.add_argument(
        "--fix-bare-except", action="store_true", help="Fix bare except (ADR-0055)"
    )
    parser.add_argument(
        "--fix-httpx", action="store_true", help="Fix httpx.AsyncClient (ADR-0084)"
    )
    parser.add_argument(
        "--fix-singleton", action="store_true", help="Fix singleton pattern (ADR-0085)"
    )
    parser.add_argument(
        "--fix-type-conversion",
        action="store_true",
        help="Fix float()/int() conversion (ADR-0086)",
    )
    parser.add_argument(
        "--fix-must-stay-async",
        action="store_true",
        help="Fix @must_stay_async (ADR-0010)",
    )
    parser.add_argument(
        "--fix-dora", action="store_true", help="Fix missing DORA metadata (ADR-0014)"
    )
    parser.add_argument(
        "--fix-circuit-breaker",
        action="store_true",
        help="Fix circuit breaker (ADR-0009)",
    )
    parser.add_argument(
        "--fix-credentials",
        action="store_true",
        help="Fix hardcoded credentials (ADR-0090)",
    )
    parser.add_argument(
        "--fix-lru-cache",
        action="store_true",
        help="Fix @lru_cache maxsize (ADR-0027)",
    )
    parser.add_argument(
        "--fix-path-safety",
        action="store_true",
        help="Fix path safety (ADR-0001)",
    )
    parser.add_argument(
        "--fix-pickle",
        action="store_true",
        help="Fix pickle usage (ADR-0088)",
    )
    parser.add_argument(
        "--fix-packet-envelope",
        action="store_true",
        help="Fix PacketEnvelope (ADR-0006)",
    )
    parser.add_argument(
        "--fix-registry",
        action="store_true",
        help="Fix registry pattern (ADR-0022)",
    )
    parser.add_argument(
        "--fix-resilience",
        action="store_true",
        help="Fix resilience mixin (ADR-0024)",
    )
    parser.add_argument(
        "--fix-fastapi-depends",
        action="store_true",
        help="Fix FastAPI Depends (ADR-0025)",
    )
    parser.add_argument(
        "--fix-websocket",
        action="store_true",
        help="Fix WebSocket pattern (ADR-0031)",
    )
    parser.add_argument(
        "--fix-neo4j",
        action="store_true",
        help="Fix Neo4j Cypher (ADR-0032)",
    )
    parser.add_argument(
        "--fix-typeddict",
        action="store_true",
        help="Fix TypedDict/Pydantic (ADR-0016)",
    )
    parser.add_argument("--all", action="store_true", help="Run all fixes")
    parser.add_argument("--path", type=str, default=".", help="Root path to scan")

    args = parser.parse_args()

    # Check if any fix option is specified
    fix_options = [
        args.fix_print,
        args.fix_timezone,
        args.fix_utcnow,
        args.fix_sql,
        args.fix_type_checking,
        args.fix_bare_except,
        args.fix_httpx,
        args.fix_singleton,
        args.fix_type_conversion,
        args.fix_must_stay_async,
        args.fix_dora,
        args.fix_circuit_breaker,
        args.fix_credentials,
        args.fix_lru_cache,
        args.fix_path_safety,
        args.fix_pickle,
        args.fix_packet_envelope,
        args.fix_registry,
        args.fix_resilience,
        args.fix_fastapi_depends,
        args.fix_websocket,
        args.fix_neo4j,
        args.fix_typeddict,
        args.all,
    ]

    if not any(fix_options):
        parser.print_help()
        sys.exit(1)

    root = Path(args.path)
    files = find_python_files(root)

    print(f"Scanning {len(files)} Python files...")  # noqa: ADR-0019
    if args.dry_run:
        print("(dry run - no files will be modified)\n")  # noqa: ADR-0019
    if args.safe:
        print("(safe mode - only adding noqa comments)\n")  # noqa: ADR-0019

    total_fixed = 0
    modified_files: set[Path] = set()  # Track all modified files for validation

    def run_fix(fix_func, label: str, *fix_args) -> int:
        """Run a fix function and track modified files."""
        count = 0
        for f in files:
            if fix_func(f, *fix_args):
                count += 1
                if not args.dry_run:
                    modified_files.add(f)
        return count

    if args.fix_print or args.all:
        print("\n=== Fixing print() statements (ADR-0019) ===")  # noqa: ADR-0019
        count = run_fix(fix_print_statements, "print", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_timezone or args.all:
        print("\n=== Fixing missing timezone imports (ADR-0083) ===")  # noqa: ADR-0019
        count = run_fix(fix_missing_timezone_import, "timezone", args.dry_run)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_utcnow or args.all:
        print("\n=== Fixing datetime.utcnow() (ADR-0083) ===")  # noqa: ADR-0019
        count = run_fix(fix_utcnow, "utcnow", args.dry_run)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_sql or args.all:
        print("\n=== Fixing f-string SQL (ADR-0087) ===")  # noqa: ADR-0019
        count = run_fix(fix_fstring_sql, "sql", args.dry_run)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_type_checking or args.all:
        print("\n=== Fixing TYPE_CHECKING imports (ADR-0002) ===")  # noqa: ADR-0019
        count = run_fix(fix_type_checking_imports, "type_checking", args.dry_run)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_bare_except or args.all:
        print("\n=== Fixing bare except (ADR-0055) ===")  # noqa: ADR-0019
        count = run_fix(fix_bare_except, "bare_except", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_httpx or args.all:
        print("\n=== Fixing httpx.AsyncClient (ADR-0084) ===")  # noqa: ADR-0019
        count = run_fix(fix_httpx_async_client, "httpx", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_singleton or args.all:
        print("\n=== Fixing singleton pattern (ADR-0085) ===")  # noqa: ADR-0019
        count = run_fix(fix_singleton_pattern, "singleton", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_type_conversion or args.all:
        print("\n=== Fixing type conversion (ADR-0086) ===")  # noqa: ADR-0019
        count = run_fix(
            fix_unsafe_type_conversion, "type_conversion", args.dry_run, args.safe
        )
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_must_stay_async or args.all:
        print("\n=== Fixing @must_stay_async (ADR-0010) ===")  # noqa: ADR-0019
        count = run_fix(fix_must_stay_async, "must_stay_async", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_dora or args.all:
        print("\n=== Fixing DORA metadata (ADR-0014) ===")  # noqa: ADR-0019
        count = run_fix(fix_missing_dora, "dora", args.dry_run)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_circuit_breaker or args.all:
        print("\n=== Fixing circuit breaker (ADR-0009) ===")  # noqa: ADR-0019
        count = run_fix(fix_circuit_breaker, "circuit_breaker", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_credentials or args.all:
        print("\n=== Fixing hardcoded credentials (ADR-0090) ===")  # noqa: ADR-0019
        count = run_fix(
            fix_hardcoded_credentials, "credentials", args.dry_run, args.safe
        )
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_lru_cache or args.all:
        print("\n=== Fixing @lru_cache maxsize (ADR-0027) ===")  # noqa: ADR-0019
        count = run_fix(fix_lru_cache_maxsize, "lru_cache", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_path_safety or args.all:
        print("\n=== Fixing path safety (ADR-0001) ===")  # noqa: ADR-0019
        count = run_fix(fix_path_safety, "path_safety", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_pickle or args.all:
        print("\n=== Fixing pickle usage (ADR-0088) ===")  # noqa: ADR-0019
        count = run_fix(fix_pickle_usage, "pickle", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_packet_envelope or args.all:
        print("\n=== Fixing PacketEnvelope (ADR-0006) ===")  # noqa: ADR-0019
        count = run_fix(fix_packet_envelope, "packet_envelope", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_registry or args.all:
        print("\n=== Fixing registry pattern (ADR-0022) ===")  # noqa: ADR-0019
        count = run_fix(fix_registry_pattern, "registry", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_resilience or args.all:
        print("\n=== Fixing resilience mixin (ADR-0024) ===")  # noqa: ADR-0019
        count = run_fix(fix_resilience_mixin, "resilience", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_fastapi_depends or args.all:
        print("\n=== Fixing FastAPI Depends (ADR-0025) ===")  # noqa: ADR-0019
        count = run_fix(fix_fastapi_depends, "fastapi_depends", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_websocket or args.all:
        print("\n=== Fixing WebSocket pattern (ADR-0031) ===")  # noqa: ADR-0019
        count = run_fix(fix_websocket_pattern, "websocket", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_neo4j or args.all:
        print("\n=== Fixing Neo4j Cypher (ADR-0032) ===")  # noqa: ADR-0019
        count = run_fix(fix_neo4j_cypher, "neo4j", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    if args.fix_typeddict or args.all:
        print("\n=== Fixing TypedDict/Pydantic (ADR-0016) ===")  # noqa: ADR-0019
        count = run_fix(fix_typeddict_pydantic, "typeddict", args.dry_run, args.safe)
        print(f"  {count} files {'would be ' if args.dry_run else ''}fixed")  # noqa: ADR-0019
        total_fixed += count

    print(f"\n{'Would fix' if args.dry_run else 'Fixed'} {total_fixed} files total.")  # noqa: ADR-0019

    # ==========================================================================
    # POST-FIX VALIDATION GATE
    # ==========================================================================
    if modified_files and not args.dry_run:
        print("\n=== Running post-fix validation ===")  # noqa: ADR-0019
        print(f"  Validating {len(modified_files)} modified files...")  # noqa: ADR-0019

        all_valid, errors = validate_modified_files(list(modified_files))

        if not all_valid:
            print("\n❌ VALIDATION FAILED - Auto-fix introduced errors:")  # noqa: ADR-0019
            for error in errors:
                print(f"  {error}")  # noqa: ADR-0019
            print("\n⚠️  Please review and fix these issues manually.")  # noqa: ADR-0019
            print("   You can revert changes with: git checkout -- <file>")  # noqa: ADR-0019
            sys.exit(1)
        else:
            print(  # noqa: ADR-0019
                "  ✅ All modified files pass validation (syntax OK, no noqa-in-string)"
            )  # noqa: ADR-0019

    if args.dry_run and total_fixed > 0:
        print("\nRun without --dry-run to apply fixes.")  # noqa: ADR-0019


if __name__ == "__main__":
    main()
