#!/usr/bin/env python3
"""
Generate README Superprompt for Perplexity

Extracts comprehensive code facts using AST and generates a superprompt
that can be pasted into Perplexity to produce a gold-standard README.

HYBRID APPROACH:
1. This script extracts FACTS (ground truth) from code
2. Generates a SUPERPROMPT with those facts embedded
3. Paste superprompt into Perplexity
4. Perplexity generates rich README using the facts
5. Validate output against facts, deploy

Usage:
    # Generate superprompt for a path
    python scripts/generate_readme_superprompt.py --path agents/cursor

    # Output to file instead of stdout
    python scripts/generate_readme_superprompt.py --path agents/cursor --output superprompt.md

    # Include config overrides
    python scripts/generate_readme_superprompt.py --path agents/cursor --config agents/cursor/readme.yaml

Output:
    A markdown file containing:
    - System prompt (from labs-research-super-prompt.md)
    - Extracted facts (classes, methods, types, routes, etc.)
    - Generation instructions
    - Validation checklist

SOP: Research results go to agents/cursor/perplexity_research_results/
     Subfolder naming: MM-DD-YYYY - <description>
"""

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# ============================================================================
# Enhanced Code Extraction (AST)
# ============================================================================


@dataclass
class TypeInfo:
    """Type annotation information."""

    name: str
    is_optional: bool = False
    is_list: bool = False
    is_dict: bool = False
    inner_types: List[str] = field(default_factory=list)


@dataclass
class FieldInfo:
    """Pydantic/dataclass field information."""

    name: str
    type_annotation: str
    default: Optional[str] = None
    is_required: bool = True


@dataclass
class ClassInfo:
    """Enhanced class information."""

    name: str
    file: str
    line_start: int
    line_end: int
    docstring: str
    methods: List[Dict[str, Any]] = field(default_factory=list)
    fields: List[FieldInfo] = field(default_factory=list)
    bases: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    is_pydantic: bool = False
    is_dataclass: bool = False


@dataclass
class FunctionInfo:
    """Enhanced function information."""

    name: str
    file: str
    line: int
    signature: str
    docstring: str
    is_async: bool = False
    return_type: Optional[str] = None
    parameters: List[Dict[str, str]] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)


@dataclass
class RouteInfo:
    """API route information."""

    method: str  # GET, POST, PUT, DELETE, WEBSOCKET
    path: str
    function_name: str
    file: str
    line: int
    decorators: List[str] = field(default_factory=list)


@dataclass
class SubsystemFacts:
    """All extracted facts from a subsystem."""

    path: str
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    routes: List[RouteInfo] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    pydantic_models: List[ClassInfo] = field(default_factory=list)
    enums: List[ClassInfo] = field(default_factory=list)
    constants: List[Tuple[str, str, str]] = field(
        default_factory=list
    )  # (name, value, file)
    # Phase 1 enhancements
    exports: List[str] = field(default_factory=list)  # __all__ contents
    dora_meta: Dict[str, Any] = field(default_factory=dict)  # __dora_meta__ contents
    has_existing_readme: bool = False  # Warning flag

    @property
    def total_lines(self) -> int:
        """Estimate total lines."""
        return sum(c.line_end - c.line_start for c in self.classes)


def extract_type_annotation(node: ast.expr) -> str:
    """Extract type annotation as string."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name):
            base = node.value.id
            if isinstance(node.slice, ast.Tuple):
                inner = ", ".join(extract_type_annotation(e) for e in node.slice.elts)
            else:
                inner = extract_type_annotation(node.slice)
            return f"{base}[{inner}]"
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    elif isinstance(node, ast.Attribute):
        return f"{extract_type_annotation(node.value)}.{node.attr}"
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # Union type with | operator
        left = extract_type_annotation(node.left)
        right = extract_type_annotation(node.right)
        return f"{left} | {right}"
    return "Any"


def extract_decorator_name(dec: ast.expr) -> str:
    """Extract decorator name."""
    if isinstance(dec, ast.Name):
        return dec.id
    elif isinstance(dec, ast.Call):
        if isinstance(dec.func, ast.Name):
            return dec.func.id
        elif isinstance(dec.func, ast.Attribute):
            return f"{extract_decorator_name(dec.func.value)}.{dec.func.attr}"
    elif isinstance(dec, ast.Attribute):
        return f"{extract_decorator_name(dec.value)}.{dec.attr}"
    return "unknown"


def extract_route_info(
    dec: ast.expr, func_name: str, file: str, line: int
) -> Optional[RouteInfo]:
    """Extract FastAPI route information from decorator."""
    dec_name = extract_decorator_name(dec)

    # Check for router decorators
    route_methods = {
        "get": "GET",
        "post": "POST",
        "put": "PUT",
        "delete": "DELETE",
        "patch": "PATCH",
        "websocket": "WEBSOCKET",
    }

    for method_suffix, http_method in route_methods.items():
        if dec_name.endswith(f".{method_suffix}") or dec_name == method_suffix:
            # Extract path from first argument
            path = "/"
            if isinstance(dec, ast.Call) and dec.args:
                if isinstance(dec.args[0], ast.Constant):
                    path = dec.args[0].value
            return RouteInfo(
                method=http_method,
                path=path,
                function_name=func_name,
                file=file,
                line=line,
                decorators=[dec_name],
            )
    return None


def extract_class_fields(node: ast.ClassDef) -> List[FieldInfo]:
    """Extract fields from class (Pydantic/dataclass)."""
    fields = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            type_ann = (
                extract_type_annotation(item.annotation) if item.annotation else "Any"
            )
            default = None
            is_required = True

            if item.value:
                if isinstance(item.value, ast.Constant):
                    default = repr(item.value.value)
                    is_required = False
                elif isinstance(item.value, ast.Call):
                    # Field(...) or similar
                    default = extract_decorator_name(item.value.func) + "(...)"
                    is_required = False

            fields.append(
                FieldInfo(
                    name=item.target.id,
                    type_annotation=type_ann,
                    default=default,
                    is_required=is_required,
                )
            )
    return fields


def extract_subsystem_facts(repo_root: Path, subsystem_path: str) -> SubsystemFacts:
    """Extract comprehensive code facts from a subsystem using AST."""
    facts = SubsystemFacts(path=subsystem_path)
    full_path = repo_root / subsystem_path

    if not full_path.exists():
        return facts

    for py_file in full_path.rglob("*.py"):
        rel_path = str(py_file.relative_to(repo_root))
        facts.files.append(rel_path)

        try:
            content = py_file.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Extract classes with enhanced info
                if isinstance(node, ast.ClassDef):
                    # Get decorators
                    decorators = [
                        extract_decorator_name(d) for d in node.decorator_list
                    ]
                    is_dataclass = "dataclass" in decorators

                    # Get base classes
                    bases = []
                    is_pydantic = False
                    for base in node.bases:
                        base_name = extract_type_annotation(base)
                        bases.append(base_name)
                        if "BaseModel" in base_name or "BaseSettings" in base_name:
                            is_pydantic = True

                    # Get methods with signatures
                    methods = []
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            params = []
                            for arg in item.args.args:
                                param = {"name": arg.arg}
                                if arg.annotation:
                                    param["type"] = extract_type_annotation(
                                        arg.annotation
                                    )
                                params.append(param)

                            return_type = None
                            if item.returns:
                                return_type = extract_type_annotation(item.returns)

                            methods.append(
                                {
                                    "name": item.name,
                                    "is_async": isinstance(item, ast.AsyncFunctionDef),
                                    "parameters": params,
                                    "return_type": return_type,
                                    "line": item.lineno,
                                    "docstring": ast.get_docstring(item) or "",
                                }
                            )

                    # Get fields
                    fields = extract_class_fields(node)

                    class_info = ClassInfo(
                        name=node.name,
                        file=rel_path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        docstring=ast.get_docstring(node) or "",
                        methods=methods,
                        fields=fields,
                        bases=bases,
                        decorators=decorators,
                        is_pydantic=is_pydantic,
                        is_dataclass=is_dataclass,
                    )

                    # Categorize
                    if is_pydantic or is_dataclass:
                        facts.pydantic_models.append(class_info)
                    if (
                        "Enum" in bases
                        or node.name.endswith("Enum")
                        or node.name.endswith("Type")
                    ):
                        facts.enums.append(class_info)

                    facts.classes.append(class_info)

                # Extract top-level functions with routes
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.col_offset == 0:  # Top-level only
                        decorators = [
                            extract_decorator_name(d) for d in node.decorator_list
                        ]

                        # Check for routes
                        for dec in node.decorator_list:
                            route = extract_route_info(
                                dec, node.name, rel_path, node.lineno
                            )
                            if route:
                                facts.routes.append(route)

                        # Get parameters
                        params = []
                        for arg in node.args.args:
                            param = {"name": arg.arg}
                            if arg.annotation:
                                param["type"] = extract_type_annotation(arg.annotation)
                            params.append(param)

                        return_type = None
                        if node.returns:
                            return_type = extract_type_annotation(node.returns)

                        sig_parts = []
                        for p in params:
                            if "type" in p:
                                sig_parts.append(f"{p['name']}: {p['type']}")
                            else:
                                sig_parts.append(p["name"])

                        sig = f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {node.name}({', '.join(sig_parts)})"
                        if return_type:
                            sig += f" -> {return_type}"

                        facts.functions.append(
                            FunctionInfo(
                                name=node.name,
                                file=rel_path,
                                line=node.lineno,
                                signature=sig,
                                docstring=ast.get_docstring(node) or "",
                                is_async=isinstance(node, ast.AsyncFunctionDef),
                                return_type=return_type,
                                parameters=params,
                                decorators=decorators,
                            )
                        )

                # Extract imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        facts.imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        facts.imports.append(node.module)

                # Extract module-level constants
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            # Extract __all__ exports
                            if target.id == "__all__" and isinstance(
                                node.value, ast.List
                            ):
                                for elt in node.value.elts:
                                    if isinstance(elt, ast.Constant):
                                        facts.exports.append(elt.value)

                            # Extract __dora_meta__ governance metadata
                            elif target.id == "__dora_meta__" and isinstance(
                                node.value, ast.Dict
                            ):
                                for key, val in zip(node.value.keys, node.value.values):
                                    if isinstance(key, ast.Constant) and isinstance(
                                        val, ast.Constant
                                    ):
                                        facts.dora_meta[key.value] = val.value
                                    elif isinstance(key, ast.Constant):
                                        # Complex value, just note it exists
                                        facts.dora_meta[key.value] = "..."

                            # Extract UPPERCASE constants
                            elif target.id.isupper():
                                value = "..."
                                if isinstance(node.value, ast.Constant):
                                    value = repr(node.value.value)[:50]
                                elif isinstance(node.value, ast.Dict):
                                    value = "{...}"
                                elif isinstance(node.value, ast.List):
                                    value = "[...]"
                                facts.constants.append((target.id, value, rel_path))

        except Exception as e:
            print(f"WARNING: Could not parse {py_file}: {e}", file=sys.stderr)

    # Deduplicate imports
    facts.imports = sorted(set(facts.imports))

    return facts


# ============================================================================
# Superprompt Generation
# ============================================================================

SUPERPROMPT_TEMPLATE = """# README Generation Request for: {title}

## SYSTEM CONTEXT

You are generating a **gold-standard README** for the `{path}` module in L9 Secure AI OS.

### Core Principles
1. **Documentation as Contract** — README specifies scope, APIs, invariants, AI rules
2. **Zero Hallucination** — Use ONLY the facts provided below, do NOT invent
3. **Production-Grade** — Complete, deployable, no placeholders

---

## EXTRACTED FACTS (GROUND TRUTH)

**Path:** `{path}`
**Files:** {file_count} Python files
**Classes:** {class_count}
**Functions:** {function_count}
**Pydantic Models:** {model_count}
**API Routes:** {route_count}

### File List
```
{file_list}
```

### Classes (with methods and fields)
{classes_section}

### Pydantic/Dataclass Models
{models_section}

### API Routes
{routes_section}

### Top-Level Functions
{functions_section}

### Key Imports (Dependencies)
```
{imports_section}
```

### Constants
{constants_section}

### Public API (`__all__` exports)
{exports_section}

### DORA Governance Metadata
{dora_section}

---

## GENERATION INSTRUCTIONS

Generate a README with these EXACT sections:

### Required Sections

1. **Overview** (1-2 paragraphs)
   - What this module does
   - Who depends on it
   - Use the class names and purposes from the facts

2. **Responsibilities and Boundaries**
   - What this module owns (derive from classes)
   - What it does NOT do (based on imports/dependencies)
   - Dependencies table (Inbound/Outbound)

3. **Directory Layout**
   - Use the file list provided
   - Add brief descriptions based on class/function purposes

4. **Key Components**
   - For each major class, include:
     - Class name and file
     - Docstring (from facts)
     - Key methods with signatures
     - If Pydantic: list fields with types

5. **Data Models and Contracts**
   - List all Pydantic models with fields
   - Include field types and defaults
   - State invariants (derive from field constraints)

6. **API Surface** (if routes exist)
   - List all routes with method, path, handler
   - Include request/response types if visible

7. **Configuration**
   - Feature flags (L9_ENABLE_*)
   - Environment variables

8. **Observability**
   - Logging format
   - Metrics to emit

9. **AI Usage Rules**
   - ✅ Allowed: Application logic, tests
   - ⚠️ Restricted: Schema changes
   - ❌ Forbidden: `__init__.py`, core entry points

---

## VALIDATION CHECKLIST

After generating, verify:

- [ ] Every class mentioned exists in the facts above
- [ ] Every method signature matches the extracted signatures
- [ ] Every file path is from the file list
- [ ] No invented classes, methods, or files
- [ ] Pydantic fields match exactly

---

## OUTPUT FORMAT

Return ONLY the README content in markdown format.
Start with `# {title}` heading.
End with generation timestamp.

Do NOT include this prompt in the output.
Do NOT add commentary before or after the README.

---

**BEGIN GENERATION**
"""


def format_class_info(cls: ClassInfo) -> str:
    """Format class info for superprompt."""
    lines = [f"#### `{cls.name}` ({cls.file}:{cls.line_start}-{cls.line_end})"]

    if cls.bases:
        lines.append(f"**Bases:** `{'`, `'.join(cls.bases)}`")
    if cls.decorators:
        lines.append(f"**Decorators:** `{'`, `'.join(cls.decorators)}`")
    if cls.docstring:
        lines.append(f"**Docstring:** {cls.docstring.split(chr(10))[0]}")

    if cls.fields:
        lines.append("\n**Fields:**")
        for f in cls.fields:
            req = "" if f.is_required else f" = {f.default}"
            lines.append(f"- `{f.name}: {f.type_annotation}{req}`")

    if cls.methods:
        lines.append("\n**Methods:**")
        for m in cls.methods[:10]:  # Limit to 10 methods
            async_prefix = "async " if m.get("is_async") else ""
            params = ", ".join(
                f"{p['name']}: {p.get('type', 'Any')}"
                for p in m.get("parameters", [])[:5]  # Limit params
            )
            ret = f" -> {m['return_type']}" if m.get("return_type") else ""
            lines.append(f"- `{async_prefix}{m['name']}({params}){ret}`")

    return "\n".join(lines)


def format_function_info(func: FunctionInfo) -> str:
    """Format function info for superprompt."""
    lines = [f"#### `{func.name}` ({func.file}:{func.line})"]
    lines.append(f"**Signature:** `{func.signature}`")
    if func.docstring:
        lines.append(f"**Docstring:** {func.docstring.split(chr(10))[0]}")
    if func.decorators:
        lines.append(f"**Decorators:** `{'`, `'.join(func.decorators)}`")
    return "\n".join(lines)


def format_route_info(route: RouteInfo) -> str:
    """Format route info for superprompt."""
    return f"- `{route.method} {route.path}` → `{route.function_name}()` ({route.file}:{route.line})"


def generate_superprompt(
    facts: SubsystemFacts,
    title: str,
    config: Optional[Dict] = None,
    max_classes: int = 15,
    max_functions: int = 15,
) -> str:
    """Generate the superprompt with embedded facts."""

    # File list
    file_list = "\n".join(sorted(facts.files)[:30])
    if len(facts.files) > 30:
        file_list += f"\n... and {len(facts.files) - 30} more files"

    # Classes section (use configurable limit)
    classes_section = "\n\n".join(
        format_class_info(c) for c in facts.classes[:max_classes]
    )
    if not classes_section:
        classes_section = "*No classes found*"
    if len(facts.classes) > max_classes:
        classes_section += (
            f"\n\n*... and {len(facts.classes) - max_classes} more classes*"
        )

    # Models section (Pydantic/dataclass)
    models_section = "\n\n".join(
        format_class_info(m) for m in facts.pydantic_models[:10]
    )
    if not models_section:
        models_section = "*No Pydantic models found*"

    # Routes section
    routes_section = "\n".join(format_route_info(r) for r in facts.routes)
    if not routes_section:
        routes_section = "*No API routes found*"

    # Functions section (use configurable limit)
    functions_section = "\n\n".join(
        format_function_info(f) for f in facts.functions[:max_functions]
    )
    if not functions_section:
        functions_section = "*No top-level functions found*"
    if len(facts.functions) > max_functions:
        functions_section += (
            f"\n\n*... and {len(facts.functions) - max_functions} more functions*"
        )

    # Imports section
    imports_section = "\n".join(facts.imports[:30])
    if len(facts.imports) > 30:
        imports_section += f"\n# ... and {len(facts.imports) - 30} more imports"

    # Constants section
    constants_section = "\n".join(
        f"- `{name}` = {val} ({file})" for name, val, file in facts.constants[:15]
    )
    if not constants_section:
        constants_section = "*No module-level constants found*"

    # Exports section (__all__)
    if facts.exports:
        exports_section = "```python\n__all__ = [\n"
        exports_section += "\n".join(f'    "{e}",' for e in facts.exports[:20])
        exports_section += "\n]\n```"
        if len(facts.exports) > 20:
            exports_section += f"\n*... and {len(facts.exports) - 20} more exports*"
    else:
        exports_section = "*No `__all__` defined (module exports all public names)*"

    # DORA metadata section
    if facts.dora_meta:
        dora_lines = ["```yaml"]
        for key, val in list(facts.dora_meta.items())[:10]:
            dora_lines.append(f"{key}: {val}")
        dora_lines.append("```")
        dora_section = "\n".join(dora_lines)
    else:
        dora_section = "*No `__dora_meta__` governance metadata found*"

    return SUPERPROMPT_TEMPLATE.format(
        title=title,
        path=facts.path,
        file_count=len(facts.files),
        class_count=len(facts.classes),
        function_count=len(facts.functions),
        model_count=len(facts.pydantic_models),
        route_count=len(facts.routes),
        file_list=file_list,
        classes_section=classes_section,
        models_section=models_section,
        routes_section=routes_section,
        functions_section=functions_section,
        imports_section=imports_section,
        constants_section=constants_section,
        exports_section=exports_section,
        dora_section=dora_section,
    )


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Generate README superprompt for Perplexity",
        epilog="""
SOP: Research results go to agents/cursor/perplexity_research_results/
     Subfolder naming: MM-DD-YYYY - <description>
     Files archived weekly after review.
        """,
    )
    parser.add_argument(
        "--path", "-p", required=True, help="Path to analyze (e.g., agents/cursor)"
    )
    parser.add_argument(
        "--title", "-t", help="Custom title (default: derived from path)"
    )
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--config", "-c", help="Optional YAML config with overrides")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show extraction stats"
    )
    # Phase 1 enhancements: configurable limits
    parser.add_argument(
        "--max-classes",
        type=int,
        default=15,
        help="Max classes to include in superprompt (default: 15)",
    )
    parser.add_argument(
        "--max-functions",
        type=int,
        default=15,
        help="Max functions to include in superprompt (default: 15)",
    )
    parser.add_argument(
        "--template",
        choices=["module", "agent", "api", "service", "kernel"],
        default="module",
        help="README template type (default: module) [STUB for Phase 2]",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    path = args.path.rstrip("/")

    # Generate title
    if args.title:
        title = args.title
    else:
        parts = path.split("/")
        title = parts[-1].replace("_", " ").replace("-", " ").title() + " Module"

    # Load optional config
    config = None
    if args.config and YAML_AVAILABLE:
        config_path = repo_root / args.config
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)

    # Verify path exists
    full_path = repo_root / path
    if not full_path.exists():
        print(f"ERROR: Path not found: {full_path}", file=sys.stderr)
        return 1

    # Phase 1: Check if README.md already exists at target
    existing_readme = full_path / "README.md"
    if existing_readme.exists():
        readme_lines = len(existing_readme.read_text().splitlines())
        print(
            f"⚠️  WARNING: README.md already exists at {path}/README.md ({readme_lines} lines)",
            file=sys.stderr,
        )
        print(
            "   Generated README will REPLACE existing content. Git has history.",
            file=sys.stderr,
        )
        if readme_lines > 100:
            print(
                f"   ⚠️  CAUTION: Existing README is substantial ({readme_lines} lines). Review before replacing.",
                file=sys.stderr,
            )

    print(f"🔍 Extracting facts from {path}...", file=sys.stderr)

    # Extract facts
    facts = extract_subsystem_facts(repo_root, path)
    facts.has_existing_readme = existing_readme.exists()

    if args.verbose:
        print(f"   Files: {len(facts.files)}", file=sys.stderr)
        print(f"   Classes: {len(facts.classes)}", file=sys.stderr)
        print(f"   Functions: {len(facts.functions)}", file=sys.stderr)
        print(f"   Pydantic Models: {len(facts.pydantic_models)}", file=sys.stderr)
        print(f"   Routes: {len(facts.routes)}", file=sys.stderr)
        print(f"   Imports: {len(facts.imports)}", file=sys.stderr)
        # Phase 1 enhancements
        print(f"   Exports (__all__): {len(facts.exports)}", file=sys.stderr)
        print(f"   DORA Meta: {'✅' if facts.dora_meta else '❌'}", file=sys.stderr)
        print(
            f"   Limits: max_classes={args.max_classes}, max_functions={args.max_functions}",
            file=sys.stderr,
        )

    # Generate superprompt (with configurable limits)
    superprompt = generate_superprompt(
        facts,
        title,
        config,
        max_classes=args.max_classes,
        max_functions=args.max_functions,
    )

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(superprompt)
        print(f"✅ Superprompt written to {output_path}", file=sys.stderr)
    else:
        print(superprompt)

    print("\n📋 Next steps:", file=sys.stderr)
    print("   1. Copy the superprompt above", file=sys.stderr)
    print("   2. Paste into Perplexity", file=sys.stderr)
    print("   3. Validate output against extracted facts", file=sys.stderr)
    print(f"   4. Save to {path}/README.md", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
