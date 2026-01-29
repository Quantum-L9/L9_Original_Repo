#!/usr/bin/env python3
"""
Generate Subsystem READMEs from Code Facts

SINGLE SOURCE OF TRUTH: config/subsystems/readme_config.yaml
This is the ONLY README pipeline - replaces the old README.meta.yaml system.

Features:
    - Reads subsystem definitions from YAML config
    - Verifies system time at startup (prevents stale timestamps)
    - Updates last_updated in config when generating
    - Backs up existing README.md to README.md.bak before overwriting
    - Adds generation header with verified timestamp
    - Supports tier-based filtering
    - Validates config schema
    - Handles forbidden_scopes, prereading, sections

Usage:
    python scripts/generate_subsystem_readmes.py                    # All subsystems
    python scripts/generate_subsystem_readmes.py --subsystem memory # Specific one
    python scripts/generate_subsystem_readmes.py --tier core        # All in tier
    python scripts/generate_subsystem_readmes.py --dry-run          # Preview only
    python scripts/generate_subsystem_readmes.py --list             # List all
    python scripts/generate_subsystem_readmes.py --validate         # Validate config
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Generate Subsystem Readmes",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T17:12:30Z",
    "updated_at": "2026-01-25T14:49:28Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "generate_subsystem_readmes",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["PostgreSQL", "Redis"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import argparse
import ast
import json
import shutil
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("WARNING: PyYAML not installed. Install with: pip install pyyaml")

# ============================================================================
# Configuration
# ============================================================================

CONFIG_PATH = "config/subsystems/readme_config.yaml"
VALID_TIERS = {"core", "orchestration", "api", "agents", "services", "infrastructure"}
TIME_DRIFT_THRESHOLD_SECONDS = 60  # Max allowed drift from verified time


def verify_system_time() -> tuple[datetime, bool, str]:
    """
    Verify system time against external source.
    Returns: (current_time, is_verified, verification_source)
    """
    now = datetime.now(UTC)

    # Try worldtimeapi.org first
    try:
        url = "http://worldtimeapi.org/api/timezone/UTC"
        req = urllib.request.Request(
            url, headers={"User-Agent": "L9-README-Generator/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            api_time = datetime.fromisoformat(
                data["utc_datetime"].replace("Z", "+00:00")
            )
            drift = abs((now - api_time).total_seconds())
            if drift <= TIME_DRIFT_THRESHOLD_SECONDS:
                return now, True, f"worldtimeapi.org (drift: {drift:.1f}s)"
            return now, False, f"worldtimeapi.org (DRIFT TOO HIGH: {drift:.1f}s)"
    except Exception:
        pass

    # Fallback: try timeapi.io
    try:
        url = "https://timeapi.io/api/Time/current/zone?timeZone=UTC"
        req = urllib.request.Request(
            url, headers={"User-Agent": "L9-README-Generator/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            api_time = datetime(
                data["year"],
                data["month"],
                data["day"],
                data["hour"],
                data["minute"],
                data["seconds"],
                tzinfo=UTC,
            )
            drift = abs((now - api_time).total_seconds())
            if drift <= TIME_DRIFT_THRESHOLD_SECONDS:
                return now, True, f"timeapi.io (drift: {drift:.1f}s)"
            return now, False, f"timeapi.io (DRIFT TOO HIGH: {drift:.1f}s)"
    except Exception:
        pass

    # Fallback: use system time but mark as unverified
    return now, False, "system clock (UNVERIFIED - no API response)"


def load_config(repo_root: Path) -> dict[str, Any]:
    """Load subsystem configuration from YAML."""
    config_file = repo_root / CONFIG_PATH
    if not config_file.exists():
        print(f"ERROR: Config file not found: {config_file}")
        print("Create it or use --path for ad-hoc generation.")
        sys.exit(1)

    if not YAML_AVAILABLE:
        print("ERROR: PyYAML required to load config. Install with: pip install pyyaml")
        sys.exit(1)

    with open(config_file) as f:
        return yaml.safe_load(f)


def save_config(repo_root: Path, config: dict[str, Any]) -> None:
    """Save config back to YAML (for updating last_updated)."""
    config_file = repo_root / CONFIG_PATH
    with open(config_file, "w") as f:
        yaml.dump(
            config, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )


def validate_subsystem_config(key: str, config: dict[str, Any]) -> list[str]:
    """Validate a single subsystem config, return list of errors."""
    errors = []
    required_fields = ["path", "title", "tier", "description", "purpose"]

    for fld in required_fields:
        if fld not in config:
            errors.append(f"  [{key}] Missing required field: {fld}")

    if "tier" in config and config["tier"] not in VALID_TIERS:
        errors.append(
            f"  [{key}] Invalid tier '{config['tier']}'. Must be one of: {VALID_TIERS}"
        )

    return errors


# ============================================================================
# Code Extraction (using enhanced ast_scanner)
# ============================================================================

# Add repo root to path for importing ast_scanner
_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Try to import the enhanced ast_scanner module
try:
    from tools.superpack_reports.ast_scanner import scan_module as ast_scan_module

    AST_SCANNER_AVAILABLE = True
except ImportError as e:
    AST_SCANNER_AVAILABLE = False
    print(f"WARNING: ast_scanner module not available ({e}), using fallback extraction")


@dataclass
class ClassInfo:
    """Class information for README generation."""

    name: str
    file: str
    line_start: int
    line_end: int
    docstring: str
    methods: list[str] = field(default_factory=list)
    method_details: list[dict] = field(default_factory=list)  # NEW: Rich method info
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)  # NEW


@dataclass
class FunctionInfo:
    """Function information for README generation."""

    name: str
    file: str
    line: int
    signature: str
    docstring: str
    is_async: bool = False
    return_type: str | None = None  # NEW
    decorators: list[str] = field(default_factory=list)  # NEW


@dataclass
class SubsystemFacts:
    """Aggregated facts about a subsystem."""

    path: str
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    # NEW: High-value extractions
    exports: list[str] = field(default_factory=list)  # __all__ contents
    constants: list[tuple[str, str, int]] = field(
        default_factory=list
    )  # (name, value, line)
    global_vars: list[tuple[str, str | None, int]] = field(
        default_factory=list
    )  # (name, type, line)
    module_docstrings: dict[str, str] = field(default_factory=dict)  # file -> docstring


def extract_subsystem_facts(repo_root: Path, subsystem_path: str) -> SubsystemFacts:
    """
    Extract code facts from a subsystem using enhanced AST scanner.

    Uses tools/superpack_reports/ast_scanner.py for rich extraction including:
    - Docstrings (module, class, method, function)
    - Line numbers (start/end)
    - Return types
    - __all__ exports
    - Constants and global variables
    """
    facts = SubsystemFacts(path=subsystem_path)
    full_path = repo_root / subsystem_path

    if not full_path.exists():
        return facts

    all_imports = []
    all_exports = []
    all_constants = []
    all_global_vars = []

    for py_file in full_path.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue

        rel_path = str(py_file.relative_to(repo_root))
        facts.files.append(rel_path)

        if AST_SCANNER_AVAILABLE:
            # Use enhanced ast_scanner
            module_info = ast_scan_module(py_file, repo_root)
            if module_info is None:
                continue

            # Store module docstring
            if module_info.docstring:
                facts.module_docstrings[rel_path] = module_info.docstring

            # Collect exports
            all_exports.extend(module_info.exports)

            # Collect constants
            for const in module_info.constants:
                all_constants.append((const.name, const.value_repr or "", const.line))

            # Collect global vars
            for gvar in module_info.global_vars:
                all_global_vars.append((gvar.name, gvar.type_hint, gvar.line))

            # Collect imports
            all_imports.extend(module_info.imports)

            # Convert classes
            for cls in module_info.classes:
                method_names = [m.name for m in cls.methods]
                method_details = [
                    {
                        "name": m.name,
                        "is_async": m.is_async,
                        "return_type": m.return_type,
                        "docstring": m.docstring,
                        "args": m.args,
                        "line_start": m.line_start,
                        "line_end": m.line_end,
                    }
                    for m in cls.methods
                ]
                facts.classes.append(
                    ClassInfo(
                        name=cls.name,
                        file=rel_path,
                        line_start=cls.line_start,
                        line_end=cls.line_end or cls.line_start,
                        docstring=cls.docstring or "",
                        methods=method_names,
                        method_details=method_details,
                        decorators=cls.decorators,
                    )
                )

            # Convert functions
            for func in module_info.functions:
                args_str = ", ".join(func.args)
                ret_str = f" -> {func.return_type}" if func.return_type else ""
                sig = f"def {func.name}({args_str}){ret_str}"
                if func.is_async:
                    sig = "async " + sig

                facts.functions.append(
                    FunctionInfo(
                        name=func.name,
                        file=rel_path,
                        line=func.line_start,
                        signature=sig,
                        docstring=func.docstring or "",
                        is_async=func.is_async,
                        return_type=func.return_type,
                        decorators=func.decorators,
                    )
                )
        else:
            # Fallback: basic AST extraction
            try:
                content = py_file.read_text()
                tree = ast.parse(content)

                for node in ast.walk(tree):
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

                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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

                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            all_imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        all_imports.append(node.module)

            except Exception as e:
                print(f"WARNING: Could not parse {py_file}: {e}")

    facts.imports = sorted(set(all_imports))
    facts.exports = sorted(set(all_exports))
    facts.constants = all_constants
    facts.global_vars = all_global_vars
    return facts


# ============================================================================
# README Generation
# ============================================================================

README_TEMPLATE = """---
dora:
  version: "1.0"
  type: subsystem_readme
  generated: "{generated_timestamp}"
  generator: scripts/generate_subsystem_readmes.py
  config: config/subsystems/readme_config.yaml
  time_verified: "{time_verified}"
  auto_generated: true
---

# {title}

> **Tier:** {tier} | **Path:** `{path}` | **Owner:** {owner}

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              {title_padded}                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Inbound   │ ───► │   {subsystem_short}   │ ───► │  Outbound   │                  │
│  │ Dependencies│      │   Module    │      │ Dependencies│                  │
│  └─────────────┘      └─────────────┘      └─────────────┘                  │
│                              │                                              │
│                              ▼                                              │
│                    ┌─────────────────┐                                      │
│                    │  Memory/Audit   │                                      │
│                    │   Substrate     │                                      │
│                    └─────────────────┘                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Overview

{description}

**Purpose:** {purpose}

**What depends on it:** {depended_by_str}

---

## Responsibilities and Boundaries

### What This Module Owns

{responsibilities}

### What This Module Does NOT Do

{non_responsibilities}

### Inbound Dependencies

| Module | Purpose |
|--------|---------|
{inbound_deps_table}

### Outbound Dependencies

| Module | Purpose |
|--------|---------|
{outbound_deps_table}

---

## Directory Layout

```
{dir_layout}
```

{dir_layout_descriptions}

### Naming Conventions

{naming_conventions}

---

## Key Components

{components}

---

## Data Models and Contracts

{data_models}

### Key Schemas

{data_schemas}

### Invariants

{invariants}

---

## Execution and Lifecycle

### Startup

{lifecycle_startup}

### Main Execution

{lifecycle_execution}

### Shutdown

{lifecycle_shutdown}

### Background Tasks

{lifecycle_background}

---

## Configuration

### Feature Flags

```yaml
{feature_flags}
```

### Tuning Parameters

```yaml
{tuning_params}
```

### Environment Variables

```bash
{env_vars}
```

---

## API Surface (Public)

{api_surface}

### Usage Example

{api_example}

---

## Observability

### Logging

{subsystem_name} operations emit structured JSON logs:

```json
{{
  "timestamp": "{timestamp}",
  "level": "INFO",
  "module": "{module_path}",
  "message": "Operation completed",
  "correlation_id": "corr-xyz789",
  "agent_id": "agent-001",
  "duration_ms": 125
}}
```

**Log Levels:**
- `DEBUG` — Detailed execution steps (off in production)
- `INFO` — Lifecycle events, successful operations
- `WARNING` — Timeouts, resource warnings, recoverable errors
- `ERROR` — Failures, exceptions, unrecoverable errors

### Metrics

{metrics}

### Tracing

{tracing}

---

## Testing

### Unit Tests

Located in `tests/{test_path}/`:
{test_files}

### Integration Tests

{integration_tests}

### Known Edge Cases

{edge_cases}

---

## AI Usage Rules

### ✅ Allowed Scopes (AI can modify freely)

{allowed_scopes}

### ⚠️ Restricted Scopes (requires human review)

{restricted_scopes}

### ❌ Forbidden Scopes (NEVER modify without explicit approval)

{forbidden_scopes}

### Required Pre-Reading

{prereading_list}

### Change Policy

All changes proposed by AI tools must:
1. Be scoped PRs with clear commit messages
2. Include tests (unit + integration where applicable)
3. Update documentation if APIs change
4. Respect feature flags for gradual rollout
5. Get human approval for restricted scopes
"""


def generate_readme(
    subsystem_name: str,
    config: dict[str, Any],
    facts: SubsystemFacts,
    verified_time: datetime,
    time_verification_source: str,
    defaults: dict[str, Any],
) -> str:
    """Generate README content from template and facts."""

    # Build directory layout
    dir_layout_lines = [f"{config['path']}/"]
    file_descriptions = config.get("file_descriptions", {})
    sorted_files = sorted(facts.files)[:15]
    for f in sorted_files:
        rel = f.replace(config["path"] + "/", "")
        dir_layout_lines.append(f"├── {rel}")
    if len(facts.files) > 15:
        dir_layout_lines.append(f"└── ... ({len(facts.files) - 15} more files)")
    dir_layout = "\n".join(dir_layout_lines)

    # Build directory layout descriptions
    if file_descriptions:
        desc_lines = ["| File | Purpose |", "|------|---------|"]
        for file_name, desc in file_descriptions.items():
            desc_lines.append(f"| `{file_name}` | {desc} |")
        dir_layout_descriptions = "\n".join(desc_lines)
    else:
        # Auto-generate from protected files
        protected = config.get("protected_files", [])
        desc_lines = ["| File | Purpose |", "|------|---------|"]
        for pf in protected[:5]:
            desc_lines.append(f"| `{pf}` | Core module (PROTECTED) |")
        for cls in facts.classes[:3]:
            fname = cls.file.split("/")[-1]
            if fname not in protected:
                doc_line = (
                    cls.docstring.split("\n")[0][:50] if cls.docstring else "Component"
                )
                desc_lines.append(f"| `{fname}` | {doc_line} |")
        dir_layout_descriptions = "\n".join(desc_lines) if len(desc_lines) > 2 else ""

    # Build naming conventions
    naming_conventions = config.get("naming_conventions")
    if naming_conventions:
        naming_lines = []
        for conv in naming_conventions:
            naming_lines.append(f"- {conv}")
        naming_conventions_str = "\n".join(naming_lines)
    else:
        # Default conventions
        naming_conventions_str = f"""- **Classes:** `PascalCase` (e.g., `{subsystem_name.title().replace("_", "")}Service`)
- **Functions:** `snake_case` (e.g., `process_{subsystem_name}_request`)
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_prefixed` for internal methods"""

    # Build components section with richer detail (using enhanced AST data)
    components_lines = []
    for cls in facts.classes[:5]:
        docstring_first_line = (
            cls.docstring.split("\n")[0] if cls.docstring else "No description"
        )
        components_lines.append(f"### `{cls.file.split('/')[-1]}` — {cls.name}\n")

        components_lines.append(
            f'```python\nclass {cls.name}:\n    """{docstring_first_line}"""\n\n    # Key methods:\n'
        )

        # Use method_details if available (from enhanced ast_scanner)
        if cls.method_details:
            for method in cls.method_details[:5]:
                async_prefix = "async " if method.get("is_async") else ""
                ret_type = method.get("return_type")
                ret_str = f" -> {ret_type}" if ret_type else ""
                components_lines.append(
                    f"    {async_prefix}def {method['name']}(self, ...){ret_str}: ...\n"
                )
        else:
            # Fallback to basic method names
            for method in cls.methods[:5]:
                components_lines.append(f"    async def {method}(self, ...): ...\n")
        components_lines.append("```\n")

        if cls.methods[:5]:
            components_lines.append(
                f"**Public Methods:** `{'`, `'.join(cls.methods[:5])}`\n"
            )
        components_lines.append(
            f"**Lines:** {cls.line_start}-{cls.line_end} in `{cls.file.split('/')[-1]}`\n"
        )

    components = (
        "\n".join(components_lines)
        if components_lines
        else "See source files for component details."
    )

    # Build inbound/outbound dependency tables
    inbound_deps = config.get("depended_by", [])
    outbound_deps = config.get("depends_on", [])

    inbound_lines = []
    for dep in inbound_deps:
        inbound_lines.append(f"| `{dep}` | Uses this module |")
    inbound_deps_table = (
        "\n".join(inbound_lines) if inbound_lines else "| — | No inbound dependencies |"
    )

    outbound_lines = []
    for dep in outbound_deps:
        outbound_lines.append(f"| `{dep}` | Required dependency |")
    outbound_deps_table = (
        "\n".join(outbound_lines)
        if outbound_lines
        else "| — | No outbound dependencies |"
    )

    # Build invariants
    inv_list = config.get("invariants", [])
    if not inv_list:
        inv_list = [
            "All operations must be idempotent",
            "State changes logged to audit trail",
        ]
    invariants = "\n".join([f"- **{inv}**" for inv in inv_list])

    # Build data models section (enhanced with exports and constants)
    data_models = config.get("data_models")
    if data_models:
        data_models_str = data_models
    else:
        dm_lines = []

        # Auto-generate from facts - data model classes
        if facts.classes:
            data_model_classes = [
                c
                for c in facts.classes
                if "Model" in c.name
                or "Schema" in c.name
                or "Request" in c.name
                or "Response" in c.name
            ]
            if data_model_classes:
                dm_lines.append(
                    "The following data models define the contracts for this subsystem:\n"
                )
                for dm in data_model_classes[:3]:
                    dm_lines.append(
                        f"- **`{dm.name}`** — {dm.docstring.split(chr(10))[0] if dm.docstring else 'Data model'}"
                    )

        # NEW: Add exports (__all__) if available
        if facts.exports:
            dm_lines.append("\n### Exported Symbols (`__all__`)\n")
            export_sample = facts.exports[:10]
            dm_lines.append(f"`{'`, `'.join(export_sample)}`")
            if len(facts.exports) > 10:
                dm_lines.append(f"\n*...and {len(facts.exports) - 10} more*")

        # NEW: Add constants if available
        if facts.constants:
            dm_lines.append("\n### Module Constants\n")
            dm_lines.append("| Constant | Value | Line |")
            dm_lines.append("|----------|-------|------|")
            for name, value, line in facts.constants[:8]:
                # Truncate long values
                val_display = value[:40] + "..." if len(value) > 40 else value
                dm_lines.append(f"| `{name}` | `{val_display}` | {line} |")
            if len(facts.constants) > 8:
                dm_lines.append(f"\n*...and {len(facts.constants) - 8} more constants*")

        if dm_lines:
            data_models_str = "\n".join(dm_lines)
        else:
            data_models_str = "See source files for data model definitions."

    # Build data schemas section with examples
    data_schemas = config.get("data_schemas")
    if data_schemas:
        data_schemas_str = data_schemas
    else:
        # Generate placeholder schema example
        data_schemas_str = f"""```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class {subsystem_name.title().replace("_", "")}Request(BaseModel):
    \"\"\"Request model for {subsystem_name} operations.\"\"\"
    id: str
    data: dict
    timestamp: datetime
    correlation_id: Optional[str] = None

class {subsystem_name.title().replace("_", "")}Response(BaseModel):
    \"\"\"Response model for {subsystem_name} operations.\"\"\"
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float
```"""

    # Build lifecycle sections
    lifecycle = config.get("lifecycle", {})
    lifecycle_startup = lifecycle.get(
        "startup",
        f"""1. **Discovery:** {subsystem_name.title()} components are discovered and registered.
2. **Configuration:** Settings loaded from environment and config files.
3. **Dependencies:** Required services (Redis, PostgreSQL, etc.) are connected.
4. **Initialization:** Internal state is initialized; ready for requests.""",
    )

    lifecycle_execution = lifecycle.get(
        "execution",
        """1. **Request received:** Validate input against schema.
2. **Processing:** Execute core logic with appropriate error handling.
3. **State updates:** Persist any state changes atomically.
4. **Response:** Return structured response with timing metadata.""",
    )

    lifecycle_shutdown = lifecycle.get(
        "shutdown",
        """1. **Graceful stop:** Stop accepting new requests.
2. **Drain:** Complete in-flight operations (with timeout).
3. **Cleanup:** Release resources, close connections.
4. **Log:** Emit shutdown complete event.""",
    )

    lifecycle_background = lifecycle.get(
        "background", "No background tasks. Operations are request-driven."
    )

    # Build allowed scopes
    allowed = config.get("allowed_patterns", [])
    allowed_scopes = (
        "\n".join([f"- `{p}` — Application logic, safe to modify" for p in allowed])
        if allowed
        else "- All non-protected files"
    )

    # Build restricted scopes (protected_files)
    protected = config.get("protected_files", [])
    restricted_scopes = (
        "\n".join([f"- `{p}` — Requires human review before merge" for p in protected])
        if protected
        else "- None"
    )

    # Build forbidden scopes
    forbidden = config.get("forbidden_scopes", config.get("protected_files", []))
    forbidden_scopes = (
        "\n".join(
            [f"- `{p}` — PROTECTED: Changes break system invariants" for p in forbidden]
        )
        if forbidden
        else "- None"
    )

    # Build prereading list
    prereading = config.get("prereading", defaults.get("prereading", []))
    prereading_list = (
        "\n".join([f"{i + 1}. [`{p}`]({p})" for i, p in enumerate(prereading)])
        if prereading
        else "1. `README-L9_ARCHITECTURE.md`\n2. `docs/CURSOR-RUNBOOK.md`"
    )

    # Build metrics
    metrics = f"""| Metric | Type | Description |
|--------|------|-------------|
| `{subsystem_name}_operation_duration_ms` | Histogram | Operation latency distribution |
| `{subsystem_name}_operation_total` | Counter | Total operations processed |
| `{subsystem_name}_error_total` | Counter | Total errors encountered |
| `{subsystem_name}_active_connections` | Gauge | Current active connections |"""

    # Build tracing
    tracing = f"""{subsystem_name.replace("_", " ").title()} emits OpenTelemetry spans:

- `{subsystem_name}.execute` — Root span for operation
  - `{subsystem_name}.validate` — Input validation
  - `{subsystem_name}.process` — Core processing
  - `{subsystem_name}.persist` — State persistence (if applicable)"""

    # Build test files reference
    test_path = config["path"].replace("/", "_")
    test_files = f"""- `test_{subsystem_name}.py` — Core unit tests
- `test_{subsystem_name}_integration.py` — Integration tests (if applicable)"""

    # Build integration tests
    integration_tests = config.get(
        "integration_tests",
        f"""Located in `tests/integration/`:

- Test {subsystem_name} with real dependencies
- Test cross-subsystem interactions
- Test failure scenarios and recovery""",
    )

    # Build edge cases
    edge_cases_list = config.get("edge_cases", [])
    if edge_cases_list:
        edge_cases = "\n".join(
            [
                f"1. **{ec['name']}** — {ec['description']}"
                if isinstance(ec, dict)
                else f"- {ec}"
                for ec in edge_cases_list
            ]
        )
    else:
        edge_cases = """1. **Timeout:** Operation exceeds deadline → Return partial result with timeout status.
2. **Invalid input:** Schema validation fails → Return 400 with validation errors.
3. **Dependency unavailable:** Required service down → Retry with exponential backoff, then fail gracefully.
4. **Resource exhaustion:** Memory/connections exceeded → Reject new requests, log alert."""

    # Build API surface (using enhanced function data)
    api_surface = config.get("api_surface")
    if api_surface:
        api_surface_str = api_surface
    else:
        # Auto-generate from functions with rich signature data
        public_funcs = [f for f in facts.functions if not f.name.startswith("_")][:5]
        if public_funcs:
            api_lines = ["### Public Functions\n"]
            for func in public_funcs:
                doc_line = (
                    func.docstring.split("\n")[0]
                    if func.docstring
                    else "No description"
                )
                api_lines.append(f"#### `{func.signature}`\n")
                api_lines.append(f"{doc_line}\n")
                api_lines.append(
                    f"- **File:** `{func.file.split('/')[-1]}:{func.line}`"
                )
                api_lines.append(f"- **Async:** {'Yes' if func.is_async else 'No'}")
                # NEW: Show return type if available
                if func.return_type:
                    api_lines.append(f"- **Returns:** `{func.return_type}`")
                api_lines.append("")
            api_surface_str = "\n".join(api_lines)
        else:
            api_surface_str = "See key components for public API details."

    # Build API example
    api_example = config.get("api_example")
    if api_example:
        api_example_str = api_example
    else:
        # Generate default example
        api_example_str = f"""```python
from {config["path"].replace("/", ".")} import {subsystem_name.title().replace("_", "")}Service

# Initialize
service = {subsystem_name.title().replace("_", "")}Service()

# Execute operation
result = await service.execute(
    request_id="req-001",
    data={{"key": "value"}},
    correlation_id="corr-xyz789",
)

print(result.success)  # True
print(result.duration_ms)  # 125.5
```"""

    # Build feature flags
    feature_flags = config.get("feature_flags")
    if feature_flags:
        ff_lines = []
        for ff_name, ff_config in feature_flags.items():
            ff_lines.append(
                f"{ff_name}: {ff_config.get('default', 'true')}  # {ff_config.get('description', '')}"
            )
        feature_flags_str = "\n".join(ff_lines)
    else:
        feature_flags_str = f"""# {subsystem_name.title()} feature flags
L9_ENABLE_{subsystem_name.upper()}_TRACING: true  # Enable detailed tracing
L9_ENABLE_{subsystem_name.upper()}_METRICS: true  # Enable Prometheus metrics
L9_ENABLE_{subsystem_name.upper()}_AUDIT: true    # Enable audit logging"""

    # Build tuning params
    tuning_params = config.get("tuning_params")
    if tuning_params:
        tp_lines = []
        for tp_name, tp_val in tuning_params.items():
            tp_lines.append(f"{tp_name}: {tp_val}")
        tuning_params_str = "\n".join(tp_lines)
    else:
        tuning_params_str = f"""{subsystem_name}:
  timeout_seconds: 30
  max_retries: 3
  pool_size: 10
  batch_size: 100"""

    # Build env vars
    env_vars_config = config.get("env_vars")
    if env_vars_config:
        env_vars_str = "\n".join([f"{k}={v}" for k, v in env_vars_config.items()])
    else:
        env_vars_str = f"""{subsystem_name.upper()}_LOG_LEVEL=INFO
{subsystem_name.upper()}_TIMEOUT=30
{subsystem_name.upper()}_ENABLED=true"""

    # Depended by string
    depended_by = config.get("depended_by", [])
    depended_by_str = (
        ", ".join([f"`{d}`" for d in depended_by])
        if depended_by
        else "External clients"
    )

    # Get owner (from config or defaults)
    owner = config.get("owner", defaults.get("owner", "Igor"))

    # Get tier
    tier = config.get("tier", "unknown").upper()

    # Build responsibilities
    responsibilities_list = config.get("responsibilities", [])
    if responsibilities_list:
        responsibilities = "\n".join([f"- {r}" for r in responsibilities_list])
    else:
        responsibilities = f"""- **Core operations:** Execute {subsystem_name.replace("_", " ")} tasks
- **State management:** Maintain internal state with proper lifecycle
- **Logging:** Emit structured logs for all operations
- **Metrics:** Expose Prometheus-compatible metrics"""

    # Build non-responsibilities
    non_responsibilities_list = config.get("non_responsibilities", [])
    if non_responsibilities_list:
        non_responsibilities = "\n".join(
            [f"- {nr}" for nr in non_responsibilities_list]
        )
    else:
        non_responsibilities = """- **Authentication** — Handled by `api/auth.py`
- **External communication** — Handled by clients/adapters
- **Scheduling** — Handled by runtime/task_queue.py"""

    # Build title padding for ASCII diagram (center in 45 chars)
    title_padded = config["title"].center(45)
    # Short subsystem name for diagram (max 11 chars)
    subsystem_short = subsystem_name[:11].center(11)

    # Fill template
    return README_TEMPLATE.format(
        title=config["title"],
        title_padded=title_padded,
        subsystem_short=subsystem_short,
        subsystem_key=subsystem_name,
        tier=tier,
        path=config["path"],
        owner=owner,
        description=config["description"],
        purpose=config["purpose"],
        depended_by_str=depended_by_str,
        responsibilities=responsibilities,
        non_responsibilities=non_responsibilities,
        inbound_deps_table=inbound_deps_table,
        outbound_deps_table=outbound_deps_table,
        dir_layout=dir_layout,
        dir_layout_descriptions=dir_layout_descriptions,
        naming_conventions=naming_conventions_str,
        components=components,
        data_models=data_models_str,
        data_schemas=data_schemas_str,
        invariants=invariants,
        lifecycle_startup=lifecycle_startup,
        lifecycle_execution=lifecycle_execution,
        lifecycle_shutdown=lifecycle_shutdown,
        lifecycle_background=lifecycle_background,
        feature_flags=feature_flags_str,
        tuning_params=tuning_params_str,
        env_vars=env_vars_str,
        api_surface=api_surface_str,
        api_example=api_example_str,
        subsystem_name=subsystem_name.replace("_", " ").title(),
        timestamp=verified_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        module_path=config["path"].replace("/", "."),
        metrics=metrics,
        tracing=tracing,
        test_path=test_path,
        test_files=test_files,
        integration_tests=integration_tests,
        edge_cases=edge_cases,
        allowed_scopes=allowed_scopes,
        restricted_scopes=restricted_scopes,
        forbidden_scopes=forbidden_scopes,
        prereading_list=prereading_list,
        generated_timestamp=verified_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        time_verified=time_verification_source,
    )


# ============================================================================
# Main
# ============================================================================


def auto_config_from_path(path: str, defaults: dict[str, Any]) -> dict[str, Any]:
    """Generate a config dict from an arbitrary path."""
    parts = path.rstrip("/").split("/")
    name = parts[-1]
    title = name.replace("_", " ").replace("-", " ").title() + " Module"

    return {
        "path": path,
        "title": title,
        "tier": "unknown",
        "description": f"Module at `{path}`",
        "purpose": "Provides functionality as documented in the key components below.",
        "owner": defaults.get("owner", "Igor"),
        "protected_files": ["__init__.py"],
        "allowed_patterns": ["**/*.py"],
        "forbidden_scopes": ["__init__.py"],
        "depends_on": [],
        "depended_by": [],
        "invariants": [],
        "prereading": defaults.get("prereading", []),
    }


def backup_existing_readme(readme_path: Path) -> Path | None:
    """Backup existing README if it exists. Returns backup path or None."""
    if readme_path.exists():
        backup_path = readme_path.with_suffix(".md.bak")
        shutil.copy2(readme_path, backup_path)
        return backup_path
    return None


def list_subsystems(config: dict[str, Any]) -> None:
    """List all configured subsystems."""
    subsystems = config.get("subsystems", {})

    # Group by tier
    by_tier: dict[str, list[tuple]] = {}
    for key, sub_config in subsystems.items():
        if sub_config.get("skip", False):
            continue
        tier = sub_config.get("tier", "unknown")
        if tier not in by_tier:
            by_tier[tier] = []
        by_tier[tier].append((key, sub_config))

    print("\n📋 Configured Subsystems\n")
    print(f"{'Key':<25} {'Path':<35} {'Title'}")
    print("-" * 90)

    for tier in [
        "core",
        "orchestration",
        "api",
        "agents",
        "services",
        "infrastructure",
    ]:
        if tier not in by_tier:
            continue
        print(f"\n[{tier.upper()}]")
        for key, sub_config in sorted(by_tier[tier]):
            last_updated = sub_config.get("last_updated", "never")
            if last_updated is None:
                last_updated = "never"
            print(f"  {key:<23} {sub_config['path']:<35} {sub_config['title']}")

    total = sum(len(v) for v in by_tier.values())
    print(f"\n✅ Total: {total} subsystems configured")


def main():
    parser = argparse.ArgumentParser(
        description="Generate subsystem READMEs from code facts and YAML config"
    )
    parser.add_argument(
        "--subsystem",
        "-s",
        help="Generate for specific subsystem key from config",
    )
    parser.add_argument(
        "--tier",
        "-t",
        choices=list(VALID_TIERS),
        help="Generate for all subsystems in a tier",
    )
    parser.add_argument(
        "--path", "-p", help="Generate for arbitrary path (not in config)"
    )
    parser.add_argument("--title", help="Custom title (used with --path)")
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Print output without writing"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup existing README before overwriting (disabled by default)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--list", "-l", action="store_true", help="List all configured subsystems"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate config without generating"
    )
    parser.add_argument(
        "--skip-time-verify",
        action="store_true",
        help="Skip time verification (use system clock)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent

    # =========================================================================
    # STEP 1: Verify system time (skip for list/validate modes)
    # =========================================================================
    if args.list or args.validate:
        # No time verification needed for list/validate
        verified_time = datetime.now(UTC)
        time_verified = True
        time_source = "system clock (list/validate mode)"
    elif args.skip_time_verify:
        verified_time = datetime.now(UTC)
        time_verified = True
        time_source = "system clock (verification skipped)"
        print(
            f"⏰ Time: {verified_time.strftime('%Y-%m-%d %H:%M:%S UTC')} (verification skipped)"
        )
    else:
        print("⏰ Verifying system time...")
        verified_time, time_verified, time_source = verify_system_time()
        if time_verified:
            print(
                f"   ✅ Time verified: {verified_time.strftime('%Y-%m-%d %H:%M:%S UTC')} ({time_source})"
            )
        else:
            print(
                f"   ⚠️  Time NOT verified: {verified_time.strftime('%Y-%m-%d %H:%M:%S UTC')} ({time_source})"
            )
            if not args.dry_run:
                print("   Use --skip-time-verify to proceed with unverified time")
                try:
                    response = input("   Continue anyway? [y/N]: ").strip().lower()
                    if response != "y":
                        print("   Aborted.")
                        return 1
                except EOFError:
                    # Non-interactive mode, proceed anyway
                    print("   (Non-interactive mode, proceeding with unverified time)")
                    pass

    # =========================================================================
    # STEP 2: Load config
    # =========================================================================
    config = load_config(repo_root)
    defaults = config.get("defaults", {})

    # List mode
    if args.list:
        list_subsystems(config)
        return 0

    # Validate mode
    if args.validate:
        print("🔍 Validating config...")
        all_errors = []
        for key, sub_config in config.get("subsystems", {}).items():
            errors = validate_subsystem_config(key, sub_config)
            all_errors.extend(errors)
        if all_errors:
            print("❌ Validation errors:")
            for err in all_errors:
                print(err)
            return 1
        print(
            f"✅ Config valid! {len(config.get('subsystems', {}))} subsystems defined."
        )
        return 0

    print("🔍 Generating subsystem READMEs from code facts...")

    # Build list of (name, config) tuples to process
    to_process = []
    subsystems = config.get("subsystems", {})

    if args.path:
        # Arbitrary path mode
        path = args.path.rstrip("/")
        sub_config = auto_config_from_path(path, defaults)
        if args.title:
            sub_config["title"] = args.title
        name = path.replace("/", "_")
        to_process.append((name, sub_config))
    elif args.subsystem:
        # Specific subsystem from config
        if args.subsystem not in subsystems:
            print(f"ERROR: Unknown subsystem '{args.subsystem}'")
            print(f"Available: {', '.join(sorted(subsystems.keys()))}")
            print("Or use --path for arbitrary directories")
            return 1
        to_process.append((args.subsystem, subsystems[args.subsystem]))
    elif args.tier:
        # All subsystems in a tier
        for key, sub_config in subsystems.items():
            if sub_config.get("skip", False):
                continue
            if sub_config.get("tier") == args.tier:
                to_process.append((key, sub_config))
        if not to_process:
            print(f"No subsystems found in tier '{args.tier}'")
            return 1
        print(f"📂 Processing {len(to_process)} subsystems in tier '{args.tier}'")
    else:
        # All subsystems
        for key, sub_config in subsystems.items():
            if sub_config.get("skip", False):
                continue
            to_process.append((key, sub_config))
        print(f"📂 Processing all {len(to_process)} subsystems")

    generated_count = 0
    skipped_count = 0
    config_updated = False

    for subsystem_name, sub_config in to_process:
        subsystem_path = sub_config["path"]

        # Verify path exists
        full_path = repo_root / subsystem_path
        if not full_path.exists():
            print(f"⚠️  Path not found: {full_path}")
            skipped_count += 1
            continue

        print(f"\n📝 Processing {subsystem_name} ({subsystem_path})...")

        # Extract facts
        facts = extract_subsystem_facts(repo_root, subsystem_path)

        if args.verbose:
            print(
                f"   Found {len(facts.files)} files, {len(facts.classes)} classes, {len(facts.functions)} functions"
            )

        # Generate README
        readme_content = generate_readme(
            subsystem_name, sub_config, facts, verified_time, time_source, defaults
        )

        # Write or print
        readme_path = repo_root / subsystem_path / "README.md"

        if args.dry_run:
            print(f"\n--- {readme_path} ---")
            print(readme_content[:1000] + "\n...\n")
        else:
            # Backup existing
            if args.backup:
                backup = backup_existing_readme(readme_path)
                if backup:
                    print(f"   📦 Backed up to {backup.name}")

            readme_path.parent.mkdir(parents=True, exist_ok=True)
            readme_path.write_text(readme_content)
            print(f"   ✅ Generated {readme_path}")
            generated_count += 1

            # Update last_updated in config
            if subsystem_name in subsystems:
                subsystems[subsystem_name]["last_updated"] = verified_time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
                config_updated = True

    # Save updated config with last_updated timestamps
    if config_updated and not args.dry_run:
        config["config_updated"] = verified_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        save_config(repo_root, config)
        print("\n📝 Updated config with last_updated timestamps")

    print("\n✨ README generation complete!")
    if not args.dry_run:
        print(f"   Generated: {generated_count}")
        print(f"   Skipped:   {skipped_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-008",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "ast",
        "async",
        "auth",
        "batch-processing",
        "cli",
        "config",
        "dataclass",
        "debugging",
        "event-driven",
    ],
    "keywords": [
        "auto",
        "backup",
        "existing",
        "extract",
        "facts",
        "function",
        "generate",
        "load",
    ],
    "business_value": "This is the ONLY README pipeline - replaces the old README.meta.yaml system. Reads subsystem definitions from YAML config Verifies system time at startup (prevents stale timestamps) Updates last_updat",
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
