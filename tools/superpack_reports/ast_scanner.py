from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ModuleInfo:
    """Information about a Python module."""

    path: Path
    module_name: str
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    is_async: bool = False
    loc: int = 0


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    bases: list[str]
    methods: list[str]
    is_pydantic: bool = False
    is_dataclass: bool = False
    decorators: list[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    """Information about a function."""

    name: str
    is_async: bool
    args: list[str]
    decorators: list[str] = field(default_factory=list)
    is_route: bool = False
    route_method: str | None = None
    route_path: str | None = None


def _base_name(base: ast.expr) -> str:
    """Extract base class name from AST node."""
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return ast.unparse(base) if hasattr(ast, "unparse") else "<expr>"


def _get_decorator_name(dec: ast.expr) -> str:
    """Extract decorator name from AST node."""
    if isinstance(dec, ast.Name):
        return dec.id
    if isinstance(dec, ast.Attribute):
        return dec.attr
    if isinstance(dec, ast.Call):
        return _get_decorator_name(dec.func)
    return "<unknown>"


ROUTE_DECORATORS = {"get", "post", "put", "delete", "patch", "websocket"}


def scan_module(path: Path, root: Path) -> ModuleInfo | None:
    """Scan a Python module and extract structural information."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return None

    rel = path.relative_to(root)
    module_name = ".".join(rel.with_suffix("").parts)

    info = ModuleInfo(
        path=path,
        module_name=module_name,
        loc=len(source.splitlines()),
    )

    for node in tree.body:
        # Imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                info.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                info.imports.append(node.module)

        # Classes
        elif isinstance(node, ast.ClassDef):
            bases = [_base_name(b) for b in node.bases]
            decorators = [_get_decorator_name(d) for d in node.decorator_list]

            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(item.name)

            cls_info = ClassInfo(
                name=node.name,
                bases=bases,
                methods=methods,
                is_pydantic="BaseModel" in bases,
                is_dataclass="dataclass" in decorators,
                decorators=decorators,
            )
            info.classes.append(cls_info)

        # Functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_async = isinstance(node, ast.AsyncFunctionDef)
            if is_async:
                info.is_async = True

            decorators = [_get_decorator_name(d) for d in node.decorator_list]
            args = [a.arg for a in node.args.args]

            # Check for route decorators
            is_route = False
            route_method = None
            route_path = None

            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    func = dec.func
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr in ROUTE_DECORATORS
                    ):
                        is_route = True
                        route_method = func.attr.upper()
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            route_path = str(dec.args[0].value)

            func_info = FunctionInfo(
                name=node.name,
                is_async=is_async,
                args=args,
                decorators=decorators,
                is_route=is_route,
                route_method=route_method,
                route_path=route_path,
            )
            info.functions.append(func_info)

    return info


def scan_directories(dirs: Iterable[Path], root: Path) -> list[ModuleInfo]:
    """Scan all Python files in directories and return module info."""
    modules = []
    for base in dirs:
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            info = scan_module(path, root)
            if info:
                modules.append(info)
    return modules
