"""
L9 Simulation - IR Candidate Evaluation Engine
==============================================

Simulates IR graphs to evaluate:
- Feasibility
- Risk assessment
- Resource requirements
- Failure modes

Components:
- SimulationEngine: Core simulation runner
- ScenarioLoader: Load and define scenarios
- OutcomeEvaluator: Evaluate and score results
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "IR Candidate Evaluation Engine",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "learning",
    "domain": "simulation",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from simulation.outcome_evaluator import (
    EvaluationCriteria,
    EvaluationResult,
    OutcomeEvaluator,
)
from simulation.scenario_loader import Scenario, ScenarioLoader, ScenarioType
from simulation.simulation_engine import (
    SimulationConfig,
    SimulationEngine,
    SimulationMetrics,
    SimulationRun,
)

__all__ = [
    "EvaluationCriteria",
    "EvaluationResult",
    # Evaluation
    "OutcomeEvaluator",
    "Scenario",
    # Scenarios
    "ScenarioLoader",
    "ScenarioType",
    "SimulationConfig",
    # Engine
    "SimulationEngine",
    "SimulationMetrics",
    "SimulationRun",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SIM-LEAR-002",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["learning", "metrics", "simulation", "utility"],
    "keywords": ["candidate", "engine", "evaluate", "evaluation", "simulation"],
    "business_value": "Utility module for   init  ",
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
