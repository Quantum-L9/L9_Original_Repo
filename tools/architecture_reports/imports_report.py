from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from .config import RepoLayout, iter_python_files
from .filesystem import open_report


def _module_from_path(layout: RepoLayout, path: Path) -> str:
    rel = path.relative_to(layout.root)
    return ".".join(rel.with_suffix("").parts)


def generate_imports(layout: RepoLayout) -> None:
    """Generate imports.txt with module-level import relations."""
    output = layout.reports_dir / "imports.txt"
    imports: dict[str, set[str]] = defaultdict(set)

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
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[module].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                imports[module].add(node.module)

    with open_report(output) as f:
        for module in sorted(imports.keys()):
            f.write(f"{module} imports:\n")
            for target in sorted(imports[module]):
                f.write(f"  - {target}\n")
            f.write("\n")
