from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from .config import RepoLayout, iter_python_files
from .filesystem import open_report


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def _base_name(base: ast.expr) -> str:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return ast.unparse(base) if hasattr(ast, "unparse") else "<expr>"


def generate_class_definitions(layout: RepoLayout) -> None:
    """Generate class_definitions.txt with class inventory by module."""
    output = layout.reports_dir / "class_definitions.txt"
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

        module = _module_from_path(layout, path)

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                bases = ", ".join(_base_name(b) for b in node.bases) or "object"
                decorators = {
                    d.id for d in node.decorator_list if isinstance(d, ast.Name)
                }
                prefix = ""
                if "dataclass" in decorators:
                    prefix = "@dataclass "
                grouped[module].append(f"{prefix}class {node.name} ({bases})")

    with open_report(output) as f:
        for module in sorted(grouped.keys()):
            f.write(f"module: {module}\n")
            for line in sorted(grouped[module]):
                f.write(f"  {line}\n")
            f.write("\n")
