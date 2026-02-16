#!/usr/bin/env python3
"""
A/B Test: AST-Only vs AST+LLM Docstring Generation

Tests whether LLM adds value over pure AST-based template generation.

Usage:
    python tools/codegen/docstring_ab_test.py
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import structlog

# Add project root to path

logger = structlog.get_logger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.superpack_reports.ast_scanner import (
    scan_module,
)

# =============================================================================
# Enhanced AST Context Extraction
# =============================================================================


@dataclass
class EnrichedContext:
    """Rich context extracted from AST for docstring generation."""

    # Basic info
    name: str
    node_type: str  # "function", "method", "class"
    signature: str
    lineno: int
    filepath: Path

    # Type information
    args_with_types: list[tuple[str, str | None]]  # (name, type_hint)
    return_type: str | None

    # Context
    module_docstring: str | None
    class_name: str | None
    class_docstring: str | None
    class_bases: list[str]

    # Code analysis
    decorators: list[str]
    is_async: bool
    is_property: bool
    is_classmethod: bool
    is_staticmethod: bool

    # Body analysis (from AST walk)
    raises: list[str] = field(default_factory=list)
    returns_value: bool = False
    calls_made: list[str] = field(default_factory=list)

    # Sibling context
    sibling_methods: list[str] = field(default_factory=list)


def extract_body_info(
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, Any]:
    """Extract raises, returns, and calls from function body."""
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

        # Find function calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    return {
        "raises": list(raises),
        "returns_value": returns_value,
        "calls_made": list(calls)[:10],  # Limit to top 10
    }


def extract_enriched_context(
    filepath: Path,
    func_name: str,
    class_name: str | None = None,
) -> EnrichedContext | None:
    """Extract rich context for a specific function/method."""

    module_info = scan_module(filepath, filepath.parent.parent)
    if not module_info:
        return None

    # Parse AST again for detailed body analysis
    try:
        source = filepath.read_text()
        tree = ast.parse(source)
    except Exception:
        return None

    # Find the target function
    target_node = None
    parent_class = None

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and class_name and node.name == class_name:
            parent_class = node
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == func_name:
                        target_node = item
                        break
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name and class_name is None:
                target_node = node
                break

    if not target_node:
        return None

    # Extract args with types
    args_with_types = []
    for arg in target_node.args.args:
        if arg.arg not in ("self", "cls"):
            type_hint = ast.unparse(arg.annotation) if arg.annotation else None
            args_with_types.append((arg.arg, type_hint))

    # Extract decorators
    decorators = []
    is_property = False
    is_classmethod = False
    is_staticmethod = False

    for dec in target_node.decorator_list:
        if isinstance(dec, ast.Name):
            decorators.append(dec.id)
            if dec.id == "property":
                is_property = True
            elif dec.id == "classmethod":
                is_classmethod = True
            elif dec.id == "staticmethod":
                is_staticmethod = True
        elif isinstance(dec, ast.Attribute):
            decorators.append(dec.attr)
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)
            elif isinstance(dec.func, ast.Attribute):
                decorators.append(dec.func.attr)

    # Get return type
    return_type = ast.unparse(target_node.returns) if target_node.returns else None

    # Get body info
    body_info = extract_body_info(target_node)

    # Get class context
    class_docstring = None
    class_bases = []
    sibling_methods = []

    if parent_class:
        class_docstring = ast.get_docstring(parent_class)
        class_bases = [ast.unparse(b) for b in parent_class.bases]
        sibling_methods = [
            item.name
            for item in parent_class.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name != func_name
        ][:10]

    # Build signature
    sig_parts = []
    for arg, typ in args_with_types:
        if typ:
            sig_parts.append(f"{arg}: {typ}")
        else:
            sig_parts.append(arg)

    prefix = "async def" if isinstance(target_node, ast.AsyncFunctionDef) else "def"
    sig = f"{prefix} {func_name}({', '.join(sig_parts)})"
    if return_type:
        sig += f" -> {return_type}"

    return EnrichedContext(
        name=func_name,
        node_type="method" if class_name else "function",
        signature=sig,
        lineno=target_node.lineno,
        filepath=filepath,
        args_with_types=args_with_types,
        return_type=return_type,
        module_docstring=module_info.docstring,
        class_name=class_name,
        class_docstring=class_docstring,
        class_bases=class_bases,
        decorators=decorators,
        is_async=isinstance(target_node, ast.AsyncFunctionDef),
        is_property=is_property,
        is_classmethod=is_classmethod,
        is_staticmethod=is_staticmethod,
        raises=body_info["raises"],
        returns_value=body_info["returns_value"],
        calls_made=body_info["calls_made"],
        sibling_methods=sibling_methods,
    )


# =============================================================================
# OPTION A: AST-Only Docstring Generator (No LLM)
# =============================================================================


def generate_docstring_ast_only(ctx: EnrichedContext) -> str:
    """Generate docstring using only AST-extracted information."""

    lines = []

    # First line: describe what it does based on name and context
    action_verb = _infer_action_verb(ctx.name, ctx)
    subject = _infer_subject(ctx)

    if ctx.is_property:
        lines.append(f"Returns the {_name_to_readable(ctx.name)}.")
    elif ctx.name == "__init__":
        lines.append(
            f"Initialize {ctx.class_name or 'the instance'} with the given parameters."
        )
    elif ctx.name == "to_dict":
        lines.append(
            f"Convert {ctx.class_name or 'the instance'} to a dictionary representation."
        )
    elif ctx.name == "__str__" or ctx.name == "__repr__":
        lines.append(
            f"Return string representation of {ctx.class_name or 'the instance'}."
        )
    elif ctx.name.startswith("get_"):
        lines.append(f"Retrieve {_name_to_readable(ctx.name[4:])}.")
    elif ctx.name.startswith("set_"):
        lines.append(f"Set {_name_to_readable(ctx.name[4:])}.")
    elif ctx.name.startswith("is_") or ctx.name.startswith("has_"):
        lines.append(f"Check if {_name_to_readable(ctx.name)}.")
    elif ctx.name.startswith("validate"):
        lines.append(f"Validate {subject}.")
    elif ctx.name.startswith("create"):
        lines.append(f"Create {subject}.")
    elif ctx.name.startswith("delete") or ctx.name.startswith("remove"):
        lines.append(f"Remove {subject}.")
    elif ctx.name.startswith("update"):
        lines.append(f"Update {subject}.")
    else:
        lines.append(f"{action_verb.capitalize()} {subject}.")

    # Add class context if available
    if ctx.class_name and ctx.class_bases:
        if "BaseModel" in ctx.class_bases:
            lines[0] = lines[0].rstrip(".") + " (Pydantic model)."
        elif "ABC" in ctx.class_bases or any("Abstract" in b for b in ctx.class_bases):
            lines[0] = lines[0].rstrip(".") + " (abstract method)."

    # Args section
    if ctx.args_with_types:
        lines.append("")
        lines.append("Args:")
        for arg_name, arg_type in ctx.args_with_types:
            if arg_type:
                lines.append(f"    {arg_name}: {_type_to_description(arg_type)}")
            else:
                lines.append(f"    {arg_name}: The {_name_to_readable(arg_name)}.")

    # Returns section
    if ctx.return_type and ctx.return_type not in ("None", "NoReturn"):
        lines.append("")
        lines.append("Returns:")
        lines.append(f"    {_type_to_description(ctx.return_type)}")
    elif ctx.returns_value and not ctx.is_property:
        lines.append("")
        lines.append("Returns:")
        lines.append("    The result of the operation.")

    # Raises section
    if ctx.raises:
        lines.append("")
        lines.append("Raises:")
        for exc in ctx.raises:
            lines.append(f"    {exc}: If {_exception_to_reason(exc)}.")

    return "\n".join(lines)


def _infer_action_verb(name: str, ctx: EnrichedContext) -> str:
    """Infer action verb from function name."""
    if ctx.is_async:
        prefix = "asynchronously "
    else:
        prefix = ""

    verbs = {
        "get": f"{prefix}retrieve",
        "set": f"{prefix}set",
        "create": f"{prefix}create",
        "delete": f"{prefix}delete",
        "update": f"{prefix}update",
        "validate": f"{prefix}validate",
        "process": f"{prefix}process",
        "handle": f"{prefix}handle",
        "build": f"{prefix}build",
        "parse": f"{prefix}parse",
        "convert": f"{prefix}convert",
        "format": f"{prefix}format",
        "check": f"{prefix}check",
        "load": f"{prefix}load",
        "save": f"{prefix}save",
        "send": f"{prefix}send",
        "receive": f"{prefix}receive",
        "fetch": f"{prefix}fetch",
        "compute": f"{prefix}compute",
        "calculate": f"{prefix}calculate",
        "run": f"{prefix}execute",
        "execute": f"{prefix}execute",
        "init": f"{prefix}initialize",
    }

    for prefix_word, verb in verbs.items():
        if name.startswith(prefix_word):
            return verb

    return f"{prefix}perform"


def _infer_subject(ctx: EnrichedContext) -> str:
    """Infer the subject/object of the function."""
    name = ctx.name

    # Remove common prefixes
    for prefix in (
        "get_",
        "set_",
        "create_",
        "delete_",
        "update_",
        "validate_",
        "process_",
        "handle_",
        "build_",
        "parse_",
        "is_",
        "has_",
    ):
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    # Convert to readable
    readable = _name_to_readable(name)

    # Add class context
    if ctx.class_name:
        return f"{readable} for {ctx.class_name}"

    return readable


def _name_to_readable(name: str) -> str:
    """Convert snake_case name to readable phrase."""
    return name.replace("_", " ").lower()


def _type_to_description(type_str: str) -> str:
    """Convert type annotation to description."""
    descriptions = {
        "str": "String value.",
        "int": "Integer value.",
        "float": "Floating point value.",
        "bool": "Boolean flag.",
        "None": "None.",
        "list": "List of items.",
        "dict": "Dictionary mapping.",
        "Any": "Value of any type.",
        "Path": "File system path.",
    }

    # Check for exact match
    if type_str in descriptions:
        return descriptions[type_str]

    # Check for generic types
    if type_str.startswith("list["):
        inner = type_str[5:-1]
        return f"List of {inner} items."
    if type_str.startswith("dict["):
        return f"Dictionary with {type_str[5:-1]}."
    if type_str.startswith("Optional["):
        inner = type_str[9:-1]
        return f"Optional {inner}, or None."
    if "|" in type_str and "None" in type_str:
        non_none = type_str.replace(" | None", "").replace("None | ", "")
        return f"{non_none} or None."

    return f"{type_str} instance."


def _exception_to_reason(exc: str) -> str:
    """Convert exception name to reason phrase."""
    reasons = {
        "ValueError": "the value is invalid",
        "TypeError": "the type is incorrect",
        "KeyError": "the key is not found",
        "AttributeError": "the attribute is missing",
        "RuntimeError": "a runtime error occurs",
        "IOError": "an I/O error occurs",
        "FileNotFoundError": "the file is not found",
        "PermissionError": "permission is denied",
        "TimeoutError": "the operation times out",
        "ConnectionError": "the connection fails",
    }
    return reasons.get(exc, "an error occurs")


# =============================================================================
# OPTION B: AST+LLM Docstring Generator
# =============================================================================


def generate_docstring_ast_llm(ctx: EnrichedContext) -> str:
    """Generate docstring using AST context + LLM."""

    try:
        from openai import OpenAI

        client = OpenAI()
    except ImportError:
        return "[LLM unavailable - openai not installed]"
    except Exception as e:
        return f"[LLM error: {e}]"

    # Build enriched prompt
    prompt = f"""Generate a Google-style docstring for this Python {ctx.node_type}.

## CONTEXT (from AST analysis)

**File:** {ctx.filepath.name}
**Module purpose:** {ctx.module_docstring[:200] if ctx.module_docstring else "N/A"}

**Signature:** {ctx.signature}

**Class context:** {ctx.class_name or "N/A"}
**Class purpose:** {ctx.class_docstring[:150] if ctx.class_docstring else "N/A"}
**Inherits from:** {", ".join(ctx.class_bases) if ctx.class_bases else "N/A"}
**Sibling methods:** {", ".join(ctx.sibling_methods[:5]) if ctx.sibling_methods else "N/A"}

**Decorators:** {", ".join(ctx.decorators) if ctx.decorators else "None"}
**Is async:** {ctx.is_async}
**Is property:** {ctx.is_property}

**Arguments:**
{chr(10).join(f"  - {name}: {typ or 'untyped'}" for name, typ in ctx.args_with_types) or "  None"}

**Return type:** {ctx.return_type or "N/A"}
**Returns value:** {ctx.returns_value}

**Raises exceptions:** {", ".join(ctx.raises) if ctx.raises else "None detected"}

**Calls these functions:** {", ".join(ctx.calls_made[:5]) if ctx.calls_made else "N/A"}

## REQUIREMENTS

1. First line: Clear, specific description using domain context
2. Args: Document each parameter with its purpose (skip self/cls)
3. Returns: Document return value if not None
4. Raises: Document exceptions if any
5. Keep under 10 lines total
6. NO triple quotes in output

## OUTPUT

Return ONLY the docstring content:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Python documentation expert. Generate precise, context-aware docstrings.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        docstring = response.choices[0].message.content.strip()
        return docstring.strip('"""').strip("'''").strip()
    except Exception as e:
        return f"[LLM error: {e}]"


# =============================================================================
# A/B Test Runner
# =============================================================================


@dataclass
class ABTestResult:
    """Result of A/B comparison."""

    filepath: str
    name: str
    class_name: str | None

    docstring_ast: str
    docstring_llm: str

    # Scores (manual or automated)
    score_ast: int = 0
    score_llm: int = 0


def run_ab_test(
    targets: list[tuple[Path, str, str | None]], limit: int = 10
) -> list[ABTestResult]:
    """Run A/B test on specified targets."""

    results = []

    for i, (filepath, func_name, class_name) in enumerate(targets[:limit]):
        print(
            f"\n[{i + 1}/{min(len(targets), limit)}] Testing: {filepath.name}::{class_name or ''}.{func_name}"
        )

        # Extract enriched context
        ctx = extract_enriched_context(filepath, func_name, class_name)
        if not ctx:
            logger.info("  ⚠️  could not extract context")
            continue

        # Generate both versions
        logger.info("  🔧 generating ast-only docstring...")
        docstring_ast = generate_docstring_ast_only(ctx)

        logger.info("  🤖 generating ast+llm docstring...")
        docstring_llm = generate_docstring_ast_llm(ctx)

        results.append(
            ABTestResult(
                filepath=str(filepath),
                name=func_name,
                class_name=class_name,
                docstring_ast=docstring_ast,
                docstring_llm=docstring_llm,
            )
        )

    return results


def print_results(results: list[ABTestResult]) -> None:
    """Print A/B test results side by side."""

    logger.info("\n" + "=" * 100")
    logger.info("a/b test results: ast-only vs ast+llm")
    logger.info("=" * 100")

    for i, r in enumerate(results, 1):
        logger.info("\n{'─' * 100}")
        logger.info("test i: {r.filepath}::{r.class name or ''}.{r.name}", i=i)
        logger.info("{'─' * 100}")

        logger.info("\n📋 option a (ast-only):\n")
        for line in r.docstring_ast.split("\n"):
            logger.info("    line", line=line)

        logger.info("\n🤖 option b (ast+llm):\n")
        for line in r.docstring_llm.split("\n"):
            logger.info("    line", line=line)

    logger.info("\n" + "=" * 100")
    logger.info("summary")
    logger.info("=" * 100")
    logger.info("\ntotal tests: {len(results)}")
    logger.info("\nkey observations:")
    logger.info("  - ast-only: consistent, fast, predictable, but sometimes generic")
    logger.info("  - ast+llm:  context-aware, natural language, but slower and costs tokens")
    logger.info("\n📊 rate each pair 1-10 to determine if llm adds value!")


def find_test_targets(
    repo_root: Path, limit: int = 10
) -> list[tuple[Path, str, str | None]]:
    """Find functions missing docstrings to test on."""

    targets = []

    # Scan a few key directories
    scan_dirs = ["agents", "api", "core/agents", "memory"]

    for scan_dir in scan_dirs:
        dir_path = repo_root / scan_dir
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            if "__pycache__" in py_file.parts or "test_" in py_file.name:
                continue

            try:
                source = py_file.read_text()
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not ast.get_docstring(item):
                                targets.append((py_file, item.name, node.name))
                                if len(targets) >= limit:
                                    return targets

                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not ast.get_docstring(node):
                        # Check it's not a method (top-level only)
                        is_toplevel = any(
                            isinstance(n, ast.Module) and node in n.body for n in [tree]
                        )
                        if is_toplevel:
                            targets.append((py_file, node.name, None))
                            if len(targets) >= limit:
                                return targets

    return targets


def main() -> int:
    """Run the A/B test."""

    repo_root = Path(__file__).parent.parent.parent

    logger.info("🔬 docstring a/b test: ast-only vs ast+llm")
    logger.info("=" * 60")

    # Find test targets
    logger.info("\n📍 finding test targets...")
    targets = find_test_targets(repo_root, limit=10)
    logger.info("   found {len(targets)} functions missing docstrings")

    # Run A/B test
    results = run_ab_test(targets, limit=10)

    # Print results
    print_results(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
