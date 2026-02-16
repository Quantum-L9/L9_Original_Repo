#!/usr/bin/env python3
"""
Fix decorator @wraps violations.

Adds @wraps(func) to decorator inner functions that are missing it.

Strategy:
1. Find functions that have inner functions AND return those inner functions
2. For each inner function without @wraps, add @wraps(param) where param is
   the first parameter of the outer function (usually 'func' or 'f')
3. Ensure 'from functools import wraps' is imported

Run: python scripts/fix_decorator_wraps.py
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Fix Decorator Wraps",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-31T23:12:54Z",
    "updated_at": "2026-01-31T23:14:00Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "fix_decorator_wraps",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import ast
import re
from pathlib import Path

import structlog

# Files with violations (from test output)

logger = structlog.get_logger(__name__)

FILES_TO_FIX = [
    "core/singleton_auto_registry.py",
    "core/auto_registry.py",
    "core/decorators.py",
    "core/packet_envelope/observability.py",
    "core/tools/memory_tools.py",
    "core/observability/instrumentation.py",
    "core/schemas/schema_registry.py",
    "core/schemas/upcaster_registry.py",
    "core/instrumentation/decorators.py",
    "core/governance/rate_limit_policy.py",
    "core/protocols/retry_protocols.py",
    "core/protocols/validation_protocols.py",
    "core/protocols/rate_limiting_protocols.py",
    "core/l_agent_runtime/action_registry.py",
    "memory/query_cache.py",
    "memory/substrate_semantic.py",
    "orchestration/task_router.py",
    "runtime/dora.py",
    "runtime/tool_registry.py",
    "runtime/kernel_loader.py",
    "runtime/tool_call_wrapper.py",
    "agents/agent_registry.py",
]


class DecoratorAnalyzer(ast.NodeVisitor):
    """Find inner functions in decorators that need @wraps."""

    def __init__(self):
        self.fixes_needed: list[
            dict
        ] = []  # {inner_line, outer_param, outer_name, inner_name}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._check_decorator_pattern(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._check_decorator_pattern(node)
        self.generic_visit(node)

    def _check_decorator_pattern(self, node):
        """Check if this function is a decorator with inner functions."""
        inner_functions = []
        returned_names = set()

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                inner_functions.append(item)
            elif isinstance(item, ast.Return) and isinstance(item.value, ast.Name):
                returned_names.add(item.value.id)

        # Function returns an inner function = decorator pattern
        for inner in inner_functions:
            if inner.name in returned_names:
                # Check if inner function has @wraps
                has_wraps = any(
                    (isinstance(d, ast.Name) and d.id == "wraps")
                    or (
                        isinstance(d, ast.Call)
                        and isinstance(d.func, ast.Name)
                        and d.func.id == "wraps"
                    )
                    or (
                        isinstance(d, ast.Call)
                        and isinstance(d.func, ast.Attribute)
                        and d.func.attr == "wraps"
                    )
                    for d in inner.decorator_list
                )

                if not has_wraps:
                    # Get the first parameter of the OUTER function (what gets wrapped)
                    outer_param = None
                    if node.args.args:
                        outer_param = node.args.args[0].arg

                    self.fixes_needed.append(
                        {
                            "inner_line": inner.lineno,
                            "outer_param": outer_param or "func",
                            "outer_name": node.name,
                            "inner_name": inner.name,
                        }
                    )


def ensure_wraps_import(content: str) -> str:
    """Ensure 'from functools import wraps' is present."""
    if re.search(r"from functools import.*\bwraps\b", content):
        return content

    if "import functools" in content:
        # Use functools.wraps in the code
        return content

    if "from functools import" in content:
        # Add wraps to existing import
        content = re.sub(
            r"from functools import ([^\n]+)",
            lambda m: f"from functools import wraps, {m.group(1)}"
            if "wraps" not in m.group(1)
            else m.group(0),
            content,
            count=1,
        )
        return content

    # Add new import after existing imports
    lines = content.split("\n")
    last_import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            last_import_idx = i

    lines.insert(last_import_idx + 1, "from functools import wraps")
    return "\n".join(lines)


def fix_file(filepath: Path, dry_run: bool = False) -> tuple[bool, int]:
    """Fix a file by adding @wraps to decorator inner functions."""
    content = filepath.read_text()

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        logger.error(
            "  ⚠️ syntax error at line {e.lineno}, skipping: filepath", filepath=filepath
        )
        return False, 0

    analyzer = DecoratorAnalyzer()
    analyzer.visit(tree)

    if not analyzer.fixes_needed:
        return False, 0

    lines = content.split("\n")

    # Sort fixes by line number descending (to avoid offset issues when inserting)
    analyzer.fixes_needed.sort(key=lambda x: x["inner_line"], reverse=True)

    for fix in analyzer.fixes_needed:
        line_no = fix["inner_line"]
        param = fix["outer_param"]
        line_idx = line_no - 1

        if line_idx >= len(lines):
            continue

        line = lines[line_idx]

        # Skip if already has @wraps on this line or previous line
        if "@wraps" in line:
            continue
        if line_idx > 0 and "@wraps" in lines[line_idx - 1]:
            continue

        # Get indentation of the function definition line
        indent = len(line) - len(line.lstrip())
        indent_str = " " * indent

        # Insert @wraps decorator before the inner function
        wraps_line = f"{indent_str}@wraps({param})"
        lines.insert(line_idx, wraps_line)

    new_content = "\n".join(lines)

    # Add import if needed
    new_content = ensure_wraps_import(new_content)

    if dry_run:
        logger.info(
            "🔍 would fix {len(analyzer.fixes needed)} in filepath", filepath=filepath
        )
        for fix in analyzer.fixes_needed:
            print(
                f"   Line {fix['inner_line']}: {fix['outer_name']}() -> {fix['inner_name']}()"
            )
        return True, len(analyzer.fixes_needed)

    filepath.write_text(new_content)
    return True, len(analyzer.fixes_needed)


def main():
    """Fix all files with decorator violations."""
    import sys

    dry_run = "--dry-run" in sys.argv

    logger.info("=" * 60)
    logger.info("decorator @wraps fixer")
    logger.info("=" * 60)
    logger.info("mode: {'dry run' if dry_run else 'live'}\n")

    repo_root = Path(__file__).parent.parent
    total_fixes = 0
    files_fixed = 0

    for rel_path in FILES_TO_FIX:
        filepath = repo_root / rel_path
        if not filepath.exists():
            logger.info("⚠️ not found: rel path", rel_path=rel_path)
            continue

        changed, count = fix_file(filepath, dry_run=dry_run)
        if changed:
            if not dry_run:
                logger.info(
                    "✅ fixed count in rel path", count=count, rel_path=rel_path
                )
            total_fixes += count
            files_fixed += 1
        else:
            logger.info("✓ no fixes needed: rel path", rel_path=rel_path)

    logger.info("\n" + "=" * 60)
    logger.info(
        "summary: total fixes fixes in files fixed files",
        total_fixes=total_fixes,
        files_fixed=files_fixed,
    )
    logger.info("=" * 60)

    if dry_run:
        logger.info("\nrun without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-004",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "analyzer",
        "ast",
        "caching",
        "cli",
        "filesystem",
        "operations",
        "scripts",
        "testing",
    ],
    "keywords": ["analyzer", "decorator", "ensure", "fix", "wraps"],
    "business_value": "the first parameter of the outer function (usually 'func' or 'f') 3. Ensure 'from functools import wraps' is imported Run: python scripts/fix_decorator_wraps.py",
    "last_modified": "2026-01-31T23:14:00Z",
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
