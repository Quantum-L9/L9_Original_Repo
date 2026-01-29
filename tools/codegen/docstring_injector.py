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
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2026-01-29T12:00:00Z",
    "updated_at": "2026-01-29T12:00:00Z",
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
import os
import sys
import textwrap
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


@dataclass
class MissingDocstring:
    """Represents a function/class missing a docstring."""

    filepath: Path
    name: str
    node_type: str  # "function", "method", "class"
    lineno: int
    signature: str
    body_preview: str
    parent_class: str | None = None
    decorators: list[str] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Generate context string for LLM prompt.

        Returns:
            Formatted context string with signature and body preview.
        """
        context = f"Type: {self.node_type}\n"
        if self.parent_class:
            context += f"Class: {self.parent_class}\n"
        if self.decorators:
            context += f"Decorators: {', '.join(self.decorators)}\n"
        context += f"Signature: {self.signature}\n"
        context += f"Body preview:\n{self.body_preview}"
        return context


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
        """Scan a single Python file for missing docstrings.

        Args:
            filepath: Path to the Python file to scan.

        Returns:
            List of MissingDocstring objects for items without docstrings.
        """
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning("Failed to parse file", filepath=str(filepath), error=str(e))
            return []

        missing = []
        source_lines = source.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    missing.append(
                        self._create_missing(
                            filepath, node, "class", source_lines, None
                        )
                    )
                # Check methods within the class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not ast.get_docstring(item):
                            missing.append(
                                self._create_missing(
                                    filepath, item, "method", source_lines, node.name
                                )
                            )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (not methods)
                if not ast.get_docstring(node) and not self._is_method(node, tree):
                    missing.append(
                        self._create_missing(
                            filepath, node, "function", source_lines, None
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
    ) -> MissingDocstring:
        """Create a MissingDocstring object from an AST node.

        Args:
            filepath: Path to the source file.
            node: The AST node (function or class).
            node_type: Type of node ("function", "method", "class").
            source_lines: List of source code lines.
            parent_class: Name of parent class if this is a method.

        Returns:
            MissingDocstring object with extracted information.
        """
        # Extract signature
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            signature = self._extract_function_signature(node)
            decorators = [
                self._decorator_to_str(d) for d in node.decorator_list
            ]
        else:
            signature = f"class {node.name}"
            decorators = [
                self._decorator_to_str(d) for d in node.decorator_list
            ]

        # Extract body preview (first 10 lines of body)
        start_line = node.lineno - 1
        end_line = min(start_line + 15, len(source_lines))
        body_preview = "\n".join(source_lines[start_line:end_line])

        return MissingDocstring(
            filepath=filepath,
            name=node.name,
            node_type=node_type,
            lineno=node.lineno,
            signature=signature,
            body_preview=body_preview,
            parent_class=parent_class,
            decorators=decorators,
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
                            "You are a Python documentation expert. Generate concise, "
                            "accurate Google-style docstrings. Return ONLY the docstring "
                            "content without triple quotes. Include Args, Returns, and "
                            "Raises sections only when applicable. Be precise and brief."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            docstring = response.choices[0].message.content.strip()
            # Remove any triple quotes if the model included them
            docstring = docstring.strip('"""').strip("'''").strip()
            return docstring
        except Exception as e:
            logger.error("Failed to generate docstring", error=str(e), name=missing.name)
            raise

    def _build_prompt(self, missing: MissingDocstring) -> str:
        """Build the LLM prompt for docstring generation.

        Args:
            missing: MissingDocstring object with context.

        Returns:
            Formatted prompt string.
        """
        return f"""Generate a Google-style docstring for the following Python {missing.node_type}.

{missing.to_prompt_context()}

Requirements:
1. First line: Brief one-sentence description
2. Args section: Only if there are parameters (exclude self/cls)
3. Returns section: Only if the function returns something meaningful
4. Raises section: Only if exceptions are explicitly raised
5. Keep it concise - no more than 10 lines total
6. Do NOT include the triple quotes

Example format:
Brief description of what this does.

Args:
    param1: Description of param1.
    param2: Description of param2.

Returns:
    Description of return value.
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
            
            # Handle multi-line signatures
            colon_line_idx = def_line_idx
            while ":" not in lines[colon_line_idx] or lines[colon_line_idx].rstrip().endswith(","):
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
        lines = docstring.strip().splitlines()
        
        if len(lines) == 1:
            # Single-line docstring
            return f'{indent}"""{lines[0]}"""\n'
        
        # Multi-line docstring
        formatted_lines = [f'{indent}"""']
        for line in lines:
            if line.strip():
                formatted_lines.append(f"{indent}{line}")
            else:
                formatted_lines.append("")
        formatted_lines.append(f'{indent}"""')
        
        return "\n".join(formatted_lines) + "\n"

    def process_batch(
        self, missing_list: list[MissingDocstring], limit: int | None = None
    ) -> list[InjectionResult]:
        """Process a batch of missing docstrings.

        Args:
            missing_list: List of MissingDocstring objects to process.
            limit: Maximum number of items to process.

        Returns:
            List of InjectionResult objects.
        """
        if limit:
            missing_list = missing_list[:limit]

        results = []
        total = len(missing_list)

        for i, missing in enumerate(missing_list, 1):
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

    return 0


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
