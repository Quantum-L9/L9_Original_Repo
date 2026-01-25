from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from .config import RepoLayout, iter_python_files
from .filesystem import open_report


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def _is_pydantic_base(base: ast.expr) -> bool:
    if isinstance(base, ast.Name):
        return base.id in {"BaseModel"}
    if isinstance(base, ast.Attribute):
        return base.attr in {"BaseModel"}
    return False


def generate_pydantic_models(layout: RepoLayout) -> None:
    """Generate pydantic_models.txt listing BaseModel subclasses by module."""
    output = layout.reports_dir / "pydantic_models.txt"
    grouped: dict[str, list[str]] = defaultdict(list)

    for path in iter_python_files(layout.src_dirs):
        try:
            src = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError:
            continue

        module = _module_from_path(layout, path)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                if any(_is_pydantic_base(b) for b in node.bases):
                    grouped[module].append(node.name)

    with open_report(output) as f:
        for module in sorted(grouped.keys()):
            f.write(f"module: {module}\n")
            for name in sorted(grouped[module]):
                f.write(f"  BaseModel: {name}\n")
            f.write("\n")
