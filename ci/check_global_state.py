"""
L9 Global State Audit

Scans Python files for suspicious module-level mutable state patterns.

This is a heuristic tool, NOT a formal guarantee.

It looks for:
  - top-level assignments to dict/list/set
  - names like STATE, CACHE, active_*, *_state, *_cache
and prints their locations for manual review.
"""

from __future__ import annotations


import ast
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)
ROOT = Path(__file__).resolve().parents[2]


def iter_python_files() -> list[Path]:
    """Iterate over Python files in the repository."""
    ignored = {"tests", ".venv", "venv", "migrations", "private"}
    files: list[Path] = []

    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        parts = set(rel.parts)
        if parts & ignored:
            continue
        files.append(path)
    return files


class GlobalStateVisitor(ast.NodeVisitor):
    """
    Performs static analysis of Python files to detect suspicious module-level mutable state patterns, aiding in global state audit.

    Args:
        filename: Path to the Python file being analyzed.


    Raises:
        SyntaxError: If the analyzed file contains invalid Python syntax.
    """

    def __init__(self, filename: Path) -> None:
        """Initialize visitor with filename."""
        self.filename = filename
        self.suspicious: list[tuple[int, str]] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment node and check for suspicious patterns."""
        # Only look at module-level assignments
        if not isinstance(getattr(node, "parent", None), ast.Module):
            return

        # Track targets
        target_names = []
        for t in node.targets:
            if isinstance(t, ast.Name):
                target_names.append(t.id)

        # Track suspicious value types
        suspicious_value = isinstance(
            node.value,
            (ast.Dict, ast.List, ast.Set, ast.Call),
        )

        # Heuristic: name patterns
        name_patterns = ("STATE", "CACHE", "active_", "_state", "_cache")
        suspicious_name = any(
            any(pattern in name.upper() for pattern in name_patterns)
            for name in target_names
        )

        if suspicious_value or suspicious_name:
            line = node.lineno
            for name in target_names:
                self.suspicious.append((line, name))

    def generic_visit(self, node: ast.AST) -> None:
        """Visit child nodes and set parent references."""
        for child in ast.iter_child_nodes(node):
            child.parent = node  # type: ignore[attr-defined]
            self.visit(child)


def main() -> None:
    """Run global state audit on repository."""
    files = iter_python_files()
    logger.info(f"[L9 STATE AUDIT] Scanning {len(files)} Python files under {ROOT}")

    total_hits = 0

    for path in files:
        try:
            src = path.read_text(encoding="utf-8")
        except Exception as e:  # pragma: no cover
            logger.warning(f"[WARN] Could not read {path}: {e}")
            continue

        try:
            tree = ast.parse(src)
        except SyntaxError as e:  # pragma: no cover
            logger.error(f"[WARN] Syntax error in {path}: {e}")
            continue

        visitor = GlobalStateVisitor(path)
        visitor.visit(tree)

        if visitor.suspicious:
            logger.info(f"\n[FILE] {path.relative_to(ROOT)}")
            for lineno, name in visitor.suspicious:
                logger.info(f"  line {lineno:4d}: {name}")
            total_hits += len(visitor.suspicious)

    logger.info(
        f"\n[L9 STATE AUDIT] Suspicious global state declarations: {total_hits}"
    )


if __name__ == "__main__":
    main()


# ============================================================================
# Runtime execution trace - updated automatically on every execution
