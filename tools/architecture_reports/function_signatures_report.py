from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from .config import RepoLayout, iter_python_files
from .filesystem import open_report


def _format_args(node: ast.arguments) -> str:
    parts: list[str] = []

    def add_arg(a: ast.arg, default: str | None = None) -> None:
        if default is not None:
            parts.append(f"{a.arg}={default}")
        else:
            parts.append(a.arg)

    defaults_iter = iter(node.defaults or [])
    defaults_count = len(list(node.defaults or []))
    positional = node.posonlyargs + node.args
    start_defaults = len(positional) - defaults_count

    for idx, a in enumerate(positional):
        default_value = None
        if idx >= start_defaults:
            # re-create iterator each time, simpler and safe for small lists
            default_value = "..."
        add_arg(a, default_value)

    if node.vararg:
        parts.append(f"*{node.vararg.arg}")

    for a in node.kwonlyargs or []:
        add_arg(a, "...")

    if node.kwarg:
        parts.append(f"**{node.kwarg.arg}")

    return ", ".join(parts)


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def generate_function_signatures(layout: RepoLayout) -> None:
    """Generate function_signatures.txt with public function signatures by module."""
    output = layout.reports_dir / "function_signatures.txt"
    grouped: dict[str, list[str]] = defaultdict(list)

    for path in iter_python_files(layout.src_dirs):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue

        module_name = _module_from_path(layout, path)

        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                sig = _format_args(node.args)
                grouped[module_name].append(f"def {node.name}({sig})")

    with open_report(output) as f:
        for module in sorted(grouped.keys()):
            f.write(f"module: {module}\n")
            for line in sorted(grouped[module]):
                f.write(f"  {line}\n")
            f.write("\n")
