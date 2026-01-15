#!/usr/bin/env python3
"""
L9 API Signature Mismatch Audit v1.0

Scans codebase for API signature mismatches between function calls and definitions.
Detects:
  - Missing required kwargs
  - Deprecated parameter names
  - Enum .value access on string returns
  - httpx API version mismatches

Usage:
  python scripts/audit/audit_api_signatures.py
  python scripts/audit/audit_api_signatures.py --fix  # Auto-fix where safe
"""

import ast
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


class SeverityLevel(str, Enum):
    CRITICAL = "critical"  # Will cause runtime errors
    HIGH = "high"  # Likely to cause errors
    MEDIUM = "medium"  # May cause issues
    LOW = "low"  # Style/deprecation


@dataclass
class SignatureMismatch:
    """Represents an API signature mismatch."""

    filepath: str
    line: int
    function_name: str
    issue: str
    severity: SeverityLevel
    fix_suggestion: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class AuditResult:
    """Result of API signature audit."""

    total_files_scanned: int = 0
    total_mismatches: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    mismatches: List[SignatureMismatch] = field(default_factory=list)
    fixed_count: int = 0
    errors: List[str] = field(default_factory=list)


# =============================================================================
# SIGNATURE RULES
# =============================================================================

# Known function signatures with required kwargs
REQUIRED_KWARGS = {
    "build_governance_context": [
        "caller_id",
        "role",
        "scope",
        "project_id",
        "allowed_scopes",
    ],
    "build_scope_project_filter": ["param_idx"],  # ctx is positional
}

# Deprecated parameter names -> new names
DEPRECATED_PARAMS = {
    "RateLimiter": {
        "max_requests": "request_limit",
        "window_seconds": "request_window_seconds",
    },
}

# Deprecated method names -> new names
DEPRECATED_METHODS = {
    "is_blocked_for_failed_auth": "is_auth_blocked",
}

# Functions that return str, not enum (so .value is wrong)
STRING_RETURN_FUNCTIONS = {
    "get_state": "CircuitBreaker.get_state() returns str, not enum",
}


# =============================================================================
# AST ANALYSIS
# =============================================================================


class SignatureAnalyzer(ast.NodeVisitor):
    """AST visitor that checks for API signature mismatches."""

    def __init__(self, filepath: str, source: str):
        self.filepath = filepath
        self.source = source
        self.mismatches: List[SignatureMismatch] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Check function/method calls for signature issues."""
        func_name = self._get_func_name(node)
        if not func_name:
            self.generic_visit(node)
            return

        # Check required kwargs
        if func_name in REQUIRED_KWARGS:
            self._check_required_kwargs(node, func_name)

        # Check deprecated params (for class instantiation)
        if func_name in DEPRECATED_PARAMS:
            self._check_deprecated_params(node, func_name)

        # Check .value access on string-returning functions
        if isinstance(node.func, ast.Attribute):
            self._check_value_access(node)

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check for .value access on non-enum returns."""
        if node.attr == "value":
            # Check if parent is a Call to a string-returning function
            if isinstance(node.value, ast.Call):
                call_node = node.value
                func_name = self._get_func_name(call_node)
                if func_name in STRING_RETURN_FUNCTIONS:
                    self.mismatches.append(
                        SignatureMismatch(
                            filepath=self.filepath,
                            line=node.lineno,
                            function_name=func_name,
                            issue=f"{STRING_RETURN_FUNCTIONS[func_name]} - remove .value",
                            severity=SeverityLevel.CRITICAL,
                            fix_suggestion=f"Remove .value - {func_name}() already returns str",
                            auto_fixable=True,
                        )
                    )

        self.generic_visit(node)

    def _get_func_name(self, node: ast.Call) -> Optional[str]:
        """Extract function name from call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _check_required_kwargs(self, node: ast.Call, func_name: str) -> None:
        """Check if call has all required kwargs."""
        required = REQUIRED_KWARGS[func_name]
        kwarg_names = [kw.arg for kw in node.keywords if kw.arg]

        missing = [r for r in required if r not in kwarg_names]
        if missing:
            self.mismatches.append(
                SignatureMismatch(
                    filepath=self.filepath,
                    line=node.lineno,
                    function_name=func_name,
                    issue=f"Missing required kwargs: {missing}",
                    severity=SeverityLevel.CRITICAL,
                    fix_suggestion=f"Add missing kwargs: {', '.join(missing)}",
                    auto_fixable=False,
                )
            )

    def _check_deprecated_params(self, node: ast.Call, func_name: str) -> None:
        """Check for deprecated parameter names."""
        deprecated = DEPRECATED_PARAMS[func_name]
        kwarg_names = [kw.arg for kw in node.keywords if kw.arg]

        for old_name, new_name in deprecated.items():
            if old_name in kwarg_names:
                self.mismatches.append(
                    SignatureMismatch(
                        filepath=self.filepath,
                        line=node.lineno,
                        function_name=func_name,
                        issue=f"Deprecated param '{old_name}' -> use '{new_name}'",
                        severity=SeverityLevel.HIGH,
                        fix_suggestion=f"Replace {old_name}= with {new_name}=",
                        auto_fixable=True,
                    )
                )

    def _check_value_access(self, node: ast.Call) -> None:
        """Check for incorrect .value access patterns."""
        # This is handled in visit_Attribute
        pass


def analyze_file(filepath: Path) -> Tuple[List[SignatureMismatch], Optional[str]]:
    """Analyze single file for signature mismatches."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(filepath))

        analyzer = SignatureAnalyzer(str(filepath), source)
        analyzer.visit(tree)

        return analyzer.mismatches, None
    except SyntaxError as e:
        return [], f"Syntax error in {filepath}: {e}"
    except Exception as e:
        return [], f"Error analyzing {filepath}: {e}"


def find_value_on_get_state(filepath: Path) -> List[SignatureMismatch]:
    """
    Specifically find .get_state().value patterns.
    Uses regex for more reliable detection than AST for chained calls.
    """
    import re

    mismatches = []
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")

        # Pattern: .get_state().value
        pattern = r"\.get_state\(\)\.value"

        for i, line in enumerate(source.splitlines(), 1):
            if re.search(pattern, line):
                mismatches.append(
                    SignatureMismatch(
                        filepath=str(filepath),
                        line=i,
                        function_name="get_state",
                        issue="get_state() returns str, not enum - .value is invalid",
                        severity=SeverityLevel.CRITICAL,
                        fix_suggestion="Remove .value from .get_state().value",
                        auto_fixable=True,
                    )
                )
    except Exception:
        pass

    return mismatches


def find_httpx_app_param(filepath: Path) -> List[SignatureMismatch]:
    """
    Find httpx AsyncClient(app=...) patterns (deprecated in 0.28+).
    """
    import re

    mismatches = []
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")

        # Pattern: AsyncClient(app= or AsyncClient( ... app=
        pattern = r"AsyncClient\([^)]*app="

        for i, line in enumerate(source.splitlines(), 1):
            if re.search(pattern, line) and "ASGITransport" not in line:
                mismatches.append(
                    SignatureMismatch(
                        filepath=str(filepath),
                        line=i,
                        function_name="AsyncClient",
                        issue="httpx 0.28+ requires ASGITransport - app= is deprecated",
                        severity=SeverityLevel.HIGH,
                        fix_suggestion="Use AsyncClient(transport=ASGITransport(app=app), ...)",
                        auto_fixable=False,
                    )
                )
    except Exception:
        pass

    return mismatches


# =============================================================================
# MAIN AUDIT
# =============================================================================


def run_api_signature_audit(
    repo_root: Path = REPO_ROOT,
    skip_dirs: List[str] = None,
    skip_files: List[str] = None,
    fix: bool = False,
) -> AuditResult:
    """
    Run API signature mismatch audit.

    Args:
        repo_root: Repository root path
        skip_dirs: Directories to skip
        skip_files: Files to skip (basenames)
        fix: Auto-fix issues where possible

    Returns:
        AuditResult with all findings
    """
    skip_dirs = skip_dirs or [
        "_archived",
        "__pycache__",
        ".git",
        "venv",
        "node_modules",
        ".venv",
        "current_work",
        "docs",
    ]
    skip_files = skip_files or [
        "audit_api_signatures.py"
    ]  # Skip self to avoid false positives
    result = AuditResult()

    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(repo_root):
        # Filter out skip directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for f in files:
            if f.endswith(".py") and f not in skip_files:
                python_files.append(Path(root) / f)

    result.total_files_scanned = len(python_files)

    # Analyze each file
    for filepath in python_files:
        # AST analysis
        mismatches, error = analyze_file(filepath)
        if error:
            result.errors.append(error)
        result.mismatches.extend(mismatches)

        # Regex-based checks for patterns AST misses
        result.mismatches.extend(find_value_on_get_state(filepath))
        result.mismatches.extend(find_httpx_app_param(filepath))

    # Deduplicate (same file+line+issue)
    seen = set()
    unique_mismatches = []
    for m in result.mismatches:
        key = (m.filepath, m.line, m.issue)
        if key not in seen:
            seen.add(key)
            unique_mismatches.append(m)
    result.mismatches = unique_mismatches

    # Count by severity
    result.total_mismatches = len(result.mismatches)
    result.critical_count = len(
        [m for m in result.mismatches if m.severity == SeverityLevel.CRITICAL]
    )
    result.high_count = len(
        [m for m in result.mismatches if m.severity == SeverityLevel.HIGH]
    )
    result.medium_count = len(
        [m for m in result.mismatches if m.severity == SeverityLevel.MEDIUM]
    )
    result.low_count = len(
        [m for m in result.mismatches if m.severity == SeverityLevel.LOW]
    )

    # Auto-fix if requested
    if fix:
        result.fixed_count = auto_fix_mismatches(result.mismatches)

    return result


def auto_fix_mismatches(mismatches: List[SignatureMismatch]) -> int:
    """
    Auto-fix auto-fixable mismatches.
    Returns count of fixed items.
    """
    fixed = 0
    files_to_fix: Dict[str, List[SignatureMismatch]] = {}

    # Group by file
    for m in mismatches:
        if m.auto_fixable:
            files_to_fix.setdefault(m.filepath, []).append(m)

    for filepath, file_mismatches in files_to_fix.items():
        try:
            content = Path(filepath).read_text()

            for m in sorted(file_mismatches, key=lambda x: -x.line):  # Bottom-up
                if ".get_state().value" in m.issue:
                    # Fix: remove .value from .get_state().value
                    content = content.replace(".get_state().value", ".get_state()")
                    fixed += 1

            Path(filepath).write_text(content)
        except Exception as e:
            print(f"Failed to fix {filepath}: {e}")

    return fixed


def print_report(result: AuditResult) -> None:
    """Print audit report to stdout."""
    print("=" * 70)
    print("L9 API SIGNATURE MISMATCH AUDIT v1.0")
    print("=" * 70)
    print(f"Files scanned: {result.total_files_scanned}")
    print(f"Mismatches found: {result.total_mismatches}")
    print(f"  Critical: {result.critical_count}")
    print(f"  High: {result.high_count}")
    print(f"  Medium: {result.medium_count}")
    print(f"  Low: {result.low_count}")

    if result.fixed_count:
        print(f"Auto-fixed: {result.fixed_count}")

    if result.errors:
        print(f"\nErrors: {len(result.errors)}")
        for err in result.errors[:5]:
            print(f"  - {err}")

    if result.mismatches:
        print("\n" + "-" * 70)
        print("FINDINGS:")
        print("-" * 70)

        for m in sorted(
            result.mismatches, key=lambda x: (x.severity.value, x.filepath, x.line)
        ):
            severity_icon = {
                SeverityLevel.CRITICAL: "🔴",
                SeverityLevel.HIGH: "🟠",
                SeverityLevel.MEDIUM: "🟡",
                SeverityLevel.LOW: "🔵",
            }.get(m.severity, "⚪")

            print(
                f"\n{severity_icon} [{m.severity.value.upper()}] {m.filepath}:{m.line}"
            )
            print(f"   Function: {m.function_name}")
            print(f"   Issue: {m.issue}")
            if m.fix_suggestion:
                print(f"   Fix: {m.fix_suggestion}")
    else:
        print("\n✅ No API signature mismatches found!")

    print("\n" + "=" * 70)


def main():
    """CLI entrypoint."""
    import argparse

    parser = argparse.ArgumentParser(description="L9 API Signature Mismatch Audit")
    parser.add_argument("--fix", action="store_true", help="Auto-fix where safe")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--quiet", action="store_true", help="Only show summary")

    args = parser.parse_args()

    result = run_api_signature_audit(fix=args.fix)

    if args.json:
        import json
        from dataclasses import asdict

        print(json.dumps(asdict(result), indent=2, default=str))
    elif args.quiet:
        print(
            f"Mismatches: {result.total_mismatches} (Critical: {result.critical_count}, High: {result.high_count})"
        )
    else:
        print_report(result)

    # Exit code based on critical findings
    if result.critical_count > 0:
        sys.exit(1)
    elif result.high_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
