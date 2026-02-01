"""
ADR-0003 Docstring Injector — Automated docstring generation using AST

Scans Python files and injects Google-style docstrings for:
- Module-level docstrings (if missing)
- Public classes (not starting with _)
- Public functions/methods (not starting with _)

Uses AST to analyze function signatures and generate appropriate docstrings.
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Docstring Injector",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-28T21:00:00Z",
    "updated_at": "2026-01-28T21:00:00Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "docstring_injector",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging  # noqa: ADR-0019

    logging.basicConfig(level=logging.INFO)
    logger = structlog.get_logger(__name__)


@dataclass
class InjectionResult:
    """Result of docstring injection for a single file."""

    file: str
    injections: int
    functions_processed: list[str]
    classes_processed: list[str]
    dry_run: bool


class DocstringInjector:
    """
    Automated docstring generator using AST analysis.

    Generates Google-style docstrings based on:
    - Function/method name (converted to description)
    - Parameters with type hints
    - Return type annotations
    - Async status
    """

    SKIP_PARTS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "tests",  # Skip tests - docstrings optional
        ".cursor",
        "migrations",
        "current_work",  # Work in progress
        "codegen",  # Generated code
        "_archived",  # Archived code
    }

    # Common parameter name patterns -> descriptions
    PARAM_DESCRIPTIONS = {
        "self": None,  # Skip self
        "cls": None,  # Skip cls
        "args": "Positional arguments.",
        "kwargs": "Keyword arguments.",
        "request": "The incoming request object.",
        "response": "The response object.",
        "session": "Database session.",
        "db": "Database connection.",
        "conn": "Database connection.",
        "cursor": "Database cursor.",
        "path": "File or directory path.",
        "file_path": "Path to the file.",
        "data": "Input data.",
        "payload": "Request payload.",
        "config": "Configuration object.",
        "settings": "Settings object.",
        "options": "Configuration options.",
        "timeout": "Timeout in seconds.",
        "limit": "Maximum number of results.",
        "offset": "Starting offset for pagination.",
        "query": "Search query string.",
        "filters": "Filter criteria.",
        "callback": "Callback function.",
        "handler": "Event handler function.",
        "context": "Execution context.",
        "ctx": "Execution context.",
        "env": "Environment variables or settings.",
        "logger": "Logger instance.",
        "client": "Client instance.",
        "service": "Service instance.",
        "repo": "Repository instance.",
        "repository": "Repository instance.",
        "user_id": "User identifier.",
        "tenant_id": "Tenant identifier.",
        "thread_id": "Thread/conversation identifier.",
        "task_id": "Task identifier.",
        "agent_id": "Agent identifier.",
        "message": "Message content.",
        "content": "Content string.",
        "text": "Text content.",
        "name": "Name string.",
        "key": "Key identifier.",
        "value": "Value to set.",
        "result": "Result object.",
        "error": "Error object or message.",
        "exception": "Exception instance.",
        "exc": "Exception instance.",
    }

    # Return type -> description mapping
    RETURN_DESCRIPTIONS = {
        "None": None,
        "bool": "True if successful, False otherwise.",
        "int": "Integer result.",
        "float": "Numeric result.",
        "str": "String result.",
        "list": "List of results.",
        "dict": "Dictionary result.",
        "tuple": "Tuple of results.",
        "set": "Set of results.",
        "bytes": "Binary data.",
        "Path": "Path object.",
        "Optional": "Result or None if not found.",
        "Any": "Result value.",
    }

    def __init__(self, repo_root: Path | None = None) -> None:
        """
        Initialize the docstring injector.

        Args:
            repo_root: Root directory of the repository.
        """
        self.repo_root = repo_root or Path.cwd()

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        parts = set(path.parts)
        return any(skip in parts for skip in self.SKIP_PARTS)

    def _name_to_description(self, name: str, is_class: bool = False) -> str:
        """
        Convert a function/class name to a human-readable description.

        Args:
            name: The function or class name.
            is_class: Whether this is a class name.

        Returns:
            Human-readable description.
        """
        # Handle special method names
        if name == "__init__":
            return "Initialize the instance."
        if name == "__str__":
            return "Return string representation."
        if name == "__repr__":
            return "Return detailed string representation."
        if name == "__eq__":
            return "Check equality with another object."
        if name == "__hash__":
            return "Return hash value."
        if name == "__len__":
            return "Return the length."
        if name == "__iter__":
            return "Return an iterator."
        if name == "__next__":
            return "Return the next item."
        if name == "__enter__":
            return "Enter the context manager."
        if name == "__exit__":
            return "Exit the context manager."
        if name == "__call__":
            return "Call the instance as a function."
        if name == "__getitem__":
            return "Get an item by key or index."
        if name == "__setitem__":
            return "Set an item by key or index."
        if name == "__contains__":
            return "Check if item is contained."

        # Convert snake_case/CamelCase to words
        # First handle CamelCase
        words = re.sub(r"([A-Z])", r" \1", name).strip()
        # Then handle snake_case
        words = words.replace("_", " ")
        # Clean up multiple spaces
        words = re.sub(r"\s+", " ", words).strip().lower()

        if not words:
            return "TODO: Add description."

        # Capitalize first letter
        words = words[0].upper() + words[1:]

        # Add appropriate ending
        if is_class:
            return f"{words}."
        # Make it sound like an action
        first_word = words.split()[0].lower()
        if (
            first_word
            in (
                "get",
                "fetch",
                "load",
                "read",
                "find",
                "search",
                "query",
            )
            or first_word in ("set", "update", "write", "save", "store", "put")
            or first_word in ("is", "has", "can", "should", "check", "validate")
            or first_word in ("create", "build", "make", "generate", "produce")
            or first_word in ("delete", "remove", "clear", "reset", "destroy")
            or first_word in ("start", "stop", "run", "execute", "process")
            or first_word in ("init", "initialize", "setup", "configure")
            or first_word in ("parse", "convert", "transform", "format")
        ):
            return f"{words}."
        if first_word == "to":
            return f"Convert {words[3:]}." if len(words) > 3 else f"{words}."
        return f"{words}."

    def _get_type_str(self, annotation: ast.expr | None) -> str:
        """
        Convert an AST annotation to a string representation.

        Args:
            annotation: AST annotation node.

        Returns:
            String representation of the type.
        """
        if annotation is None:
            return "Any"

        if isinstance(annotation, ast.Name):
            return annotation.id
        if isinstance(annotation, ast.Constant):
            return str(annotation.value)
        if isinstance(annotation, ast.Subscript):
            # Handle generics like List[str], Optional[int], etc.
            if isinstance(annotation.value, ast.Name):
                base = annotation.value.id
                if isinstance(annotation.slice, ast.Name):
                    return f"{base}[{annotation.slice.id}]"
                if isinstance(annotation.slice, ast.Constant):
                    return f"{base}[{annotation.slice.value}]"
                if isinstance(annotation.slice, ast.Tuple):
                    parts = [self._get_type_str(elt) for elt in annotation.slice.elts]
                    return f"{base}[{', '.join(parts)}]"
                return base
            return "Any"
        if isinstance(annotation, ast.BinOp):
            # Handle Union types with | syntax
            if isinstance(annotation.op, ast.BitOr):
                left = self._get_type_str(annotation.left)
                right = self._get_type_str(annotation.right)
                return f"{left} | {right}"
        elif isinstance(annotation, ast.Attribute):
            return annotation.attr

        return "Any"

    def _get_param_description(self, param_name: str, param_type: str) -> str:
        """
        Generate a description for a parameter.

        Args:
            param_name: Name of the parameter.
            param_type: Type annotation string.

        Returns:
            Parameter description.
        """
        # Check known parameter names
        if param_name in self.PARAM_DESCRIPTIONS:
            desc = self.PARAM_DESCRIPTIONS[param_name]
            if desc is None:
                return ""  # Skip this param
            return desc

        # Generate from type
        if param_type != "Any":
            return f"The {param_name.replace('_', ' ')} ({param_type})."
        return f"The {param_name.replace('_', ' ')}."

    def _get_return_description(self, return_type: str) -> str | None:
        """
        Generate a description for the return value.

        Args:
            return_type: Return type annotation string.

        Returns:
            Return description or None if void.
        """
        if return_type in ("None", ""):
            return None

        # Check base type
        base_type = return_type.split("[")[0]
        if base_type in self.RETURN_DESCRIPTIONS:
            return self.RETURN_DESCRIPTIONS[base_type]

        return f"The {return_type} result."

    def generate_function_docstring(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        indent: str = "    ",
    ) -> str:
        """
        Generate a Google-style docstring for a function.

        Args:
            node: The function AST node.
            indent: Indentation string for the docstring.

        Returns:
            Generated docstring with proper indentation.
        """
        lines = []

        # Description line
        description = self._name_to_description(node.name)
        lines.append(f'{indent}"""')
        lines.append(f"{indent}{description}")

        # Collect parameters (skip self/cls)
        params = []
        for arg in node.args.args:
            name = arg.arg
            if name in ("self", "cls"):
                continue
            type_str = self._get_type_str(arg.annotation)
            desc = self._get_param_description(name, type_str)
            if desc:
                params.append((name, type_str, desc))

        # Add *args if present
        if node.args.vararg:
            params.append(("*args", "Any", "Positional arguments."))

        # Add **kwargs if present
        if node.args.kwarg:
            params.append(("**kwargs", "Any", "Keyword arguments."))

        # Args section
        if params:
            lines.append("")
            lines.append(f"{indent}Args:")
            for name, type_str, desc in params:
                if type_str != "Any":
                    lines.append(f"{indent}    {name}: {desc}")
                else:
                    lines.append(f"{indent}    {name}: {desc}")

        # Returns section
        return_type = self._get_type_str(node.returns)
        return_desc = self._get_return_description(return_type)
        if return_desc:
            lines.append("")
            lines.append(f"{indent}Returns:")
            lines.append(f"{indent}    {return_desc}")

        lines.append(f'{indent}"""')
        return "\n".join(lines)

    def generate_class_docstring(self, node: ast.ClassDef, indent: str = "") -> str:
        """
        Generate a Google-style docstring for a class.

        Args:
            node: The class AST node.
            indent: Indentation string for the docstring.

        Returns:
            Generated docstring with proper indentation.
        """
        description = self._name_to_description(node.name, is_class=True)
        return f'{indent}"""{description}"""'

    def generate_module_docstring(self, filepath: Path) -> str:
        """
        Generate a module-level docstring based on filename.

        Args:
            filepath: Path to the Python file.

        Returns:
            Generated module docstring.
        """
        name = filepath.stem
        description = self._name_to_description(name)
        # Make it more module-appropriate
        description = description.rstrip(".")
        return f'"""\n{description} module.\n"""'

    def inject_docstrings(
        self, filepath: Path, dry_run: bool = True
    ) -> InjectionResult:
        """
        Inject missing docstrings into a Python file.

        Args:
            filepath: Path to the Python file.
            dry_run: If True, only report what would be done.

        Returns:
            InjectionResult with details of changes.
        """
        try:
            content = filepath.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning(f"Could not parse {filepath}: {e}")
            return InjectionResult(
                file=str(filepath),
                injections=0,
                functions_processed=[],
                classes_processed=[],
                dry_run=dry_run,
            )

        lines = content.splitlines(keepends=True)
        insertions: list[tuple[int, str]] = []  # (line_index, docstring)
        functions_processed = []
        classes_processed = []

        # Check module docstring
        has_module_docstring = ast.get_docstring(tree) is not None
        if not has_module_docstring and filepath.name != "__init__.py":
            # Find where to insert (after any leading comments/shebang)
            insert_line = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if (
                    stripped.startswith("#")
                    or stripped.startswith("'''")
                    or not stripped
                ):
                    insert_line = i + 1
                else:
                    break
            module_doc = self.generate_module_docstring(filepath)
            insertions.append((insert_line, module_doc + "\n\n"))

        # Walk AST for classes and functions
        for node in ast.walk(tree):
            # Skip private items
            node_name = getattr(node, "name", None)
            if (
                node_name
                and node_name.startswith("_")
                and not node_name.startswith("__")
            ):
                continue

            if isinstance(node, ast.ClassDef):
                if ast.get_docstring(node) is None:
                    # Find the line after class definition
                    class_line = node.lineno - 1  # 0-indexed
                    # Find the colon ending the class def
                    for i in range(class_line, min(class_line + 5, len(lines))):
                        if ":" in lines[i]:
                            insert_line = i + 1
                            break
                    else:
                        insert_line = class_line + 1

                    # Determine indentation
                    indent = "    "
                    docstring = f'{indent}"""{self._name_to_description(node.name, is_class=True)}"""\n\n'
                    insertions.append((insert_line, docstring))
                    classes_processed.append(node.name)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node) is None:
                    # Find the line after function definition
                    func_line = node.lineno - 1  # 0-indexed
                    # Find the colon ending the function def
                    for i in range(func_line, min(func_line + 10, len(lines))):
                        if ":" in lines[i] and not lines[i].strip().startswith("#"):
                            insert_line = i + 1
                            break
                    else:
                        insert_line = func_line + 1

                    # Determine indentation (function body indent)
                    base_indent = ""
                    if insert_line < len(lines):
                        next_line = (
                            lines[insert_line] if insert_line < len(lines) else ""
                        )
                        match = re.match(r"^(\s*)", next_line)
                        if match:
                            base_indent = match.group(1)
                    if not base_indent:
                        # Guess from function definition
                        match = re.match(r"^(\s*)", lines[func_line])
                        base_indent = (match.group(1) if match else "") + "    "

                    docstring = self.generate_function_docstring(node, base_indent)
                    insertions.append((insert_line, docstring + "\n"))
                    functions_processed.append(node.name)

        if not dry_run and insertions:
            # Sort insertions by line number (descending) to avoid offset issues
            insertions.sort(key=lambda x: x[0], reverse=True)
            for line_idx, docstring in insertions:
                lines.insert(line_idx, docstring)

            filepath.write_text("".join(lines), encoding="utf-8")

        return InjectionResult(
            file=str(filepath),
            injections=len(insertions),
            functions_processed=functions_processed,
            classes_processed=classes_processed,
            dry_run=dry_run,
        )

    def scan_repo(self, dry_run: bool = True) -> list[InjectionResult]:
        """
        Scan repository and inject docstrings.

        Args:
            dry_run: If True, only report what would be done.

        Returns:
            List of injection results for each file.
        """
        results = []
        for py_file in sorted(self.repo_root.rglob("*.py")):
            if not py_file.is_file() or self._should_skip(py_file):
                continue

            result = self.inject_docstrings(py_file, dry_run=dry_run)
            if result.injections > 0:
                results.append(result)

        return results


def main() -> int:
    """
    CLI entry point for docstring injector.

    Returns:
        Exit code (0 for success).
    """
    parser = argparse.ArgumentParser(
        description="ADR-0003 Docstring Injector - Auto-generate missing docstrings"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Path to repository root",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report what would be done (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually inject docstrings",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Process single file only",
    )

    args = parser.parse_args()

    injector = DocstringInjector(Path(args.repo))
    dry_run = not args.execute

    if args.file:
        result = injector.inject_docstrings(Path(args.file), dry_run=dry_run)
        results = [result] if result.injections > 0 else []
    else:
        results = injector.scan_repo(dry_run=dry_run)

    # Print summary
    total_injections = sum(r.injections for r in results)
    total_functions = sum(len(r.functions_processed) for r in results)
    total_classes = sum(len(r.classes_processed) for r in results)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Docstring Injection Summary")
    print("=" * 50)
    print(f"Files with missing docstrings: {len(results)}")
    print(f"Total injections needed: {total_injections}")
    print(f"  - Functions/methods: {total_functions}")
    print(f"  - Classes: {total_classes}")

    if results and len(results) <= 20:
        print("\nFiles:")
        for r in results:
            mode = "[would inject]" if dry_run else "[injected]"
            print(f"  {mode} {r.file}: {r.injections} docstrings")
            if r.functions_processed:
                print(f"    Functions: {', '.join(r.functions_processed[:5])}")
            if r.classes_processed:
                print(f"    Classes: {', '.join(r.classes_processed[:5])}")

    if dry_run:
        print("\nRun with --execute to inject docstrings.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-007",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "ast",
        "caching",
        "cli",
        "dataclass",
        "event-driven",
        "filesystem",
        "logging",
        "messaging",
        "migration",
    ],
    "keywords": [
        "docstring",
        "docstrings",
        "function",
        "generate",
        "inject",
        "injection",
        "injector",
        "module",
    ],
    "business_value": "Provides docstring injector components including InjectionResult, DocstringInjector",
    "last_modified": "2026-01-31T22:28:10Z",
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
