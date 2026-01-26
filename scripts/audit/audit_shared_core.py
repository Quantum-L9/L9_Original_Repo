#!/usr/bin/env python3
"""
L9 Audit Shared Core Utilities v2.0
Common components for all frontier-grade audits.

Provides:
  - CallGraphBuilder (AST-based call graph)
  - CacheManager (incremental audit caching)
  - Reporter (multi-format output)
  - GMPIntegration (GMP TODO plan generation)
  - ConfigValidator (rules engine)
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Audit Shared Core",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-06T19:43:29Z",
    "updated_at": "2026-01-14T15:05:34Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "audit_shared_core",
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
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

# =============================================================================
# CACHE MANAGER
# =============================================================================


@dataclass
class CacheEntry:
    """Single cache entry."""

    path: str
    hash: str
    modified: float
    audit_type: str


class CacheManager:
    """Manage incremental audit caching."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = cache_dir / "manifest.json"

    def get_file_hash(self, filepath: Path) -> str:
        """Calculate SHA256 hash of file content."""
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            sha.update(f.read())
        return sha.hexdigest()

    def load_manifest(self) -> dict[str, CacheEntry]:
        """Load cache manifest."""
        if not self.manifest_file.exists():
            return {}
        try:
            data = json.loads(self.manifest_file.read_text())
            return {k: CacheEntry(**v) for k, v in data.items()}
        except (json.JSONDecodeError, TypeError):
            return {}

    def save_manifest(self, manifest: dict[str, CacheEntry]):
        """Save cache manifest."""
        data = {k: asdict(v) for k, v in manifest.items()}
        self.manifest_file.write_text(json.dumps(data, indent=2))

    def get_modified_files(
        self,
        all_files: list[Path],
        audit_type: str = "general",
        repo_root: Path | None = None,
    ) -> set[Path]:
        """Return only modified files since last run."""
        manifest = self.load_manifest()
        modified = set()

        for filepath in all_files:
            rel_path = str(filepath.relative_to(repo_root or filepath.parent))
            current_hash = self.get_file_hash(filepath)

            if (
                rel_path not in manifest
                or manifest[rel_path].hash != current_hash
                or manifest[rel_path].audit_type != audit_type
            ):
                modified.add(filepath)

        return modified

    def update_manifest(
        self,
        all_files: list[Path],
        audit_type: str = "general",
        repo_root: Path | None = None,
    ):
        """Update manifest with current file hashes."""
        manifest = self.load_manifest()

        for filepath in all_files:
            rel_path = str(filepath.relative_to(repo_root or filepath.parent))
            manifest[rel_path] = CacheEntry(
                path=rel_path,
                hash=self.get_file_hash(filepath),
                modified=filepath.stat().st_mtime,
                audit_type=audit_type,
            )

        self.save_manifest(manifest)

    def invalidate(self, pattern: str | None = None):
        """Invalidate cache entries matching pattern."""
        manifest = self.load_manifest()
        if pattern:
            manifest = {k: v for k, v in manifest.items() if pattern not in k}
        else:
            manifest = {}
        self.save_manifest(manifest)


# =============================================================================
# CALL GRAPH BUILDER
# =============================================================================


@dataclass
class CallGraphEdge:
    """Edge in call graph."""

    caller: str
    caller_file: str
    callee: str
    callee_type: str  # 'function', 'method', 'class'
    line_num: int


class CallGraphBuilder(ast.NodeVisitor):
    """Build call graph from Python AST."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.calls: list[CallGraphEdge] = []
        self.definitions: dict[str, tuple[int, str]] = {}
        self.current_scope = None
        self.current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.definitions[node.name] = (node.lineno, "function")
        old_scope = self.current_scope
        self.current_scope = node.name
        self.generic_visit(node)
        self.current_scope = old_scope

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.definitions[node.name] = (node.lineno, "function")
        old_scope = self.current_scope
        self.current_scope = node.name
        self.generic_visit(node)
        self.current_scope = old_scope

    def visit_ClassDef(self, node: ast.ClassDef):
        self.definitions[node.name] = (node.lineno, "class")
        old_scope = self.current_scope
        old_class = self.current_class
        self.current_scope = node.name
        self.current_class = node.name
        self.generic_visit(node)
        self.current_scope = old_scope
        self.current_class = old_class

    def visit_Call(self, node: ast.Call):
        # Track function calls
        callee = None
        if isinstance(node.func, ast.Name):
            callee = node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                callee = f"{node.func.value.id}.{node.func.attr}"

        if callee and self.current_scope:
            self.calls.append(
                CallGraphEdge(
                    caller=self.current_scope,
                    caller_file=self.filepath,
                    callee=callee,
                    callee_type="function",
                    line_num=node.lineno,
                )
            )

        self.generic_visit(node)


# =============================================================================
# REPORTER (Multi-format)
# =============================================================================


class Reporter:
    """Generate audit reports in multiple formats."""

    def __init__(self, audit_name: str, repo_root: Path):
        self.audit_name = audit_name
        self.repo_root = repo_root
        self.report_dir = repo_root / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def to_json(self, data: dict[str, Any], filename: str | None = None) -> Path:
        """Export data as JSON."""
        if not filename:
            filename = f"audit_{self.audit_name}.json"
        output_path = self.report_dir / filename
        output_path.write_text(json.dumps(data, indent=2, default=str))
        return output_path

    def to_jsonl(
        self, records: list[dict[str, Any]], filename: str | None = None
    ) -> Path:
        """Export records as JSONL."""
        if not filename:
            filename = f"audit_{self.audit_name}.jsonl"
        output_path = self.report_dir / filename
        with open(output_path, "w") as f:
            for record in records:
                f.write(json.dumps(record, default=str) + "\n")
        return output_path

    def to_html(self, html_content: str, filename: str | None = None) -> Path:
        """Export as HTML."""
        if not filename:
            filename = f"audit_{self.audit_name}.html"
        output_path = self.report_dir / filename
        output_path.write_text(html_content)
        return output_path

    def to_markdown(self, markdown_content: str, filename: str | None = None) -> Path:
        """Export as Markdown."""
        if not filename:
            filename = f"audit_{self.audit_name}.md"
        output_path = self.report_dir / filename
        output_path.write_text(markdown_content)
        return output_path

    def generate_html_template(
        self, title: str, summary: dict[str, Any], content: str
    ) -> str:
        """Generate basic HTML template."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #2160ae; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; border-left: 4px solid #2160ae; padding-left: 15px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: #f0f7ff; padding: 15px; border-radius: 4px; border-left: 4px solid #2160ae; }}
        .summary-value {{ font-size: 28px; font-weight: bold; color: #2160ae; }}
        .summary-label {{ color: #666; font-size: 12px; text-transform: uppercase; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #f0f7ff; padding: 12px; text-align: left; border-bottom: 2px solid #2160ae; font-weight: 600; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f9f9f9; }}
        .status-ok {{ color: #388e3c; font-weight: bold; }}
        .status-warning {{ color: #f57c00; font-weight: bold; }}
        .status-error {{ color: #d32f2f; font-weight: bold; }}
        code {{ background: #f5f5f5; padding: 2px 4px; border-radius: 2px; font-family: 'Courier New', monospace; font-size: 0.9em; }}
        footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 {title}</h1>
        <p>Generated: {datetime.now().isoformat()}</p>

        <div class="summary">
"""
        for key, value in summary.items():
            sanitized_key = key.replace("_", " ").title()
            html_content += f"""
            <div class="summary-card">
                <div class="summary-value">{value}</div>
                <div class="summary-label">{sanitized_key}</div>
            </div>
"""
        html_content += f"""
        </div>

        {content}

        <footer>
            <p>L9 Audit Suite v2.0 — Frontier Grade</p>
            <p>Report generated at {datetime.now().isoformat()}</p>
        </footer>
    </div>
</body>
</html>
        """
        return html_content


# =============================================================================
# GMP INTEGRATION
# =============================================================================


@dataclass
class GMPTODOItem:
    """GMP TODO item."""

    id: str
    file_path: str
    line_range: tuple[int, int]
    action: str  # Replace, Insert, Delete, Wrap
    target: str
    expected_behavior: str
    imports_needed: list[str] = field(default_factory=list)


class GMPIntegration:
    """Generate GMP TODO plans from audit findings."""

    def __init__(self, audit_name: str):
        self.audit_name = audit_name
        self.todos: list[GMPTODOItem] = []

    def add_todo(
        self,
        file_path: str,
        line_start: int,
        line_end: int,
        action: str,
        target: str,
        behavior: str,
        imports: list[str] | None = None,
    ):
        """Add a TODO item."""
        todo_id = f"TODO_{self.audit_name.upper()}_{len(self.todos) + 1:03d}"
        self.todos.append(
            GMPTODOItem(
                id=todo_id,
                file_path=file_path,
                line_range=(line_start, line_end),
                action=action,
                target=target,
                expected_behavior=behavior,
                imports_needed=imports or [],
            )
        )

    def generate_plan(self) -> str:
        """Generate GMP TODO plan markdown."""
        plan = f"## TODO PLAN (LOCKED) — {self.audit_name}\n\n"

        for todo in self.todos:
            plan += f"""
### {todo.id}
- **File:** `{todo.file_path}:{todo.line_range[0]}-{todo.line_range[1]}`
- **Action:** {todo.action}
- **Target:** {todo.target}
- **Expected:** {todo.expected_behavior}
"""
            if todo.imports_needed:
                plan += f"- **Imports:** {', '.join(todo.imports_needed)}\n"

        return plan


# =============================================================================
# CONFIG VALIDATOR
# =============================================================================


@dataclass
class ValidationRule:
    """Single validation rule."""

    variable: str
    expected_type: str
    required: bool = True
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: list[str] | None = None


class ConfigValidator:
    """Validate configuration against rules."""

    def __init__(self):
        self.rules: dict[str, ValidationRule] = {}

    def add_rule(self, rule: ValidationRule):
        """Add validation rule."""
        self.rules[rule.variable] = rule

    def validate(self, config: dict[str, Any]) -> dict[str, list[str]]:
        """Validate config, return errors by variable."""
        errors = defaultdict(list)

        for var_name, rule in self.rules.items():
            value = config.get(var_name)

            # Check required
            if rule.required and value is None:
                errors[var_name].append("Required variable missing")
                continue

            if value is None:
                continue

            # Check type
            if rule.expected_type == "bool" and not isinstance(value, bool):
                if isinstance(value, str):
                    if value.lower() not in ["true", "false", "1", "0"]:
                        errors[var_name].append(f"Expected bool, got '{value}'")
                else:
                    errors[var_name].append(
                        f"Expected bool, got {type(value).__name__}"
                    )

            # Check range
            if rule.min_value is not None and value < rule.min_value:
                errors[var_name].append(f"Value {value} below minimum {rule.min_value}")
            if rule.max_value is not None and value > rule.max_value:
                errors[var_name].append(f"Value {value} above maximum {rule.max_value}")

            # Check allowed values
            if rule.allowed_values and value not in rule.allowed_values:
                errors[var_name].append(f"Value '{value}' not in {rule.allowed_values}")

        return dict(errors)


# =============================================================================
# OBSERVABILITY HOOKS
# =============================================================================


class ObservabilityHooks:
    """Integration with L9 observability layer."""

    def __init__(self, substrate_enabled: bool = False):
        self.substrate_enabled = substrate_enabled
        self.spans: list[dict[str, Any]] = []

    def record_span(
        self,
        name: str,
        operation: str,
        status: str,
        duration_ms: float,
        attributes: dict[str, Any] | None = None,
    ):
        """Record a span for observability."""
        span = {
            "name": name,
            "operation": operation,
            "status": status,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
            "attributes": attributes or {},
        }
        self.spans.append(span)

        if self.substrate_enabled:
            # Would send to memory substrate if available
            pass

    def export_spans(self, output_file: Path):
        """Export spans to file."""
        with open(output_file, "w") as f:
            for span in self.spans:
                f.write(json.dumps(span) + "\n")


# =============================================================================
# LOGGER SETUP
# =============================================================================


def setup_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger for the given name."""
    return structlog.get_logger(name)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-016",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "ast",
        "builder-pattern",
        "caching",
        "dataclass",
        "filesystem",
        "logging",
        "operations",
        "scripts",
        "security",
        "serialization",
    ],
    "keywords": [
        "audit",
        "builder",
        "cache",
        "core",
        "edge",
        "entry",
        "export",
        "files",
    ],
    "business_value": "CallGraphBuilder (AST-based call graph) CacheManager (incremental audit caching) Reporter (multi-format output) GMPIntegration (GMP TODO plan generation) ConfigValidator (rules engine)",
    "last_modified": "2026-01-14T15:05:34Z",
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
