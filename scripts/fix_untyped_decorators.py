#!/usr/bin/env python3
"""
Fix Untyped Decorators Script
=============================

Identifies and fixes decorators that cause mypy's "untyped-decorator" error.

This error occurs when a decorator doesn't properly preserve the type signature
of the decorated function. The fix uses ParamSpec and TypeVar to maintain
type information.

Usage:
    # Identify all untyped decorators
    python scripts/fix_untyped_decorators.py scan

    # Preview fixes (dry run)
    python scripts/fix_untyped_decorators.py fix --dry-run

    # Apply fixes to specific file
    python scripts/fix_untyped_decorators.py fix --file core/singleton_auto_registry.py

    # Apply fixes
    python scripts/fix_untyped_decorators.py fix

    # Verify fixes work
    python scripts/fix_untyped_decorators.py verify

Version: 1.1.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Fix Untyped Decorators",
    "module_version": "1.1.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T08:58:01Z",
    "updated_at": "2026-01-25T08:58:45Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "fix_untyped_decorators",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple


@dataclass
class DecoratorIssue:
    """Represents an untyped decorator that needs fixing."""

    file_path: Path
    line_number: int
    decorator_name: str
    function_name: str
    current_signature: str
    issue_type: str  # 'returns_callable' | 'no_return_type' | 'uses_any'
    fix_strategy: str = ""  # How to fix it


class DecoratorFix(NamedTuple):
    """A fix to apply to a decorator."""

    file_path: Path
    old_code: str
    new_code: str
    description: str
    imports_needed: list[str]


# Known good patterns (already properly typed)
PROPERLY_TYPED_PATTERNS = [
    r"Callable\[\[F\], F\]",  # Already uses TypeVar
    r"Callable\[P, R\]",  # Already uses ParamSpec
    r"Callable\[P, T\]",
    r"Callable\[ParamSpec",
]


def scan_for_untyped_decorators(
    root_path: Path,
    exclude_dirs: set[str] | None = None,
    single_file: Path | None = None,
) -> list[DecoratorIssue]:
    """
    Scan codebase for decorators that could cause untyped-decorator errors.
    """
    if exclude_dirs is None:
        exclude_dirs = {
            ".venv",
            "venv",
            "__pycache__",
            ".git",
            "node_modules",
            "_archived",
            "readme",
            "current_work",  # Skip work-in-progress
            "codegen",  # Skip templates
        }

    issues: list[DecoratorIssue] = []

    files_to_check = [single_file] if single_file else list(root_path.rglob("*.py"))

    for py_file in files_to_check:
        # Skip excluded directories
        if any(excl in py_file.parts for excl in exclude_dirs):
            continue

        # Skip directories that happen to have .py in the name
        if not py_file.is_file():
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"  Warning: Could not parse {py_file}: {e}")
            continue

        file_issues = analyze_file_decorators(tree, py_file, content)
        issues.extend(file_issues)

    return issues


def analyze_file_decorators(
    tree: ast.AST, file_path: Path, content: str
) -> list[DecoratorIssue]:
    """Analyze all decorators in a file."""
    issues = []
    lines = content.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        # Check if this looks like a decorator or decorator factory
        issue = check_decorator_typing(node, file_path, lines, content)
        if issue:
            issues.append(issue)

    return issues


def check_decorator_typing(
    node: ast.FunctionDef, file_path: Path, lines: list[str], content: str
) -> DecoratorIssue | None:
    """Check if a function is a decorator with untyped return."""

    # Get the function source for detailed analysis
    try:
        func_source = ast.get_source_segment(content, node) or ""
    except Exception:
        func_source = ""

    # Skip if already properly typed
    for pattern in PROPERLY_TYPED_PATTERNS:
        if re.search(pattern, func_source):
            return None

    # Check for decorator factory pattern (nested decorator function)
    has_nested_decorator = False
    for child in ast.walk(node):
        if isinstance(child, ast.FunctionDef) and child.name in (
            "decorator",
            "wrapper",
            "_decorator",
            "_wrapper",
        ):
            has_nested_decorator = True
            break

    if not has_nested_decorator:
        return None  # Not a decorator factory

    # Get signature
    sig = lines[node.lineno - 1] if node.lineno <= len(lines) else ""

    # Determine issue type
    returns_annotation = node.returns

    if returns_annotation is None:
        # No return type at all
        issue_type = "no_return_type"
        fix_strategy = "add_paramspec_return"
    elif isinstance(returns_annotation, (ast.Name, ast.Subscript)):
        # Has return type - check if it loses type info
        ret_str = ast.unparse(returns_annotation) if hasattr(ast, "unparse") else ""
        if (
            "Callable" in ret_str
            and "ParamSpec" not in ret_str
            and "[P," not in ret_str
        ):
            issue_type = "returns_callable"
            fix_strategy = "add_paramspec"
        else:
            return None  # Likely fine
    else:
        return None

    return DecoratorIssue(
        file_path=file_path,
        line_number=node.lineno,
        decorator_name=node.name,
        function_name=node.name,
        current_signature=sig.strip(),
        issue_type=issue_type,
        fix_strategy=fix_strategy,
    )


def generate_fix_for_file(
    file_path: Path, issues: list[DecoratorIssue]
) -> list[DecoratorFix]:
    """Generate all fixes for a single file."""
    if not issues:
        return []

    content = file_path.read_text(encoding="utf-8")
    fixes = []
    imports_needed = set()

    for issue in issues:
        fix = generate_single_fix(issue, content)
        if fix:
            fixes.append(fix)
            imports_needed.update(fix.imports_needed)

    return fixes


def generate_single_fix(issue: DecoratorIssue, content: str) -> DecoratorFix | None:
    """Generate a fix for a single decorator issue."""
    lines = content.splitlines()

    # Get the decorator function source
    start_line = issue.line_number - 1
    end_line = find_function_end(lines, start_line)

    if end_line is None:
        return None

    old_code = "\n".join(lines[start_line : end_line + 1])
    imports_needed = []

    # Apply the fix based on strategy
    if issue.fix_strategy == "add_paramspec":
        new_code = fix_with_paramspec(old_code, issue.decorator_name)
        imports_needed = ["ParamSpec", "TypeVar"]
    elif issue.fix_strategy == "add_paramspec_return":
        new_code = fix_add_return_type(old_code, issue.decorator_name)
        imports_needed = ["ParamSpec", "TypeVar"]
    else:
        return None

    if new_code == old_code:
        return None

    return DecoratorFix(
        file_path=issue.file_path,
        old_code=old_code,
        new_code=new_code,
        description=f"Add ParamSpec typing to {issue.decorator_name}",
        imports_needed=imports_needed,
    )


def find_function_end(lines: list[str], start_line: int) -> int | None:
    """Find the end line of a function definition."""
    if start_line >= len(lines):
        return None

    # Get indentation of the function def
    first_line = lines[start_line]
    base_indent = len(first_line) - len(first_line.lstrip())

    for i in range(start_line + 1, len(lines)):
        line = lines[i]
        if not line.strip():  # Empty line
            continue
        if line.strip().startswith("#"):  # Comment
            continue
        current_indent = len(line) - len(line.lstrip())
        # If we hit a line with same or less indentation that's not empty
        if current_indent <= base_indent:
            return i - 1

    return len(lines) - 1


def fix_with_paramspec(code: str, func_name: str) -> str:
    """
    Fix a decorator that returns plain Callable by adding ParamSpec typing.

    Transforms inner decorator:
        def decorator(func: Callable) -> Callable:
    To:
        def decorator(func: Callable[P, R]) -> Callable[P, R]:
    """
    # Replace inner decorator func parameter type
    code = re.sub(
        r"def\s+(decorator|wrapper|_decorator|_wrapper)\s*\(\s*func\s*:\s*Callable\s*\)\s*->\s*Callable\s*:",
        r"def \1(func: Callable[P, R]) -> Callable[P, R]:",
        code,
    )

    # Also handle Callable[..., Any] pattern
    code = re.sub(
        r"func\s*:\s*Callable\[\.\.\.,\s*Any\]",
        "func: Callable[P, R]",
        code,
    )

    return re.sub(
        r"->\s*Callable\[\.\.\.,\s*Any\]",
        "-> Callable[P, R]",
        code,
    )



def fix_add_return_type(code: str, func_name: str) -> str:
    """
    Add return type to a decorator factory.

    Transforms:
        def factory(...):
            def decorator(func):
    To:
        def factory(...) -> Callable[[Callable[P, R]], Callable[P, R]]:
            def decorator(func: Callable[P, R]) -> Callable[P, R]:
    """
    # First, add typing to inner decorator
    code = re.sub(
        r"def\s+(decorator|wrapper|_decorator|_wrapper)\s*\(\s*func\s*:\s*Callable\s*\)\s*:",
        r"def \1(func: Callable[P, R]) -> Callable[P, R]:",
        code,
    )

    # Handle case where inner decorator has no type hints
    return re.sub(
        r"def\s+(decorator|wrapper|_decorator|_wrapper)\s*\(\s*func\s*\)\s*:",
        r"def \1(func: Callable[P, R]) -> Callable[P, R]:",
        code,
    )



def check_and_add_imports(file_path: Path, imports_needed: set[str]) -> str | None:
    """Check if imports are needed and return the import statement."""
    content = file_path.read_text(encoding="utf-8")

    missing_imports = []
    for imp in imports_needed:
        if imp not in content:
            missing_imports.append(imp)

    if not missing_imports:
        return None

    # Check if there's already a typing import
    if "from typing import" in content:
        return f"# Add to existing typing import: {', '.join(missing_imports)}"

    return f"from typing import {', '.join(sorted(missing_imports))}"


def add_paramspec_definitions(content: str) -> str:
    """Add P and R definitions if needed."""
    if "P = ParamSpec" in content:
        return content

    # Find the right place to add (after imports)
    lines = content.splitlines()
    insert_idx = 0

    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_idx = i + 1
        elif line.strip() and not line.startswith("#") and not line.startswith('"""'):
            if insert_idx > 0:
                break

    # Add blank line + definitions
    definitions = [
        "",
        "P = ParamSpec('P')",
        "R = TypeVar('R')",
    ]

    lines = lines[:insert_idx] + definitions + lines[insert_idx:]
    return "\n".join(lines)


def apply_fixes(fixes: list[DecoratorFix], dry_run: bool = True) -> int:
    """Apply all fixes to files."""
    applied = 0

    # Group fixes by file
    fixes_by_file: dict[Path, list[DecoratorFix]] = {}
    for fix in fixes:
        fixes_by_file.setdefault(fix.file_path, []).append(fix)

    for file_path, file_fixes in fixes_by_file.items():
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        # Collect all needed imports
        all_imports_needed: set[str] = set()
        for fix in file_fixes:
            all_imports_needed.update(fix.imports_needed)

        # Apply code fixes
        for fix in file_fixes:
            if fix.old_code in content:
                content = content.replace(fix.old_code, fix.new_code, 1)
                applied += 1
                print(f"  {'[DRY-RUN] ' if dry_run else ''}Fixed: {fix.description}")
                print(
                    f"    File: {fix.file_path}:{file_fixes[0].old_code.split(chr(10))[0]}"
                )

        # Add imports if needed
        if all_imports_needed and content != original_content:
            # Check what's already imported
            missing = []
            for imp in all_imports_needed:
                if f" {imp}" not in content and f",{imp}" not in content:
                    if (imp == "ParamSpec" and "ParamSpec" not in content) or (
                        imp == "TypeVar" and "TypeVar" not in content
                    ):
                        missing.append(imp)

            if missing:
                # Add to existing typing import or create new one
                if "from typing import" in content:
                    # Find the typing import line and extend it
                    content = re.sub(
                        r"(from typing import )(.*?)(\n)",
                        lambda m: f"{m.group(1)}{m.group(2)}, {', '.join(sorted(missing))}{m.group(3)}",
                        content,
                        count=1,
                    )
                    print(f"    Added imports: {', '.join(missing)}")
                else:
                    # Add new import line after __future__
                    import_line = f"from typing import {', '.join(sorted(missing))}\n"
                    if "from __future__" in content:
                        content = re.sub(
                            r"(from __future__ import [^\n]+\n)",
                            rf"\1{import_line}",
                            content,
                            count=1,
                        )
                    else:
                        content = import_line + content
                    print(f"    Added import: from typing import {', '.join(missing)}")

            # Add ParamSpec/TypeVar definitions if needed
            if "Callable[P, R]" in content and "P = ParamSpec" not in content:
                content = add_paramspec_definitions(content)
                print("    Added P = ParamSpec('P') and R = TypeVar('R') definitions")

        if not dry_run and content != original_content:
            file_path.write_text(content, encoding="utf-8")

    return applied


def run_mypy_check(root_path: Path, files: list[Path] | None = None) -> tuple[int, str]:
    """Run mypy with untyped-decorator check enabled."""
    cmd = [
        sys.executable,
        "-m",
        "mypy",
        "--disallow-untyped-decorators",
        "--show-error-codes",
        "--no-error-summary",
    ]

    if files:
        cmd.extend(str(f) for f in files)
    else:
        cmd.append(str(root_path))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = result.stdout + result.stderr
        error_count = output.count("untyped-decorator")
        return error_count, output
    except subprocess.TimeoutExpired:
        return -1, "mypy timed out"
    except FileNotFoundError:
        return -1, "mypy not found"


def main():
    parser = argparse.ArgumentParser(
        description="Fix untyped decorators for mypy compliance"
    )
    parser.add_argument(
        "command",
        choices=["scan", "fix", "verify"],
        help="Command to run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview fixes without applying them",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Root path to scan (default: current directory)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Single file to fix",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    print("Untyped Decorator Fixer v1.1")
    print("=" * 40)
    print(f"Root path: {args.path}")
    print()

    if args.command == "scan":
        print("Scanning for untyped decorators...")
        single_file = args.file.resolve() if args.file else None
        issues = scan_for_untyped_decorators(args.path, single_file=single_file)

        if not issues:
            print("\n✅ No untyped decorator issues found!")
            return 0

        print(f"\n⚠️  Found {len(issues)} potential untyped decorator(s):\n")

        for issue in issues:
            print(f"  {issue.file_path}:{issue.line_number}")
            print(f"    Function: {issue.decorator_name}")
            print(f"    Issue: {issue.issue_type}")
            print(f"    Strategy: {issue.fix_strategy}")
            print(f"    Signature: {issue.current_signature[:60]}...")
            print()

        return len(issues)

    if args.command == "fix":
        print("Scanning for untyped decorators...")
        single_file = args.file.resolve() if args.file else None
        issues = scan_for_untyped_decorators(args.path, single_file=single_file)

        if not issues:
            print("\n✅ No untyped decorator issues found!")
            return 0

        print(f"\nGenerating fixes for {len(issues)} issue(s)...")

        all_fixes = []
        for issue in issues:
            fix = generate_single_fix(
                issue, issue.file_path.read_text(encoding="utf-8")
            )
            if fix:
                all_fixes.append(fix)

        if not all_fixes:
            print("\n⚠️  No automatic fixes could be generated.")
            print("Manual intervention may be required.")
            return 1

        dry_run = args.dry_run or args.file is None
        if args.file is None:
            print(
                "\nNote: Use --file to apply fixes to specific file, or --dry-run to preview"
            )
            dry_run = True

        print(f"\nApplying {len(all_fixes)} fix(es)...")
        applied = apply_fixes(all_fixes, dry_run=dry_run)

        if dry_run:
            print(f"\n[DRY-RUN] Would apply {applied} fix(es)")
            print("Run with --file <path> to apply changes to a specific file.")
        else:
            print(f"\n✅ Applied {applied} fix(es)")

        return 0

    if args.command == "verify":
        print("Running mypy with --disallow-untyped-decorators...")
        files = [args.file.resolve()] if args.file else None
        error_count, output = run_mypy_check(args.path, files)

        if error_count == 0:
            print("\n✅ No untyped-decorator errors found!")
            return 0
        if error_count < 0:
            print(f"\n⚠️  {output}")
            return 1

        print(f"\n⚠️  Found {error_count} untyped-decorator error(s)")

        if args.verbose:
            print("\nDetailed errors:")
            for line in output.splitlines():
                if "untyped-decorator" in line:
                    print(f"  {line}")

        return error_count
    return None


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-003",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "ast",
        "caching",
        "cli",
        "dataclass",
        "filesystem",
        "operations",
        "scripts",
        "subprocess",
    ],
    "keywords": [
        "analyze",
        "apply",
        "check",
        "decorator",
        "decorators",
        "definitions",
        "end",
        "factory",
    ],
    "business_value": "This error occurs when a decorator doesn't properly preserve the type signature of the decorated function. The fix uses ParamSpec and TypeVar to maintain type information. # Identify all untyped decor",
    "last_modified": "2026-01-25T08:58:45Z",
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
