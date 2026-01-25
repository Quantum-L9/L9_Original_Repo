from __future__ import annotations

import ast

from .config import RepoLayout
from .filesystem import open_report

FASTAPI_DECORATORS = {"get", "post", "put", "delete", "patch"}


def generate_route_handlers(layout: RepoLayout) -> None:
    """Generate route_handlers.txt mapping HTTP routes to handler functions."""
    output = layout.reports_dir / "route_handlers.txt"

    rows: list[tuple[str, str, str]] = []  # (method, path, handler)

    for base in layout.api_dirs:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            try:
                src = path.read_text(encoding="utf-8")
            except OSError:
                continue
            try:
                tree = ast.parse(src, filename=str(path))
            except SyntaxError:
                continue

            module = ".".join(path.relative_to(layout.root).with_suffix("").parts)

            for node in tree.body:
                if not isinstance(node, ast.FunctionDef):
                    continue
                method = None
                route_path = None
                for dec in node.decorator_list:
                    if not isinstance(dec, ast.Call):
                        continue
                    func = dec.func
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr in FASTAPI_DECORATORS
                    ):
                        method = func.attr.upper()
                        if (
                            dec.args
                            and isinstance(dec.args[0], ast.Constant)
                            and isinstance(dec.args[0].value, str)
                        ):
                            route_path = dec.args[0].value
                if method and route_path:
                    handler = f"{module}.{node.name}"
                    rows.append((method, route_path, handler))

    rows.sort(key=lambda r: (r[1], r[0]))

    with open_report(output) as f:
        for method, path, handler in rows:
            f.write(f"{method} {path} -> {handler}\n")
