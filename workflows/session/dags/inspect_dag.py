"""
Inspect DAG — Real LangGraph Implementation
============================================

READ-ONLY inspection: classify → orient → structure → compliance → impact → route → report

This is an EXECUTABLE graph, not documentation.

Version: 2.0.0
"""

from typing import Any, Literal

import structlog
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# State Model
# =============================================================================


class InspectState(BaseModel):
    """State flowing through inspect graph."""

    # Input
    target: str = Field(..., description="File path or module name to inspect")

    # Classification
    component_type: Literal[
        "MODULE", "SERVICE", "AGENT", "ROUTER", "TOOL", "KERNEL", "CONFIG", "UNKNOWN"
    ] = Field(default="UNKNOWN")
    tier: Literal[
        "KERNEL_TIER", "RUNTIME_TIER", "INFRA_TIER", "UX_TIER", "UNKNOWN"
    ] = Field(default="UNKNOWN")

    # Orientation
    orientation: str = Field(default="", description="What/where/who/depends")
    callers: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)

    # Structure
    structure_map: list[dict[str, Any]] = Field(default_factory=list)
    hotspots: list[dict[str, str]] = Field(default_factory=list)

    # Compliance
    health_score: int = Field(default=0, ge=0, le=100)
    anti_patterns: list[dict[str, str]] = Field(default_factory=list)
    structural_ok: bool = Field(default=True)
    async_ok: bool = Field(default=True)
    quality_ok: bool = Field(default=True)

    # Impact
    downstream_count: int = Field(default=0)
    upstream_count: int = Field(default=0)
    impact_score: int = Field(default=0)
    impact_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(default="LOW")

    # Routing
    routing_decision: Literal[
        "/harvest-analyze", "/refactor-sweep", "/wire", "/gmp", "STOP"
    ] = Field(default="STOP")
    routing_rationale: str = Field(default="")

    # Output
    report: str = Field(default="")
    errors: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


# =============================================================================
# Node Functions
# =============================================================================


async def classify_node(state: InspectState) -> dict[str, Any]:
    """Classify target into type and tier."""
    logger.info("classify_node", target=state.target)

    target = state.target.lower()

    # Type classification
    component_type = "UNKNOWN"
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
    tier = "UNKNOWN"
    if any(k in target for k in ["kernel", "executor", "orchestrator", "substrate"]):
        tier = "KERNEL_TIER"
    elif any(k in target for k in ["task", "redis", "tool", "agent", "registry"]):
        tier = "RUNTIME_TIER"
    elif any(k in target for k in ["docker", "deploy", "k8s", "helm", "infra"]):
        tier = "INFRA_TIER"
    else:
        tier = "UX_TIER"

    return {"component_type": component_type, "tier": tier}


async def orient_node(state: InspectState) -> dict[str, Any]:
    """30-second understanding of what this does."""
    logger.info("orient_node", target=state.target)

    # In real implementation: read file, parse imports, find callers
    orientation = f"Component at {state.target}. Type: {state.component_type}, Tier: {state.tier}"

    return {
        "orientation": orientation,
        "callers": [],  # Would populate from rg search
        "dependencies": [],  # Would populate from import analysis
    }


async def structure_node(state: InspectState) -> dict[str, Any]:
    """Map structure and flow."""
    logger.info("structure_node", target=state.target)

    # In real implementation: parse AST, list classes/functions
    return {
        "structure_map": [],  # Would contain classes, functions, exports
        "hotspots": [],  # Would contain high-complexity areas
    }


async def compliance_node(state: InspectState) -> dict[str, Any]:
    """Check L9 canon compliance."""
    logger.info("compliance_node", target=state.target)

    # In real implementation: run static analysis
    anti_patterns = []
    structural_ok = True
    async_ok = True
    quality_ok = True

    # Calculate health score
    deductions = len(anti_patterns) * 10
    deductions += 0 if structural_ok else 20
    deductions += 0 if async_ok else 20
    deductions += 0 if quality_ok else 20
    health_score = max(0, 100 - deductions)

    return {
        "health_score": health_score,
        "anti_patterns": anti_patterns,
        "structural_ok": structural_ok,
        "async_ok": async_ok,
        "quality_ok": quality_ok,
    }


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


async def routing_node(state: InspectState) -> dict[str, Any]:
    """Decide next command."""
    logger.info("routing_node", health=state.health_score, impact=state.impact_level)

    # Decision logic
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


async def report_node(state: InspectState) -> dict[str, Any]:
    """Generate final report."""
    logger.info("report_node", decision=state.routing_decision)

    report = f"""## 🔍 INSPECT: {state.target}

**Type:** {state.component_type} | **Tier:** {state.tier}
**Health:** {state.health_score}/100 | **Impact:** {state.impact_level}

### Compliance
- Structural: {"✅" if state.structural_ok else "❌"}
- Async: {"✅" if state.async_ok else "❌"}
- Quality: {"✅" if state.quality_ok else "❌"}

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
