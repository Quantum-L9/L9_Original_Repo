"""
Inspect DAG — Real LangGraph Implementation
============================================

READ-ONLY inspection: classify → orient → structure → compliance → impact → route → report

Supports TWO modes:
  1. Existing file: /inspect core/tools/registry_adapter.py
  2. External code: /inspect current_work/guide.md  (markdown with code blocks)

External code mode runs validate_external_code.py checks automatically.

Version: 3.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Inspect Dag",
    "module_version": "3.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "inspect_dag",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Redis"],
        "memory_layers": [],
        "imported_by": ["workflows.dags.__init__"],
    },
}
# ============================================================================

import ast
from pathlib import Path
from typing import Any, Literal

import structlog
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from core.decorators import must_stay_async
from tools.validation.validate_external_code import (
    ValidationIssue,
    extract_python_code_blocks,
    validate_adr_compliance,
    validate_config_values,
    validate_imports,
)

logger = structlog.get_logger(__name__)

# Repo root for import resolution
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# =============================================================================
# State Model
# =============================================================================


class InspectState(BaseModel):
    """State flowing through inspect graph."""

    # Input
    target: str = Field(..., description="File path or module name to inspect")

    # Mode detection
    is_external: bool = Field(
        default=False,
        description="True if target is external code (markdown, non-repo file)",
    )
    code_blocks: list[dict[str, Any]] = Field(
        default_factory=list, description="Extracted code blocks from markdown"
    )

    # Classification
    component_type: Literal[
        "MODULE",
        "SERVICE",
        "AGENT",
        "ROUTER",
        "TOOL",
        "KERNEL",
        "CONFIG",
        "EXTERNAL",
        "UNKNOWN",
    ] = Field(default="UNKNOWN")
    tier: Literal["KERNEL_TIER", "RUNTIME_TIER", "INFRA_TIER", "UX_TIER", "UNKNOWN"] = (
        Field(default="UNKNOWN")
    )

    # Orientation
    orientation: str = Field(default="", description="What/where/who/depends")
    callers: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)

    # Structure
    structure_map: list[dict[str, Any]] = Field(default_factory=list)
    hotspots: list[dict[str, str]] = Field(default_factory=list)

    # Compliance — validation issues from real checks
    health_score: int = Field(default=0, ge=0, le=100)
    anti_patterns: list[dict[str, str]] = Field(default_factory=list)
    validation_issues: list[dict[str, str]] = Field(
        default_factory=list, description="Issues from validate_external_code"
    )
    structural_ok: bool = Field(default=True)
    async_ok: bool = Field(default=True)
    quality_ok: bool = Field(default=True)
    import_ok: bool = Field(default=True)
    adr_ok: bool = Field(default=True)
    config_ok: bool = Field(default=True)

    # Impact
    downstream_count: int = Field(default=0)
    upstream_count: int = Field(default=0)
    impact_score: int = Field(default=0)
    impact_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(default="LOW")

    # Routing
    routing_decision: Literal[
        "/harvest-analyze",
        "/refactor-sweep",
        "/wire",
        "/gmp",
        "STOP",
        "FIX-BEFORE-IMPORT",
    ] = Field(default="STOP")
    routing_rationale: str = Field(default="")

    # Output
    report: str = Field(default="")
    errors: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# =============================================================================
# Node Functions
# =============================================================================


@must_stay_async("callers use await")
async def classify_node(state: InspectState) -> dict[str, Any]:
    """Classify target into type and tier. Detect external code."""
    logger.info("classify_node", target=state.target)

    target = state.target.lower()
    target_path = _REPO_ROOT / state.target

    # --- Detect external code ---
    is_external = False
    code_blocks: list[dict[str, Any]] = []

    if target.endswith(".md"):
        # Markdown file — extract code blocks
        is_external = True
        if target_path.exists():
            raw_blocks = extract_python_code_blocks(target_path)
            code_blocks = [{"line": ln, "code": code} for ln, code in raw_blocks]
            logger.info("external_code_detected", blocks=len(code_blocks))
    elif not target_path.exists() and not (_REPO_ROOT / f"{state.target}.py").exists():
        # File doesn't exist in repo — treat as external/proposed
        is_external = True

    if is_external:
        return {
            "is_external": True,
            "code_blocks": code_blocks,
            "component_type": "EXTERNAL",
            "tier": "UX_TIER",
        }

    # --- Existing file classification ---
    component_type: str = "UNKNOWN"
    if "router" in target or "routes" in target:
        component_type = "ROUTER"
    elif "agent" in target:
        component_type = "AGENT"
    elif "service" in target:
        component_type = "SERVICE"
    elif "tool" in target:
        component_type = "TOOL"
    elif "kernel" in target:
        component_type = "KERNEL"
    elif target.endswith((".yaml", ".yml", ".toml", ".env")):
        component_type = "CONFIG"
    else:
        component_type = "MODULE"

    # Tier classification
    tier: str = "UNKNOWN"
    if any(k in target for k in ["kernel", "executor", "orchestrator", "substrate"]):
        tier = "KERNEL_TIER"
    elif any(k in target for k in ["task", "redis", "tool", "agent", "registry"]):
        tier = "RUNTIME_TIER"
    elif any(k in target for k in ["docker", "deploy", "k8s", "helm", "infra"]):
        tier = "INFRA_TIER"
    else:
        tier = "UX_TIER"

    return {"component_type": component_type, "tier": tier}


@must_stay_async("callers use await")
async def orient_node(state: InspectState) -> dict[str, Any]:
    """30-second understanding of what this does."""
    logger.info("orient_node", target=state.target, is_external=state.is_external)

    if state.is_external:
        block_count = len(state.code_blocks)
        total_lines = sum(b["code"].count("\n") + 1 for b in state.code_blocks)
        orientation = (
            f"External code at {state.target}. "
            f"{block_count} Python code block(s), ~{total_lines} total lines. "
            f"Requires validation before import into L9."
        )
        return {"orientation": orientation}

    # Existing file — read imports
    target_path = _REPO_ROOT / state.target
    dependencies: list[str] = []
    if target_path.exists() and target_path.suffix == ".py":
        try:
            tree = ast.parse(target_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    dependencies.append(node.module)
        except (SyntaxError, OSError):
            pass

    orientation = (
        f"Component at {state.target}. Type: {state.component_type}, Tier: {state.tier}. "
        f"Imports: {len(dependencies)} modules."
    )

    return {
        "orientation": orientation,
        "dependencies": dependencies,
    }


@must_stay_async("callers use await")
async def structure_node(state: InspectState) -> dict[str, Any]:
    """Map structure: parse AST for classes, functions, imports."""
    logger.info("structure_node", target=state.target, is_external=state.is_external)

    structure_map: list[dict[str, Any]] = []
    hotspots: list[dict[str, str]] = []
    dependencies: list[str] = []

    # Collect all code to analyze
    code_snippets: list[str] = []

    if state.is_external and state.code_blocks:
        code_snippets = [b["code"] for b in state.code_blocks]
    else:
        target_path = _REPO_ROOT / state.target
        if target_path.exists() and target_path.suffix == ".py":
            try:
                code_snippets = [target_path.read_text(encoding="utf-8")]
            except OSError as exc:
                return {"errors": [f"Cannot read {state.target}: {exc}"]}

    for code in code_snippets:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            hotspots.append({"pattern": "syntax_error", "location": str(exc)})
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n.name
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                structure_map.append(
                    {
                        "type": "class",
                        "name": node.name,
                        "line": node.lineno,
                        "methods": methods,
                    }
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip methods (already captured under class)
                if not any(
                    isinstance(p, ast.ClassDef)
                    for p in ast.walk(tree)
                    if hasattr(p, "body") and node in getattr(p, "body", [])
                ):
                    is_async = isinstance(node, ast.AsyncFunctionDef)
                    structure_map.append(
                        {
                            "type": "async_function" if is_async else "function",
                            "name": node.name,
                            "line": node.lineno,
                        }
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                dependencies.append(node.module)

        # Hotspot: functions > 50 lines
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line = getattr(node, "end_lineno", node.lineno)
                length = end_line - node.lineno
                if length > 50:
                    hotspots.append(
                        {
                            "pattern": "long_function",
                            "location": f"{node.name} ({length} lines at L{node.lineno})",
                        }
                    )

    return {
        "structure_map": structure_map,
        "hotspots": hotspots,
        "dependencies": dependencies,
    }


def _issue_to_dict(issue: ValidationIssue) -> dict[str, str]:
    """Convert ValidationIssue to serializable dict."""
    return {
        "severity": issue.severity,
        "type": issue.type,
        "message": issue.issue,
        "line": str(issue.line),
        "suggestion": issue.fix_suggestion,
    }


def _run_validators_on_code(code: str) -> list[ValidationIssue]:
    """Run all validators from validate_external_code on a code string."""
    issues: list[ValidationIssue] = []
    issues.extend(validate_imports(code, _REPO_ROOT))
    issues.extend(validate_adr_compliance(code))
    issues.extend(validate_config_values(code, _REPO_ROOT))
    return issues


@must_stay_async("callers use await")
async def compliance_node(state: InspectState) -> dict[str, Any]:
    """Check L9 canon compliance using real validators."""
    logger.info("compliance_node", target=state.target, is_external=state.is_external)

    all_issues: list[ValidationIssue] = []
    anti_patterns: list[dict[str, str]] = list(state.anti_patterns)

    # --- Collect code to validate ---
    code_snippets: list[str] = []

    if state.is_external and state.code_blocks:
        code_snippets = [b["code"] for b in state.code_blocks]
    else:
        target_path = _REPO_ROOT / state.target
        if target_path.exists() and target_path.suffix == ".py":
            try:
                code_snippets = [target_path.read_text(encoding="utf-8")]
            except OSError:
                pass

    # --- Run validators ---
    for code in code_snippets:
        all_issues.extend(_run_validators_on_code(code))

    # --- Classify results ---
    import_issues = [i for i in all_issues if i.type == "import_error"]
    adr_issues = [i for i in all_issues if i.type == "adr_violation"]
    config_issues = [i for i in all_issues if i.type == "config_drift"]
    critical_issues = [i for i in all_issues if i.severity in ("critical", "high")]

    import_ok = len(import_issues) == 0
    adr_ok = len(adr_issues) == 0
    config_ok = len(config_issues) == 0

    # --- Structural checks from hotspots ---
    structural_ok = not any(h.get("pattern") == "syntax_error" for h in state.hotspots)

    # --- Async check: sync I/O in async functions ---
    async_ok = True
    for code in code_snippets:
        if "time.sleep(" in code and "async def" in code:
            async_ok = False
            anti_patterns.append(
                {
                    "pattern": "sync_io_in_async",
                    "location": "time.sleep() in async function",
                }
            )

    # --- Quality: missing DORA header ---
    quality_ok = True
    for code in code_snippets:
        if "class " in code or "def " in code:
            if "__dora_meta__" not in code:
                quality_ok = False
                anti_patterns.append(
                    {
                        "pattern": "missing_dora_header",
                        "location": "No __dora_meta__ dict found",
                    }
                )
                break  # Only flag once

    # --- Convert issues to anti_patterns for existing report format ---
    for issue in all_issues:
        if issue.severity in ("critical", "high"):
            anti_patterns.append(
                {
                    "pattern": f"{issue.type}_{issue.severity}",
                    "location": f"L{issue.line}: {issue.issue}",
                }
            )

    # --- Health score ---
    deductions = 0
    deductions += len(critical_issues) * 15
    deductions += len(adr_issues) * 10
    deductions += len(config_issues) * 5
    deductions += 0 if structural_ok else 20
    deductions += 0 if async_ok else 20
    deductions += 0 if quality_ok else 10
    deductions += 0 if import_ok else 25
    health_score = max(0, 100 - deductions)

    validation_issues = [_issue_to_dict(i) for i in all_issues]

    return {
        "health_score": health_score,
        "anti_patterns": anti_patterns,
        "validation_issues": validation_issues,
        "structural_ok": structural_ok,
        "async_ok": async_ok,
        "quality_ok": quality_ok,
        "import_ok": import_ok,
        "adr_ok": adr_ok,
        "config_ok": config_ok,
    }


@must_stay_async("callers use await")
async def impact_node(state: InspectState) -> dict[str, Any]:
    """Calculate impact score."""
    logger.info("impact_node", target=state.target)

    # In real implementation: count importers/imports
    downstream = 0  # Would count via rg
    upstream = 0  # Would count imports

    # Cross-layer risk
    cross_layer_risk = 0
    if state.tier == "KERNEL_TIER":
        cross_layer_risk = 10

    score = (downstream * 2) + upstream + cross_layer_risk

    # Level
    if score <= 5:
        level = "LOW"
    elif score <= 15:
        level = "MEDIUM"
    elif score <= 30:
        level = "HIGH"
    else:
        level = "CRITICAL"

    return {
        "downstream_count": downstream,
        "upstream_count": upstream,
        "impact_score": score,
        "impact_level": level,
    }


@must_stay_async("callers use await")
async def routing_node(state: InspectState) -> dict[str, Any]:
    """Decide next command."""
    logger.info("routing_node", health=state.health_score, impact=state.impact_level)

    # --- External code: gate on validation ---
    if state.is_external:
        error_count = sum(
            1
            for i in state.validation_issues
            if i.get("severity") in ("critical", "high")
        )
        if error_count > 0:
            decision = "FIX-BEFORE-IMPORT"
            rationale = (
                f"{error_count} error(s) must be fixed before this code can enter L9. "
                f"Run: make validate-external-code FILE={state.target}"
            )
        elif state.health_score >= 80:
            decision = "/harvest-analyze"
            rationale = "External code passes validation — ready for harvest"
        else:
            decision = "FIX-BEFORE-IMPORT"
            rationale = f"Health {state.health_score}/100 — fix warnings before import"
        return {"routing_decision": decision, "routing_rationale": rationale}

    # --- Existing file routing ---
    if state.health_score >= 80 and state.impact_level == "LOW":
        decision = "STOP"
        rationale = "Healthy, low impact, no action needed"
    elif state.anti_patterns:
        decision = "/refactor-sweep"
        rationale = f"Anti-patterns detected: {len(state.anti_patterns)}"
    elif not state.structural_ok:
        decision = "/wire"
        rationale = "Structural issues - wiring needed"
    elif state.tier == "KERNEL_TIER":
        decision = "/gmp"
        rationale = "KERNEL_TIER requires full GMP"
    else:
        decision = "STOP"
        rationale = "No clear action required"

    return {"routing_decision": decision, "routing_rationale": rationale}


@must_stay_async("callers use await")
async def report_node(state: InspectState) -> dict[str, Any]:
    """Generate final report."""
    logger.info("report_node", decision=state.routing_decision)

    # --- Validation issues section ---
    issues_section = ""
    if state.validation_issues:
        errors = [
            i
            for i in state.validation_issues
            if i.get("severity") in ("critical", "high")
        ]
        warnings = [
            i for i in state.validation_issues if i.get("severity") in ("medium", "low")
        ]

        issue_lines = []
        for issue in errors:
            issue_lines.append(
                f"- **{issue.get('severity', 'error').upper()}** [{issue.get('type', '?')}] "
                f"L{issue.get('line', '?')}: {issue.get('message', '')} "
                f"→ {issue.get('suggestion', '')}"
            )
        for issue in warnings:
            issue_lines.append(
                f"- **{issue.get('severity', 'warn').upper()}** [{issue.get('type', '?')}] "
                f"L{issue.get('line', '?')}: {issue.get('message', '')}"
            )

        issues_section = f"""
### Validation Issues ({len(errors)} critical/high, {len(warnings)} medium/low)
{chr(10).join(issue_lines)}
"""
    else:
        issues_section = "\n### Validation Issues\nNone detected\n"

    # --- Structure section ---
    structure_lines = []
    for item in state.structure_map[:20]:  # Cap at 20 for readability
        kind = item.get("type", "?")
        name = item.get("name", "?")
        line = item.get("line", "?")
        methods = item.get("methods", [])
        if methods:
            structure_lines.append(
                f"- `{kind}` **{name}** (L{line}) — {len(methods)} methods"
            )
        else:
            structure_lines.append(f"- `{kind}` **{name}** (L{line})")
    structure_section = (
        chr(10).join(structure_lines)
        if structure_lines
        else "No Python structures found"
    )

    # --- Mode label ---
    mode_label = "EXTERNAL CODE" if state.is_external else "EXISTING FILE"

    report = f"""## 🔍 INSPECT [{mode_label}]: {state.target}

**Type:** {state.component_type} | **Tier:** {state.tier}
**Health:** {state.health_score}/100 | **Impact:** {state.impact_level}

### Compliance
- Imports: {"✅" if state.import_ok else "❌"}
- ADR: {"✅" if state.adr_ok else "❌"}
- Config: {"✅" if state.config_ok else "❌"}
- Structural: {"✅" if state.structural_ok else "❌"}
- Async: {"✅" if state.async_ok else "❌"}
- Quality (DORA): {"✅" if state.quality_ok else "❌"}
{issues_section}
### Structure
{structure_section}

### Anti-Patterns
{chr(10).join(f"- {p.get('pattern', 'unknown')}: {p.get('location', '')}" for p in state.anti_patterns) or "None detected"}

### Decision
➡️ **NEXT:** `{state.routing_decision}`

**Rationale:** {state.routing_rationale}"""

    return {"report": report}


# =============================================================================
# Graph Builder
# =============================================================================


def build_inspect_graph() -> StateGraph:
    """
    Build and compile the inspect graph.

    Flow: START → classify → orient → structure → compliance → impact → routing → report → END
    """
    graph = StateGraph(InspectState)

    # Add nodes
    graph.add_node("classify", classify_node)
    graph.add_node("orient", orient_node)
    graph.add_node("structure", structure_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("impact", impact_node)
    graph.add_node("routing", routing_node)
    graph.add_node("report", report_node)

    # Linear flow
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "orient")
    graph.add_edge("orient", "structure")
    graph.add_edge("structure", "compliance")
    graph.add_edge("compliance", "impact")
    graph.add_edge("impact", "routing")
    graph.add_edge("routing", "report")
    graph.add_edge("report", END)

    return graph.compile()


# =============================================================================
# Execution
# =============================================================================


async def run_inspect(target: str) -> InspectState:
    """
    Execute inspect graph on target.

    Args:
        target: File path or module name

    Returns:
        Final state with report
    """
    logger.info("run_inspect", target=target)

    graph = build_inspect_graph()
    initial_state = InspectState(target=target)

    result = await graph.ainvoke(initial_state)
    return InspectState.model_validate(result)


# =============================================================================
# Export for registry compatibility
# =============================================================================

INSPECT_DAG = build_inspect_graph()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-034",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "async",
        "data-models",
        "logging",
        "operations",
        "pydantic",
        "schema",
        "static-analysis",
        "streaming",
        "validation",
    ],
    "keywords": [
        "build",
        "classify",
        "compliance",
        "dag",
        "graph",
        "impact",
        "inspect",
        "orient",
    ],
    "business_value": "EXECUTABLE graph with real validation. External code gate. Version: 3.0.0",
    "last_modified": "2026-01-31T22:21:54Z",
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
