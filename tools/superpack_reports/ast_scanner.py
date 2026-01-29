from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Ast Scanner",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:50:13Z",
    "updated_at": "2026-01-25T14:49:28Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "ast_scanner",
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
    # NEW: High-value extractions
    docstring: str | None = None
    exports: list[str] = field(default_factory=list)  # __all__ contents
    global_vars: list[GlobalVarInfo] = field(default_factory=list)
    constants: list[ConstantInfo] = field(default_factory=list)


@dataclass
class ClassInfo:
    """Information about a class."""

    name: str
    bases: list[str]
    methods: list[MethodInfo] = field(default_factory=list)
    is_pydantic: bool = False
    is_dataclass: bool = False
    decorators: list[str] = field(default_factory=list)
    # NEW: High-value extractions
    docstring: str | None = None
    line_start: int = 0
    line_end: int | None = None


@dataclass
class MethodInfo:
    """Information about a class method."""

    name: str
    is_async: bool = False
    args: list[str] = field(default_factory=list)
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    line_start: int = 0
    line_end: int | None = None


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
    # NEW: High-value extractions
    return_type: str | None = None
    docstring: str | None = None
    line_start: int = 0
    line_end: int | None = None


@dataclass
class GlobalVarInfo:
    """Information about a module-level global variable."""

    name: str
    type_hint: str | None = None
    line: int = 0


@dataclass
class ConstantInfo:
    """Information about a module-level constant (UPPER_CASE assignment)."""

    name: str
    value_repr: str | None = None  # String representation of value
    line: int = 0


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


def _get_type_annotation(node: ast.expr | None) -> str | None:
    """Extract type annotation as string from AST node."""
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return "<complex>"


def _is_constant_name(name: str) -> bool:
    """Check if name follows CONSTANT_CASE convention."""
    return name.isupper() and not name.startswith("_")


def _get_value_repr(node: ast.expr) -> str | None:
    """Get string representation of a value node (truncated for safety)."""
    try:
        unparsed = ast.unparse(node)
        # Truncate long values
        if len(unparsed) > 100:
            return unparsed[:100] + "..."
        return unparsed
    except Exception:
        return None


def _extract_all_names(node: ast.Assign) -> list[str] | None:
    """Extract names from __all__ assignment."""
    if not isinstance(node.value, (ast.List, ast.Tuple)):
        return None
    names = []
    for elt in node.value.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            names.append(elt.value)
    return names


ROUTE_DECORATORS = {"get", "post", "put", "delete", "patch", "websocket"}


def scan_module(path: Path, root: Path) -> ModuleInfo | None:
    """
    Scan a Python module and extract structural information.

    Extracts:
    - Module docstring and __all__ exports
    - Classes with docstrings, methods, line numbers
    - Functions with docstrings, return types, line numbers
    - Global variables and constants

    Args:
        path: Path to the Python file
        root: Root directory for relative path calculation

    Returns:
        ModuleInfo or None if file cannot be parsed
    """
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
        docstring=ast.get_docstring(tree),
    )

    for node in tree.body:
        # Imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                info.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                info.imports.append(node.module)

        # Assignments: __all__, globals, constants
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    # __all__ exports
                    if name == "__all__":
                        all_names = _extract_all_names(node)
                        if all_names:
                            info.exports = all_names
                    # Constants (UPPER_CASE)
                    elif _is_constant_name(name):
                        info.constants.append(
                            ConstantInfo(
                                name=name,
                                value_repr=_get_value_repr(node.value),
                                line=node.lineno,
                            )
                        )
                    # Global variables (lower_case at module level)
                    elif not name.startswith("_"):
                        info.global_vars.append(
                            GlobalVarInfo(
                                name=name,
                                type_hint=None,
                                line=node.lineno,
                            )
                        )

        # Annotated assignments (typed globals)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            type_hint = _get_type_annotation(node.annotation)
            if _is_constant_name(name):
                info.constants.append(
                    ConstantInfo(
                        name=name,
                        value_repr=_get_value_repr(node.value) if node.value else None,
                        line=node.lineno,
                    )
                )
            elif not name.startswith("_"):
                info.global_vars.append(
                    GlobalVarInfo(
                        name=name,
                        type_hint=type_hint,
                        line=node.lineno,
                    )
                )

        # Classes
        elif isinstance(node, ast.ClassDef):
            bases = [_base_name(b) for b in node.bases]
            decorators = [_get_decorator_name(d) for d in node.decorator_list]

            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_decorators = [
                        _get_decorator_name(d) for d in item.decorator_list
                    ]
                    methods.append(
                        MethodInfo(
                            name=item.name,
                            is_async=isinstance(item, ast.AsyncFunctionDef),
                            args=[a.arg for a in item.args.args],
                            return_type=_get_type_annotation(item.returns),
                            decorators=method_decorators,
                            docstring=ast.get_docstring(item),
                            line_start=item.lineno,
                            line_end=getattr(item, "end_lineno", None),
                        )
                    )

            cls_info = ClassInfo(
                name=node.name,
                bases=bases,
                methods=methods,
                is_pydantic="BaseModel" in bases,
                is_dataclass="dataclass" in decorators,
                decorators=decorators,
                docstring=ast.get_docstring(node),
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", None),
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
                return_type=_get_type_annotation(node.returns),
                docstring=ast.get_docstring(node),
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", None),
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


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-008",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "ast",
        "caching",
        "dataclass",
        "filesystem",
        "operations",
        "pydantic",
        "realtime",
        "tools",
    ],
    "keywords": ["ast", "directories", "function", "module", "scan", "scanner"],
    "business_value": "Provides ast scanner components including ModuleInfo, ClassInfo, FunctionInfo",
    "last_modified": "2026-01-25T14:49:28Z",
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
