#!/usr/bin/env python3
"""
Generate Subsystem READMEs from Code Facts

Uses AST extraction + template to automatically generate README.md files
for each subsystem based on actual code structure.

Usage:
    # Generate all preset subsystems
    python scripts/generate_subsystem_readmes.py

    # Generate specific preset
    python scripts/generate_subsystem_readmes.py --subsystem agents

    # Generate for ANY arbitrary path
    python scripts/generate_subsystem_readmes.py --path agents/cursor
    python scripts/generate_subsystem_readmes.py --path services/research --title "Research Service"

    # Preview without writing
    python scripts/generate_subsystem_readmes.py --path agents/cursor --dry-run

Presets:
    agents  -> core/agents/README.md
    memory  -> memory/README.md
    tools   -> core/tools/README.md
    api     -> api/README.md
"""

import ast
import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
from dataclasses import dataclass, field
import argparse

# ============================================================================
# Configuration: Subsystem Definitions
# ============================================================================

SUBSYSTEMS = {
    "agents": {
        "path": "core/agents",
        "title": "Agents Subsystem",
        "description": "Agent execution runtime for L9 Secure AI OS",
        "purpose": "Orchestrates agent task execution, kernel loading, tool dispatch, and memory integration.",
        "protected_files": ["executor.py", "registry.py", "__init__.py"],
        "allowed_patterns": [
            "adaptive_prompting.py",
            "selfreflection.py",
            "prompt_builder.py",
            "bootstrap/**",
            "graph_state/**",
        ],
        "depends_on": [
            "memory/substrate_service.py",
            "core/tools/registry_adapter.py",
            "runtime/kernel_loader.py",
        ],
        "depended_by": ["api/agent_routes.py", "runtime/task_queue.py"],
    },
    "memory": {
        "path": "memory",
        "title": "Memory Subsystem",
        "description": "Multi-layer memory substrate for L9 Secure AI OS",
        "purpose": "Provides PacketEnvelope storage, semantic search, retrieval, and audit trails.",
        "protected_files": ["substrate_service.py", "substrate_dag.py", "__init__.py"],
        "allowed_patterns": [
            "retrieval.py",
            "semantic_search.py",
            "context_builder.py",
            "insight_extraction.py",
        ],
        "depends_on": ["runtime/redis_client.py"],
        "depended_by": ["core/agents/executor.py", "api/memory/router.py"],
    },
    "tools": {
        "path": "core/tools",
        "title": "Tools Subsystem",
        "description": "Tool registry and dispatch for L9 Secure AI OS",
        "purpose": "Manages tool definitions, capability enforcement, and safe tool invocation.",
        "protected_files": ["registry_adapter.py", "tool_graph.py", "__init__.py"],
        "allowed_patterns": [
            "sanitizer.py",
            "memory_tools.py",
            "research_tools.py",
            "reflection_tools.py",
        ],
        "depends_on": ["runtime/l_tools.py", "core/governance/approval_manager.py"],
        "depended_by": ["core/agents/executor.py"],
    },
    "api": {
        "path": "api",
        "title": "API Subsystem",
        "description": "HTTP and WebSocket interfaces for L9 Secure AI OS",
        "purpose": "Exposes FastAPI endpoints for agent tasks, memory operations, and real-time communication.",
        "protected_files": ["server.py", "auth.py", "__init__.py"],
        "allowed_patterns": [
            "routes/*.py",
            "agent_routes.py",
            "os_routes.py",
            "memory/*.py",
        ],
        "depends_on": ["core/agents/executor.py", "memory/substrate_service.py"],
        "depended_by": [],
    },
}

INVARIANTS = {
    "agents": [
        "Agent IDs are UUIDv4 or registered agent names",
        "All agent tasks emit PacketEnvelope to memory substrate",
        "Kernel stack loaded via KernelLoader before execution",
        "Tool access mediated by RegistryAdapter with capability checks",
        "High-risk tools require Igor approval before dispatch",
    ],
    "memory": [
        "All packet IDs are UUIDv4",
        "All timestamps are UTC ISO-8601",
        "PacketEnvelope is the canonical data structure for all memory writes",
        "Embeddings are list[float] with dimension 1536 or 3072",
        "Deduplication via dedup_key prevents duplicate ingestion",
    ],
    "tools": [
        "Tool names must exist in L_TOOLS_DEFINITIONS registry",
        "Destructive tools require explicit approval gates",
        "All tool executions logged to PacketEnvelope audit trail",
        "Tool dispatch respects AgentCapabilities enum",
    ],
    "api": [
        "Request/response schemas validated via Pydantic",
        "All logging is structured JSON with context (agent_id, task_id)",
        "WebSocket routes use websocket_orchestrator for lifecycle",
        "Rate limiting enforced via RateLimiter with Redis backend",
    ],
}


# ============================================================================
# Code Extraction
# ============================================================================


@dataclass
class ClassInfo:
    name: str
    file: str
    line_start: int
    line_end: int
    docstring: str
    methods: List[str] = field(default_factory=list)
    is_async: bool = False


@dataclass
class FunctionInfo:
    name: str
    file: str
    line: int
    signature: str
    docstring: str
    is_async: bool = False


@dataclass
class SubsystemFacts:
    path: str
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)


def extract_subsystem_facts(repo_root: Path, subsystem_path: str) -> SubsystemFacts:
    """Extract code facts from a subsystem using AST."""
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
                # Extract classes
                if isinstance(node, ast.ClassDef):
                    methods = [
                        m.name
                        for m in node.body
                        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                    ]
                    facts.classes.append(
                        ClassInfo(
                            name=node.name,
                            file=rel_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                            docstring=ast.get_docstring(node) or "",
                            methods=methods,
                        )
                    )

                # Extract top-level functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Only top-level functions (not methods)
                    if node.col_offset == 0:
                        args = [arg.arg for arg in node.args.args]
                        sig = f"def {node.name}({', '.join(args)})"
                        if isinstance(node, ast.AsyncFunctionDef):
                            sig = "async " + sig

                        facts.functions.append(
                            FunctionInfo(
                                name=node.name,
                                file=rel_path,
                                line=node.lineno,
                                signature=sig,
                                docstring=ast.get_docstring(node) or "",
                                is_async=isinstance(node, ast.AsyncFunctionDef),
                            )
                        )

                # Extract imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        facts.imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        facts.imports.append(node.module)

        except Exception as e:
            print(f"WARNING: Could not parse {py_file}: {e}")

    # Deduplicate imports
    facts.imports = sorted(set(facts.imports))

    return facts


# ============================================================================
# README Generation
# ============================================================================

README_TEMPLATE = """# {title}

## Overview

The **{title}** is the {description}. It {purpose}

**What depends on it:** {depended_by_str}

## Responsibilities and Boundaries

### What This Module Owns

{responsibilities}

### What This Module Does NOT Do

{non_responsibilities}

### Dependencies

| Direction | Module | Purpose |
|-----------|--------|---------|
{dependencies_table}

## Directory Layout

```
{dir_layout}
```

## Key Components

{components}

## Data Models and Contracts

{data_models}

### Invariants

{invariants}

## Configuration

### Feature Flags

```yaml
# Subsystem-specific feature flags
{feature_flags}
```

### Environment Variables

```bash
{env_vars}
```

## API Surface (Public)

{api_surface}

## Observability

### Logging

{subsystem_name} operations emit structured JSON logs:

```json
{{
  "timestamp": "{timestamp}",
  "level": "INFO",
  "module": "{module_path}",
  "message": "Operation completed",
  "correlation_id": "corr-xyz789"
}}
```

### Metrics

{metrics}

## Testing

### Unit Tests

Located in `tests/{test_path}/`:
{test_files}

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

{allowed_scopes}

### ⚠️ Restricted Scopes (requires human review)

{restricted_scopes}

### ❌ Forbidden Scopes (never modify without approval)

{forbidden_scopes}

### Required Pre-Reading

1. `README-L9_ARCHITECTURE.md` — System architecture
2. `docs/CURSOR-RUNBOOK.md` — AI collaboration rules
3. This file — Subsystem contracts

---

*L9 Secure AI OS — {title}*
*Generated: {generated_date}*
"""


def generate_readme(
    subsystem_name: str,
    config: Dict[str, Any],
    facts: SubsystemFacts,
) -> str:
    """Generate README content from template and facts."""

    # Build directory layout
    dir_layout_lines = [f"{config['path']}/"]
    for f in sorted(facts.files)[:15]:  # Limit to 15 files
        rel = f.replace(config["path"] + "/", "")
        dir_layout_lines.append(f"├── {rel}")
    if len(facts.files) > 15:
        dir_layout_lines.append(f"└── ... ({len(facts.files) - 15} more files)")
    dir_layout = "\n".join(dir_layout_lines)

    # Build components section
    components_lines = []
    for cls in facts.classes[:5]:  # Top 5 classes
        docstring_first_line = (
            cls.docstring.split("\n")[0] if cls.docstring else "No description"
        )
        components_lines.append(f"### `{cls.file.split('/')[-1]}` — {cls.name}\n")
        components_lines.append(
            f'```python\nclass {cls.name}:\n    """{docstring_first_line}"""\n```\n'
        )
        if cls.methods[:5]:
            components_lines.append(f"**Methods:** `{'`, `'.join(cls.methods[:5])}`\n")
    components = (
        "\n".join(components_lines)
        if components_lines
        else "See source files for component details."
    )

    # Build dependencies table
    dep_lines = []
    for dep in config.get("depends_on", []):
        dep_lines.append(f"| **Outbound** | `{dep}` | Required dependency |")
    for dep in config.get("depended_by", []):
        dep_lines.append(f"| **Inbound** | `{dep}` | Uses this module |")
    dependencies_table = (
        "\n".join(dep_lines) if dep_lines else "| — | — | No external dependencies |"
    )

    # Build invariants
    inv_list = INVARIANTS.get(subsystem_name, ["No invariants defined"])
    invariants = "\n".join([f"- **{inv}**" for inv in inv_list])

    # Build allowed/restricted/forbidden scopes
    allowed = config.get("allowed_patterns", [])
    allowed_scopes = (
        "\n".join([f"- `{p}` — Application logic" for p in allowed])
        if allowed
        else "- All non-protected files"
    )

    protected = config.get("protected_files", [])
    forbidden_scopes = (
        "\n".join([f"- `{p}` — PROTECTED" for p in protected])
        if protected
        else "- None"
    )

    # Build metrics
    metrics = f"""- `{subsystem_name}_operation_duration_ms` — Operation latency (histogram)
- `{subsystem_name}_operation_total` — Total operations (counter)
- `{subsystem_name}_error_rate` — Error percentage (gauge)"""

    # Build test files reference
    test_path = config["path"].replace("/", "_")
    test_files = "\n".join(
        [f"- `test_{subsystem_name}.py` — Unit tests" for _ in range(1)]
    )

    # Depended by string
    depended_by = config.get("depended_by", [])
    depended_by_str = (
        ", ".join([f"`{d}`" for d in depended_by])
        if depended_by
        else "External clients"
    )

    # Fill template
    return README_TEMPLATE.format(
        title=config["title"],
        description=config["description"],
        purpose=config["purpose"],
        depended_by_str=depended_by_str,
        responsibilities="- See key components below for detailed responsibilities",
        non_responsibilities="- Operations handled by other subsystems (see dependencies)",
        dependencies_table=dependencies_table,
        dir_layout=dir_layout,
        components=components,
        data_models="See `schemas.py` or data model files in this subsystem.",
        invariants=invariants,
        feature_flags=f"L9_ENABLE_{subsystem_name.upper()}_TRACING: true",
        env_vars=f"{subsystem_name.upper()}_LOG_LEVEL=INFO",
        api_surface="See key components for public API details.",
        subsystem_name=subsystem_name.capitalize(),
        timestamp=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        module_path=config["path"].replace("/", "."),
        metrics=metrics,
        test_path=test_path,
        test_files=test_files,
        allowed_scopes=allowed_scopes,
        restricted_scopes="- Schema changes\n- Feature flag logic",
        forbidden_scopes=forbidden_scopes,
        generated_date=datetime.utcnow().strftime("%Y-%m-%d"),
    )


# ============================================================================
# Main
# ============================================================================


def auto_config_from_path(path: str) -> Dict[str, Any]:
    """Generate a config dict from an arbitrary path."""
    # Extract name from path (last component or meaningful part)
    parts = path.rstrip("/").split("/")
    name = parts[-1]

    # Generate readable title
    title = name.replace("_", " ").replace("-", " ").title() + " Module"

    return {
        "path": path,
        "title": title,
        "description": f"module at `{path}`",
        "purpose": "provides functionality as documented in the key components below.",
        "protected_files": ["__init__.py"],
        "allowed_patterns": ["**/*.py"],
        "depends_on": [],
        "depended_by": [],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate subsystem READMEs from code facts"
    )
    parser.add_argument(
        "--subsystem",
        "-s",
        help="Generate for specific preset subsystem (agents, memory, tools, api)",
    )
    parser.add_argument(
        "--path", "-p", help="Generate for arbitrary path (e.g., agents/cursor)"
    )
    parser.add_argument("--title", "-t", help="Custom title (used with --path)")
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Print output without writing"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent

    print("🔍 Generating subsystem READMEs from code facts...")

    # Build list of (name, config) tuples to process
    to_process = []

    if args.path:
        # Arbitrary path mode
        path = args.path.rstrip("/")
        config = auto_config_from_path(path)
        if args.title:
            config["title"] = args.title
        name = path.replace("/", "_")
        to_process.append((name, config))
    elif args.subsystem:
        # Preset subsystem mode
        if args.subsystem not in SUBSYSTEMS:
            print(f"ERROR: Unknown subsystem '{args.subsystem}'")
            print(f"Available presets: {', '.join(SUBSYSTEMS.keys())}")
            print("Or use --path for arbitrary directories")
            return 1
        to_process.append((args.subsystem, SUBSYSTEMS[args.subsystem]))
    else:
        # All presets
        to_process = list(SUBSYSTEMS.items())

    for subsystem_name, config in to_process:
        subsystem_path = config["path"]

        # Verify path exists
        full_path = repo_root / subsystem_path
        if not full_path.exists():
            print(f"⚠️  Path not found: {full_path}")
            continue

        print(f"\n📝 Processing {subsystem_name} ({subsystem_path})...")

        # Extract facts
        facts = extract_subsystem_facts(repo_root, subsystem_path)

        if args.verbose:
            print(
                f"   Found {len(facts.files)} files, {len(facts.classes)} classes, {len(facts.functions)} functions"
            )

        # Generate README
        readme_content = generate_readme(subsystem_name, config, facts)

        # Write or print
        readme_path = repo_root / subsystem_path / "README.md"

        if args.dry_run:
            print(f"\n--- {readme_path} ---")
            print(readme_content[:500] + "...\n")
        else:
            readme_path.parent.mkdir(parents=True, exist_ok=True)
            readme_path.write_text(readme_content)
            print(f"   ✅ Generated {readme_path}")

    print("\n✨ README generation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
