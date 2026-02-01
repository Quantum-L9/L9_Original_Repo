"""
L9 Research Factory - Agents Module
Version: 1.0.0

Research agents for the multi-agent orchestration:
- BaseAgent: Shared LLM wrapper and utilities
- PlannerAgent: Decomposes research goals into steps
- ResearcherAgent: Gathers evidence via tools
- CriticAgent: Evaluates research quality
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Agents Module",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:22:00Z",
    "layer": "operations",
    "domain": "research_services",
    "module_name": "__init__",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from services.research.agents.base_agent import BaseAgent
from services.research.agents.critic_agent import CriticAgent
from services.research.agents.planner_agent import PlannerAgent
from services.research.agents.researcher_agent import ResearcherAgent

__all__ = [
    "BaseAgent",
    "CriticAgent",
    "PlannerAgent",
    "ResearcherAgent",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-033",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["adapter", "operations", "research-services"],
    "keywords": ["agent", "agents", "module", "research"],
    "business_value": "BaseAgent: Shared LLM wrapper and utilities PlannerAgent: Decomposes research goals into steps ResearcherAgent: Gathers evidence via tools CriticAgent: Evaluates research quality",
    "last_modified": "2026-01-31T22:22:00Z",
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
