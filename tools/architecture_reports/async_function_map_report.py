from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from .config import RepoLayout, iter_python_files
from .filesystem import open_report


class AsyncCallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: set[str] = set()

    def visit_Await(self, node: ast.Await) -> None:
        if isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Attribute):
                self.calls.add(func.attr)
            elif isinstance(func, ast.Name):
                self.calls.add(func.id)
        self.generic_visit(node)


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def generate_async_function_map(layout: RepoLayout) -> None:
    """Generate async_function_map.txt with async defs and awaited callees."""
    output = layout.reports_dir / "async_function_map.txt"
    grouped: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    for path in iter_python_files(layout.src_dirs):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue

        module = _module_from_path(layout, path)

        for node in tree.body:
            if isinstance(node, ast.AsyncFunctionDef):
                visitor = AsyncCallVisitor()
                visitor.visit(node)
                grouped[module][node.name].update(visitor.calls)

    with open_report(output) as f:
        for module in sorted(grouped.keys()):
            for func, calls in sorted(grouped[module].items()):
                f.write(f"async function: {module}.{func}\n")
                if not calls:
                    f.write("  calls: (none detected)\n\n")
                    continue
                f.write("  calls:\n")
                for name in sorted(calls):
                    f.write(f"    - {name}\n")
                f.write("\n")
