#!/usr/bin/env python3
from __future__ import annotations

"""
L9 Docstring Injector
=====================
Automated tool for injecting Google-style docstrings into Python files.

This tool uses AST analysis to identify functions, methods, and classes
missing docstrings, then uses an LLM to generate contextually accurate
docstrings based on the code structure and surrounding context.

Features:
- AST-based detection of missing docstrings
- LLM-powered docstring generation (OpenAI-compatible API)
- Dry-run mode for preview without modification
- Batch processing with progress tracking
- Syntax verification before writing
- Full L9/DORA compliance

Usage:
    python tools/codegen/docstring_injector.py                    # Dry run
    python tools/codegen/docstring_injector.py --apply            # Apply changes
    python tools/codegen/docstring_injector.py --file path/to.py  # Single file
    python tools/codegen/docstring_injector.py --limit 50         # Limit count
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 Docstring Injector",
    "module_version": "2.0.0",  # v2: AST-enriched context
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-29T12:00:00Z",
    "updated_at": "2026-01-31T09:00:00Z",
    "layer": "operations",
    "domain": "tools",
    "module_name": "docstring_injector",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from openai import OpenAI

logger = structlog.get_logger(__name__)

# Directories to skip during scanning
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    ".pytest_cache",
    "build",
    "dist",
    "tests",
    ".eggs",
}

# Files to skip
SKIP_FILES = {
    "__init__.py",  # Often intentionally empty or minimal
}


# =============================================================================
# AST Body Analysis Helpers (for enriched context)
# =============================================================================


def _extract_body_info(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
    """Extract raises, returns, and calls from function body via AST walk.

    Args:
        func_node: The function AST node to analyze.

    Returns:
        Dict with 'raises' (list), 'returns_value' (bool), 'calls_made' (list).
    """
    raises = set()
    returns_value = False
    calls = set()

    for node in ast.walk(func_node):
        # Find raise statements
        if isinstance(node, ast.Raise):
            if node.exc:
                if isinstance(node.exc, ast.Call):
                    if isinstance(node.exc.func, ast.Name):
                        raises.add(node.exc.func.id)
                    elif isinstance(node.exc.func, ast.Attribute):
                        raises.add(node.exc.func.attr)
                elif isinstance(node.exc, ast.Name):
                    raises.add(node.exc.id)

        # Find return statements with values
        if isinstance(node, ast.Return) and node.value is not None:
            returns_value = True

        # Find function calls (for context)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    return {
        "raises": sorted(raises),
        "returns_value": returns_value,
        "calls_made": sorted(calls)[:10],  # Limit to top 10
    }


def _extract_class_context(
    class_node: ast.ClassDef,
    method_name: str,
) -> dict:
    """Extract class-level context for a method.

    Args:
        class_node: The class AST node.
        method_name: Name of the method we're documenting.

    Returns:
        Dict with 'class_docstring', 'class_bases', 'sibling_methods'.
    """
    return {
        "class_docstring": ast.get_docstring(class_node),
        "class_bases": [
            ast.unparse(b) if hasattr(ast, "unparse") else "<base>"
            for b in class_node.bases
        ],
        "sibling_methods": [
            item.name
            for item in class_node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name != method_name
        ][:10],
    }


def _extract_decorator_flags(decorators: list[ast.expr]) -> dict:
    """Extract boolean flags from decorators.

    Args:
        decorators: List of decorator AST nodes.

    Returns:
        Dict with 'is_property', 'is_classmethod', 'is_staticmethod'.
    """
    is_property = False
    is_classmethod = False
    is_staticmethod = False

    for dec in decorators:
        if isinstance(dec, ast.Name):
            if dec.id == "property":
                is_property = True
            elif dec.id == "classmethod":
                is_classmethod = True
            elif dec.id == "staticmethod":
                is_staticmethod = True
        elif isinstance(dec, ast.Attribute):
            if dec.attr == "setter":
                is_property = True

    return {
        "is_property": is_property,
        "is_classmethod": is_classmethod,
        "is_staticmethod": is_staticmethod,
    }


def _extract_args_with_types(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[str, str | None]]:
    """Extract argument names with their type annotations.

    Args:
        func_node: The function AST node.

    Returns:
        List of (name, type_hint) tuples, excluding self/cls.
    """
    args_with_types = []
    for arg in func_node.args.args:
        if arg.arg not in ("self", "cls"):
            type_hint = ast.unparse(arg.annotation) if arg.annotation else None
            args_with_types.append((arg.arg, type_hint))
    return args_with_types


@dataclass
class MissingDocstring:
    """Represents a function/class missing a docstring with enriched AST context."""

    filepath: Path
    name: str
    node_type: str  # "function", "method", "class"
    lineno: int
    signature: str
    body_preview: str
    parent_class: str | None = None
    decorators: list[str] = field(default_factory=list)

    # === ENRICHED AST CONTEXT (v2) ===
    # Type information
    args_with_types: list[tuple[str, str | None]] = field(default_factory=list)
    return_type: str | None = None

    # Module/class context
    module_docstring: str | None = None
    class_docstring: str | None = None
    class_bases: list[str] = field(default_factory=list)

    # Code analysis from AST walk
    raises: list[str] = field(default_factory=list)
    returns_value: bool = False
    calls_made: list[str] = field(default_factory=list)

    # Decorator flags
    is_async: bool = False
    is_property: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False

    # Sibling context
    sibling_methods: list[str] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Generate enriched context string for LLM prompt.

        Returns:
            Formatted context string with full AST-extracted information.
        """
        lines = []

        # File context
        lines.append(f"**File:** {self.filepath.name}")
        if self.module_docstring:
            lines.append(f"**Module purpose:** {self.module_docstring[:200]}")

        # Type information
        lines.append(f"\n**Type:** {self.node_type}")
        lines.append(f"**Signature:** {self.signature}")

        # Class context (for methods)
        if self.parent_class:
            lines.append(f"\n**Class:** {self.parent_class}")
            if self.class_docstring:
                lines.append(f"**Class purpose:** {self.class_docstring[:150]}")
            if self.class_bases:
                lines.append(f"**Inherits from:** {', '.join(self.class_bases)}")
            if self.sibling_methods:
                lines.append(
                    f"**Sibling methods:** {', '.join(self.sibling_methods[:5])}"
                )

        # Decorators and flags
        if self.decorators:
            lines.append(f"\n**Decorators:** {', '.join(self.decorators)}")

        flags = []
        if self.is_async:
            flags.append("async")
        if self.is_property:
            flags.append("property")
        if self.is_classmethod:
            flags.append("classmethod")
        if self.is_staticmethod:
            flags.append("staticmethod")
        if flags:
            lines.append(f"**Flags:** {', '.join(flags)}")

        # Arguments with types
        if self.args_with_types:
            args_str = ", ".join(
                f"{name}: {typ}" if typ else name for name, typ in self.args_with_types
            )
            lines.append(f"\n**Arguments:** {args_str}")

        # Return type
        if self.return_type:
            lines.append(f"**Return type:** {self.return_type}")
        elif self.returns_value:
            lines.append("**Returns:** Yes (type not annotated)")

        # Exceptions raised
        if self.raises:
            lines.append(f"**Raises:** {', '.join(self.raises)}")

        # Functions called (for context)
        if self.calls_made:
            lines.append(f"**Calls:** {', '.join(self.calls_made[:8])}")

        # Body preview (truncated)
        lines.append(f"\n**Body preview:**\n{self.body_preview[:400]}")

        return "\n".join(lines)


@dataclass
class InjectionResult:
    """Result of a docstring injection attempt."""

    filepath: Path
    name: str
    lineno: int
    success: bool
    docstring: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert result to dictionary for JSON serialization.

        Returns:
            Dict with filepath, name, lineno, success, docstring, and error.
        """
        return {
            "filepath": str(self.filepath),
            "name": self.name,
            "lineno": self.lineno,
            "success": self.success,
            "docstring": self.docstring,
            "error": self.error,
        }


class DocstringScanner:
    """Scans Python files for missing docstrings using AST analysis."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize the scanner.

        Args:
            repo_root: Root directory of the repository to scan.
        """
        self.repo_root = repo_root
        self.missing: list[MissingDocstring] = []

    def scan_file(self, filepath: Path) -> list[MissingDocstring]:
        """Scan a single Python file for missing docstrings with enriched AST context.

        Args:
            filepath: Path to the Python file to scan.

        Returns:
            List of MissingDocstring objects with full AST-extracted context.
        """
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning("Failed to parse file", filepath=str(filepath), error=str(e))
            return []

        missing = []
        source_lines = source.splitlines()

        # Extract module-level docstring for context
        module_docstring = ast.get_docstring(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    missing.append(
                        self._create_missing(
                            filepath,
                            node,
                            "class",
                            source_lines,
                            parent_class=None,
                            class_node=None,
                            module_docstring=module_docstring,
                        )
                    )
                # Check methods within the class - pass class node for context
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not ast.get_docstring(item):
                            missing.append(
                                self._create_missing(
                                    filepath,
                                    item,
                                    "method",
                                    source_lines,
                                    parent_class=node.name,
                                    class_node=node,
                                    module_docstring=module_docstring,
                                )
                            )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (not methods)
                if not ast.get_docstring(node) and not self._is_method(node, tree):
                    missing.append(
                        self._create_missing(
                            filepath,
                            node,
                            "function",
                            source_lines,
                            parent_class=None,
                            class_node=None,
                            module_docstring=module_docstring,
                        )
                    )

        return missing

    def _is_method(self, func_node: ast.AST, tree: ast.Module) -> bool:
        """Check if a function node is a method inside a class.

        Args:
            func_node: The function node to check.
            tree: The full AST module.

        Returns:
            True if the function is inside a class, False otherwise.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if item is func_node:
                        return True
        return False

    def _create_missing(
        self,
        filepath: Path,
        node: ast.AST,
        node_type: str,
        source_lines: list[str],
        parent_class: str | None,
        class_node: ast.ClassDef | None = None,
        module_docstring: str | None = None,
    ) -> MissingDocstring:
        """Create a MissingDocstring object with enriched AST context.

        Args:
            filepath: Path to the source file.
            node: The AST node (function or class).
            node_type: Type of node ("function", "method", "class").
            source_lines: List of source code lines.
            parent_class: Name of parent class if this is a method.
            class_node: The parent class AST node (for extracting class context).
            module_docstring: Module-level docstring for context.

        Returns:
            MissingDocstring object with full AST-extracted information.
        """
        # Extract signature and decorators
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            signature = self._extract_function_signature(node)
            decorators = [self._decorator_to_str(d) for d in node.decorator_list]

            # Extract enriched context for functions/methods
            args_with_types = _extract_args_with_types(node)
            return_type = ast.unparse(node.returns) if node.returns else None
            body_info = _extract_body_info(node)
            decorator_flags = _extract_decorator_flags(node.decorator_list)
            is_async = isinstance(node, ast.AsyncFunctionDef)
        else:
            # Class node
            signature = f"class {node.name}"
            decorators = [self._decorator_to_str(d) for d in node.decorator_list]
            args_with_types = []
            return_type = None
            body_info = {"raises": [], "returns_value": False, "calls_made": []}
            decorator_flags = {
                "is_property": False,
                "is_classmethod": False,
                "is_staticmethod": False,
            }
            is_async = False

        # Extract body preview (first 15 lines of body)
        start_line = node.lineno - 1
        end_line = min(start_line + 15, len(source_lines))
        body_preview = "\n".join(source_lines[start_line:end_line])

        # Extract class context if this is a method
        class_context = {
            "class_docstring": None,
            "class_bases": [],
            "sibling_methods": [],
        }
        if class_node is not None:
            class_context = _extract_class_context(class_node, node.name)

        return MissingDocstring(
            filepath=filepath,
            name=node.name,
            node_type=node_type,
            lineno=node.lineno,
            signature=signature,
            body_preview=body_preview,
            parent_class=parent_class,
            decorators=decorators,
            # Enriched fields
            args_with_types=args_with_types,
            return_type=return_type,
            module_docstring=module_docstring,
            class_docstring=class_context["class_docstring"],
            class_bases=class_context["class_bases"],
            raises=body_info["raises"],
            returns_value=body_info["returns_value"],
            calls_made=body_info["calls_made"],
            is_async=is_async,
            is_property=decorator_flags["is_property"],
            is_classmethod=decorator_flags["is_classmethod"],
            is_staticmethod=decorator_flags["is_staticmethod"],
            sibling_methods=class_context["sibling_methods"],
        )

    def _extract_function_signature(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> str:
        """Extract function signature as a string.

        Args:
            node: The function AST node.

        Returns:
            String representation of the function signature.
        """
        args = []

        # Handle positional-only args (Python 3.8+)
        for arg in node.args.posonlyargs:
            args.append(self._format_arg(arg))
        if node.args.posonlyargs:
            args.append("/")

        # Regular args
        defaults_offset = len(node.args.args) - len(node.args.defaults)
        for i, arg in enumerate(node.args.args):
            arg_str = self._format_arg(arg)
            if i >= defaults_offset:
                arg_str += "=..."
            args.append(arg_str)

        # *args
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        elif node.args.kwonlyargs:
            args.append("*")

        # Keyword-only args
        kw_defaults_offset = len(node.args.kwonlyargs) - len(
            [d for d in node.args.kw_defaults if d is not None]
        )
        for i, arg in enumerate(node.args.kwonlyargs):
            arg_str = self._format_arg(arg)
            if node.args.kw_defaults[i] is not None:
                arg_str += "=..."
            args.append(arg_str)

        # **kwargs
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")

        # Return annotation
        return_annotation = ""
        if node.returns:
            return_annotation = f" -> {ast.unparse(node.returns)}"

        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({', '.join(args)}){return_annotation}"

    def _format_arg(self, arg: ast.arg) -> str:
        """Format a function argument with optional type annotation.

        Args:
            arg: The argument AST node.

        Returns:
            Formatted argument string.
        """
        if arg.annotation:
            return f"{arg.arg}: {ast.unparse(arg.annotation)}"
        return arg.arg

    def _decorator_to_str(self, decorator: ast.expr) -> str:
        """Convert a decorator AST node to string.

        Args:
            decorator: The decorator expression node.

        Returns:
            String representation of the decorator.
        """
        try:
            return ast.unparse(decorator)
        except Exception:
            return "@unknown"

    def scan_directory(
        self, scan_dirs: list[str] | None = None
    ) -> list[MissingDocstring]:
        """Scan directories for files with missing docstrings.

        Args:
            scan_dirs: List of directory names to scan (relative to repo_root).
                      If None, scans common L9 directories.

        Returns:
            List of all MissingDocstring objects found.
        """
        if scan_dirs is None:
            scan_dirs = [
                "agents",
                "api",
                "bootstrap",
                "ci",
                "codegenagent",
                "config",
                "core",
                "dev",
                "email_agent",
                "ir_engine",
                "mcp_memory",
                "memory",
                "orchestrators",
                "runtime",
                "scripts",
                "services",
                "tools",
                "workflows",
                "world_model",
            ]

        all_missing = []

        for scan_dir in scan_dirs:
            dir_path = self.repo_root / scan_dir
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                # Skip directories
                if any(skip in py_file.parts for skip in SKIP_DIRS):
                    continue
                # Skip specific files
                if py_file.name in SKIP_FILES:
                    continue
                # Skip test files
                if py_file.name.startswith("test_"):
                    continue

                file_missing = self.scan_file(py_file)
                all_missing.extend(file_missing)

        self.missing = all_missing
        return all_missing


class DocstringGenerator:
    """Generates docstrings using an LLM."""

    def __init__(self, model: str = "gpt-4.1-nano") -> None:
        """Initialize the generator.

        Args:
            model: OpenAI model to use for generation.
        """
        self.model = model
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        """Lazy-load the OpenAI client.

        Returns:
            Configured OpenAI client instance.
        """
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI()
        return self._client

    def generate_docstring(self, missing: MissingDocstring) -> str:
        """Generate a docstring for a missing docstring item.

        Args:
            missing: MissingDocstring object with context.

        Returns:
            Generated Google-style docstring (without triple quotes).
        """
        prompt = self._build_prompt(missing)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Python documentation expert. Generate concise Google-style docstrings.\n\n"
                            "CRITICAL FORMATTING RULES:\n"
                            "1. Return ONLY plain text - NO triple quotes, NO markdown\n"
                            "2. NO leading indentation on any line\n"
                            "3. NEVER include 'Args: None' or 'Returns: None' sections\n"
                            "4. Args/Returns sections ONLY if there are actual parameters/return values\n"
                            "5. Keep descriptions on single lines - no line breaks within a description\n"
                            "6. First line is always a brief one-sentence summary\n"
                            "7. Max 8 lines total"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,  # Lower temperature for more consistent formatting
                max_tokens=400,
            )
            docstring = response.choices[0].message.content.strip()
            # Remove any triple quotes if the model included them
            docstring = docstring.strip('"""').strip("'''").strip()
            return docstring
        except Exception as e:
            logger.error(
                "Failed to generate docstring", error=str(e), name=missing.name
            )
            raise

    def _build_prompt(self, missing: MissingDocstring) -> str:
        """Build LLM prompt with enriched AST context for high-quality docstring generation.

        Args:
            missing: MissingDocstring object with full AST-extracted context.

        Returns:
            Formatted prompt string optimized for domain-aware generation.
        """
        # Build structured context from enriched fields
        context_parts = []

        # File and module context
        context_parts.append("## CONTEXT (from AST analysis)\n")
        context_parts.append(f"**File:** {missing.filepath.name}")
        if missing.module_docstring:
            context_parts.append(
                f"**Module purpose:** {missing.module_docstring[:200]}"
            )

        # Signature
        context_parts.append(f"\n**Signature:** `{missing.signature}`")

        # Class context (critical for methods)
        if missing.parent_class:
            context_parts.append(f"\n**Class:** {missing.parent_class}")
            if missing.class_docstring:
                context_parts.append(
                    f"**Class purpose:** {missing.class_docstring[:150]}"
                )
            if missing.class_bases:
                context_parts.append(
                    f"**Inherits from:** {', '.join(missing.class_bases)}"
                )
            if missing.sibling_methods:
                context_parts.append(
                    f"**Sibling methods:** {', '.join(missing.sibling_methods[:5])}"
                )

        # Decorators and flags
        if missing.decorators:
            context_parts.append(f"\n**Decorators:** {', '.join(missing.decorators)}")

        flags = []
        if missing.is_async:
            flags.append("async")
        if missing.is_property:
            flags.append("property")
        if missing.is_classmethod:
            flags.append("classmethod")
        if missing.is_staticmethod:
            flags.append("staticmethod")
        if flags:
            context_parts.append(f"**Flags:** {', '.join(flags)}")

        # Arguments (with types from AST)
        if missing.args_with_types:
            args_lines = []
            for name, typ in missing.args_with_types:
                args_lines.append(f"  - `{name}`: {typ or 'untyped'}")
            context_parts.append("\n**Arguments:**\n" + "\n".join(args_lines))

        # Return info
        if missing.return_type and missing.return_type not in ("None", "NoReturn"):
            context_parts.append(f"**Return type:** `{missing.return_type}`")
        elif missing.returns_value:
            context_parts.append("**Returns:** Yes (type not annotated)")

        # Exceptions (from AST walk)
        if missing.raises:
            context_parts.append(f"**Raises:** {', '.join(missing.raises)}")

        # Functions called (helps LLM understand purpose)
        if missing.calls_made:
            context_parts.append(f"**Calls:** {', '.join(missing.calls_made[:8])}")

        # Body preview (truncated)
        context_parts.append(
            f"\n**Body preview:**\n```python\n{missing.body_preview[:300]}\n```"
        )

        context_str = "\n".join(context_parts)

        return f"""Generate a Google-style docstring for this Python {missing.node_type}.

{context_str}

## REQUIREMENTS

1. **First line:** Clear, specific description using domain context from the class/module
2. **Args:** Document each parameter with its purpose (NOT just type repetition)
3. **Returns:** Document return value if not None, include what the value represents
4. **Raises:** Document exceptions if any were detected in the body
5. **Keep it concise** - max 10 lines total
6. **NO triple quotes** in output - just the docstring content
7. **Use domain keywords** from class/module context for searchability

Example format:
Brief description using domain-specific terms.

Args:
    param1: What this parameter controls or represents.
    param2: Purpose of this parameter.

Returns:
    What the return value represents in the domain context.

Raises:
    ExceptionType: When this exception is raised.
"""


class DocstringInjector:
    """Injects generated docstrings into Python source files."""

    def __init__(
        self,
        scanner: DocstringScanner,
        generator: DocstringGenerator,
        dry_run: bool = True,
    ) -> None:
        """Initialize the injector.

        Args:
            scanner: DocstringScanner instance for finding missing docstrings.
            generator: DocstringGenerator instance for creating docstrings.
            dry_run: If True, only preview changes without modifying files.
        """
        self.scanner = scanner
        self.generator = generator
        self.dry_run = dry_run
        self.results: list[InjectionResult] = []

    def inject_docstring(
        self, missing: MissingDocstring, docstring: str
    ) -> InjectionResult:
        """Inject a docstring into a source file.

        Args:
            missing: MissingDocstring object identifying where to inject.
            docstring: The docstring content to inject.

        Returns:
            InjectionResult indicating success or failure.
        """
        try:
            source = missing.filepath.read_text(encoding="utf-8")
            lines = source.splitlines(keepends=True)

            # Find the line with the function/class definition
            def_line_idx = missing.lineno - 1

            # Find the colon and determine indentation
            def_line = lines[def_line_idx]

            # Handle multi-line signatures - find the function/class closing colon
            # Track parentheses balance to find the actual end of signature
            colon_line_idx = def_line_idx
            paren_balance = 0
            found_open_paren = False

            while colon_line_idx < len(lines):
                line_content = lines[colon_line_idx]

                # Count parentheses (ignore those in strings/comments for simplicity)
                for char in line_content:
                    if char == "(":
                        paren_balance += 1
                        found_open_paren = True
                    elif char == ")":
                        paren_balance -= 1

                line_stripped = line_content.rstrip()

                # Found the signature end: line ends with colon and parens are balanced
                if line_stripped.endswith(":"):
                    if not found_open_paren:
                        # Simple signature like "class Foo:" or "def bar():"
                        break
                    if paren_balance <= 0:
                        # Multi-line signature complete, parens balanced
                        break

                colon_line_idx += 1

            if colon_line_idx >= len(lines):
                return InjectionResult(
                    filepath=missing.filepath,
                    name=missing.name,
                    lineno=missing.lineno,
                    success=False,
                    error="Could not find end of signature",
                )

            # Calculate indentation (body indentation)
            next_line_idx = colon_line_idx + 1
            if next_line_idx < len(lines):
                next_line = lines[next_line_idx]
                # Get indentation of the next non-empty line
                while next_line_idx < len(lines) and not next_line.strip():
                    next_line_idx += 1
                    if next_line_idx < len(lines):
                        next_line = lines[next_line_idx]

                indent = len(next_line) - len(next_line.lstrip())
            else:
                # Default to 4 spaces more than the def line
                indent = len(def_line) - len(def_line.lstrip()) + 4

            indent_str = " " * indent

            # Format the docstring
            formatted_docstring = self._format_docstring(docstring, indent_str)

            # Insert after the colon line
            insert_idx = colon_line_idx + 1
            lines.insert(insert_idx, formatted_docstring)

            new_source = "".join(lines)

            # Verify syntax
            try:
                ast.parse(new_source)
            except SyntaxError as e:
                return InjectionResult(
                    filepath=missing.filepath,
                    name=missing.name,
                    lineno=missing.lineno,
                    success=False,
                    docstring=docstring,
                    error=f"Syntax error after injection: {e}",
                )

            # Write if not dry run
            if not self.dry_run:
                missing.filepath.write_text(new_source, encoding="utf-8")

            return InjectionResult(
                filepath=missing.filepath,
                name=missing.name,
                lineno=missing.lineno,
                success=True,
                docstring=docstring,
            )

        except Exception as e:
            return InjectionResult(
                filepath=missing.filepath,
                name=missing.name,
                lineno=missing.lineno,
                success=False,
                error=str(e),
            )

    def _format_docstring(self, docstring: str, indent: str) -> str:
        """Format a docstring with proper indentation and quotes.

        Args:
            docstring: Raw docstring content.
            indent: Indentation string to use.

        Returns:
            Formatted docstring with triple quotes and proper indentation.
        """
        # Clean up LLM output artifacts
        docstring = self._clean_docstring(docstring)

        lines = docstring.strip().splitlines()

        if len(lines) == 1:
            # Single-line docstring
            return f'{indent}"""{lines[0].strip()}"""\n'

        # Multi-line docstring - normalize indentation
        # First, dedent all lines to remove any LLM-added indentation
        dedented_lines = []
        for line in lines:
            stripped = line.strip()
            dedented_lines.append(stripped)

        # Now apply consistent indentation based on content
        formatted_lines = [f'{indent}"""']
        for line in dedented_lines:
            if not line:
                formatted_lines.append("")
            elif line.startswith(
                (
                    "Args:",
                    "Returns:",
                    "Raises:",
                    "Yields:",
                    "Examples:",
                    "Example:",
                    "Note:",
                    "Notes:",
                    "Attributes:",
                    "Warning:",
                    "Warnings:",
                )
            ):
                # Section headers - no extra indent
                formatted_lines.append(f"{indent}{line}")
            elif dedented_lines.index(line) > 0 and any(
                dedented_lines[dedented_lines.index(line) - 1].startswith(prefix)
                for prefix in ("Args:", "Returns:", "Raises:", "Yields:", "Attributes:")
            ):
                # First line after section header - add one level of indent
                formatted_lines.append(f"{indent}    {line}")
            elif len(formatted_lines) > 1 and formatted_lines[-1].strip().endswith(":"):
                # Line after a colon (like a section header or param) - indent
                formatted_lines.append(f"{indent}    {line}")
            elif len(formatted_lines) > 1 and formatted_lines[-1].startswith(
                f"{indent}    "
            ):
                # Continue indentation from previous indented line
                formatted_lines.append(f"{indent}    {line}")
            else:
                # Regular line
                formatted_lines.append(f"{indent}{line}")

        formatted_lines.append(f'{indent}"""')

        return "\n".join(formatted_lines) + "\n"

    def _clean_docstring(self, docstring: str) -> str:
        """Clean up LLM-generated docstring artifacts.

        Args:
            docstring: Raw docstring from LLM.

        Returns:
            Cleaned docstring with consistent formatting.
        """
        # Remove any triple quotes the LLM might have included
        docstring = docstring.strip('"""').strip("'''").strip()

        # Remove markdown-style trailing spaces
        lines = docstring.splitlines()
        cleaned_lines = [line.rstrip() for line in lines]

        # Remove "Args:  \n    None" patterns - they're noise
        result_lines = []
        skip_next = False
        for i, line in enumerate(cleaned_lines):
            if skip_next:
                skip_next = False
                continue
            stripped = line.strip()
            # Skip "None" or "N/A" as standalone arg/return descriptions
            if stripped in ("None", "N/A", "None.", "N/A."):
                # Check if this follows an "Args:" or "Returns:" with nothing after
                if i > 0 and cleaned_lines[i - 1].strip() in (
                    "Args:",
                    "Returns:",
                    "Raises:",
                ):
                    # Remove the section header too
                    if result_lines and result_lines[-1].strip() in (
                        "Args:",
                        "Returns:",
                        "Raises:",
                    ):
                        result_lines.pop()
                continue
            # Skip empty sections like "Returns:\n    None"
            if stripped in ("Args:", "Returns:", "Raises:"):
                # Check if next line is just "None"
                if i + 1 < len(cleaned_lines) and cleaned_lines[i + 1].strip() in (
                    "None",
                    "N/A",
                    "None.",
                    "N/A.",
                ):
                    skip_next = True
                    continue
            result_lines.append(line)

        return "\n".join(result_lines)

    def process_batch(
        self, missing_list: list[MissingDocstring], limit: int | None = None
    ) -> list[InjectionResult]:
        """Process a batch of missing docstrings.

        Groups items by file and processes in reverse line order to avoid
        line number invalidation from earlier injections.

        Args:
            missing_list: List of MissingDocstring objects to process.
            limit: Maximum number of items to process.

        Returns:
            List of InjectionResult objects.
        """
        if limit:
            missing_list = missing_list[:limit]

        # Group by file and sort by line number (descending within each file)
        # This ensures injections don't shift line numbers for subsequent items
        from collections import defaultdict

        by_file: dict[Path, list[MissingDocstring]] = defaultdict(list)
        for missing in missing_list:
            by_file[missing.filepath].append(missing)

        # Sort each file's items by line number descending (process bottom-up)
        for filepath in by_file:
            by_file[filepath].sort(key=lambda m: m.lineno, reverse=True)

        # Flatten back to a list, maintaining file grouping
        ordered_list = []
        for filepath in by_file:
            ordered_list.extend(by_file[filepath])

        results = []
        total = len(ordered_list)

        for i, missing in enumerate(ordered_list, 1):
            logger.info(
                "Processing",
                progress=f"{i}/{total}",
                file=str(missing.filepath.relative_to(self.scanner.repo_root)),
                name=missing.name,
            )

            try:
                docstring = self.generator.generate_docstring(missing)
                result = self.inject_docstring(missing, docstring)
            except Exception as e:
                result = InjectionResult(
                    filepath=missing.filepath,
                    name=missing.name,
                    lineno=missing.lineno,
                    success=False,
                    error=str(e),
                )

            results.append(result)
            self.results.append(result)

            if result.success:
                logger.info("Injected docstring", name=missing.name)
            else:
                logger.warning(
                    "Failed to inject", name=missing.name, error=result.error
                )

        return results

    def generate_report(self) -> str:
        """Generate a summary report of injection results.

        Returns:
            Formatted report string.
        """
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful

        lines = [
            "=" * 70,
            "DOCSTRING INJECTION REPORT",
            "=" * 70,
            "",
            f"Mode: {'DRY RUN' if self.dry_run else 'APPLIED'}",
            f"Total processed: {total}",
            f"Successful: {successful}",
            f"Failed: {failed}",
            "",
        ]

        if failed > 0:
            lines.append("FAILURES:")
            for result in self.results:
                if not result.success:
                    lines.append(
                        f"  - {result.filepath}:{result.lineno} {result.name}: {result.error}"
                    )
            lines.append("")

        if self.dry_run and successful > 0:
            lines.append("PREVIEW (first 5 successful):")
            for result in [r for r in self.results if r.success][:5]:
                lines.append(f"\n  {result.filepath}:{result.lineno} {result.name}")
                lines.append(f"  Docstring: {result.docstring[:100]}...")
            lines.append("")

        return "\n".join(lines)


def main() -> int:
    """CLI entry point for docstring injection.

    Parses arguments and orchestrates the docstring injection process.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description="Inject Google-style docstrings into Python files"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Process a single file instead of scanning directories",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of docstrings to generate",
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1-nano",
        help="OpenAI model to use (default: gpt-4.1-nano)",
    )
    parser.add_argument(
        "--dirs",
        nargs="+",
        help="Directories to scan (default: common L9 directories)",
    )

    args = parser.parse_args()

    # Determine repo root
    repo_root = Path(__file__).parent.parent.parent
    if not (repo_root / "pyproject.toml").exists():
        repo_root = Path.cwd()

    logger.info("Starting docstring injection", repo_root=str(repo_root))

    # Initialize components
    scanner = DocstringScanner(repo_root)
    generator = DocstringGenerator(model=args.model)
    injector = DocstringInjector(scanner, generator, dry_run=not args.apply)

    # Scan for missing docstrings
    if args.file:
        file_path = args.file.resolve()
        if not file_path.exists():
            logger.error("File not found", file=str(args.file))
            return 1
        missing = scanner.scan_file(file_path)
    else:
        missing = scanner.scan_directory(args.dirs)

    logger.info("Scan complete", missing_count=len(missing))

    if not missing:
        logger.info("No missing docstrings found!")
        return 0

    # Process
    injector.process_batch(missing, limit=args.limit)

    # Report
    report = injector.generate_report()
    print(report)

    # Validation step - verify quality of injected docstrings
    if args.apply and injector.results:
        print("\n" + "=" * 70)
        print("VALIDATION: Checking quality of injected docstrings")
        print("=" * 70)

        validation_results = validate_injected_docstrings(injector.results, repo_root)
        print(validation_results)

    return 0


def validate_injected_docstrings(
    results: list[InjectionResult], repo_root: Path
) -> str:
    """Validate quality of injected docstrings.

    Args:
        results: List of injection results to validate.
        repo_root: Root directory of the repository.

    Returns:
        Validation report string.
    """
    successful = [r for r in results if r.success]
    if not successful:
        return "No successful injections to validate."

    # Quality metrics
    metrics = {
        "total_validated": 0,
        "has_first_line": 0,
        "has_args": 0,
        "has_returns": 0,
        "proper_length": 0,  # 1-10 lines
        "syntax_valid": 0,
        "quality_scores": [],
    }

    issues = []

    for result in successful[:20]:  # Validate first 20
        if not result.docstring:
            continue

        metrics["total_validated"] += 1
        score = 0
        docstring = result.docstring
        lines = docstring.strip().splitlines()

        # Check first line exists and is brief
        if lines and len(lines[0]) < 200:
            metrics["has_first_line"] += 1
            score += 30
        else:
            issues.append(f"{result.name}: Missing or overly long first line")

        # Check for Args section when appropriate
        if "Args:" in docstring:
            metrics["has_args"] += 1
            score += 20

        # Check for Returns section
        if "Returns:" in docstring:
            metrics["has_returns"] += 1
            score += 20

        # Check length (1-10 lines is ideal)
        if 1 <= len(lines) <= 10:
            metrics["proper_length"] += 1
            score += 15
        elif len(lines) > 10:
            issues.append(f"{result.name}: Docstring too long ({len(lines)} lines)")

        # Verify file still has valid syntax
        try:
            source = result.filepath.read_text()
            ast.parse(source)
            metrics["syntax_valid"] += 1
            score += 15
        except SyntaxError:
            issues.append(f"{result.name}: File has syntax error after injection!")
            score -= 50

        metrics["quality_scores"].append(score)

    # Calculate averages
    total = metrics["total_validated"]
    if total == 0:
        return "No docstrings to validate."

    avg_score = (
        sum(metrics["quality_scores"]) / len(metrics["quality_scores"])
        if metrics["quality_scores"]
        else 0
    )

    report_lines = [
        f"\nValidated: {total} docstrings",
        "",
        "Quality Metrics:",
        f"  - Has clear first line:  {metrics['has_first_line']}/{total} ({metrics['has_first_line'] * 100 // total}%)",
        f"  - Has Args section:      {metrics['has_args']}/{total} ({metrics['has_args'] * 100 // total}%)",
        f"  - Has Returns section:   {metrics['has_returns']}/{total} ({metrics['has_returns'] * 100 // total}%)",
        f"  - Proper length (1-10):  {metrics['proper_length']}/{total} ({metrics['proper_length'] * 100 // total}%)",
        f"  - Syntax valid:          {metrics['syntax_valid']}/{total} ({metrics['syntax_valid'] * 100 // total}%)",
        "",
        f"Average Quality Score: {avg_score:.1f}/100",
        "",
    ]

    if avg_score >= 90:
        report_lines.append("✅ EXCELLENT - Docstrings are high quality")
    elif avg_score >= 75:
        report_lines.append("✅ GOOD - Docstrings meet quality standards")
    elif avg_score >= 60:
        report_lines.append("⚠️  ACCEPTABLE - Some improvements needed")
    else:
        report_lines.append("❌ NEEDS WORK - Quality below standards")

    if issues:
        report_lines.append(f"\nIssues found ({len(issues)}):")
        for issue in issues[:10]:
            report_lines.append(f"  - {issue}")
        if len(issues) > 10:
            report_lines.append(f"  ... and {len(issues) - 10} more")

    return "\n".join(report_lines)


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "TOO-OPER-DOCSTRING-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["openai", "structlog"],
    "tags": [
        "ast",
        "automation",
        "cli",
        "codegen",
        "documentation",
        "llm",
        "operations",
        "tools",
    ],
    "keywords": [
        "docstring",
        "generate",
        "inject",
        "python",
        "scanner",
        "ast",
        "llm",
    ],
    "business_value": "Automates docstring generation for Python files using LLM, "
    "ensuring consistent documentation across the L9 codebase.",
    "last_modified": "2026-01-29T12:00:00Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial implementation with AST scanning and LLM generation",
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
