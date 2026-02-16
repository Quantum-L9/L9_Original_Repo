"""
L9 Agents - Role-Based Agent System
====================================

Specialized agents for the L9 coding department:

Architects:
- ArchitectAgentA: Primary system designer
- ArchitectAgentB: Challenger and validator

Coders:
- CoderAgentA: Primary implementer
- CoderAgentB: Secondary implementer (parallel work)

Quality:
- QAAgent: Quality assurance and testing

Meta:
- ReflectionAgent: Self-correction and meta-reasoning
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Role-Based Agent System",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "intelligence",
    "domain": "agent_execution",
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

from agents.architect_agent.architect_agent_a import ArchitectAgentA
from agents.architect_agent.architect_agent_b import ArchitectAgentB
from agents.base_agent import (
    AgentConfig,
    AgentMessage,
    AgentResponse,
    AgentRole,
    BaseAgent,
)
from agents.coder_agent.coder_agent_a import CoderAgentA
from agents.coder_agent.coder_agent_b import CoderAgentB
from agents.l_cto import (
    LCTOAgent,
    create_l_cto_agent,
    create_l_cto_research_agent,
    is_research_mode,
)
from agents.qa_agent import QAAgent
from agents.reflection_agent import ReflectionAgent
from agents.research_agent_impl import ResearchAgent

__all__ = [
    "AgentConfig",
    "AgentMessage",
    "AgentResponse",
    "AgentRole",
    # Architects
    "ArchitectAgentA",
    "ArchitectAgentB",
    # Base
    "BaseAgent",
    # Coders
    "CoderAgentA",
    "LCTOAgent",
    # Quality
    "QAAgent",
    # Meta
    "ReflectionAgent",
    # Research
    "ResearchAgent",
    "create_l_cto_agent",
    "create_l_cto_research_agent",
    "is_research_mode",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-007",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "agents.architect_agent.architect_agent_a",
        "agents.architect_agent.architect_agent_b",
        "agents.base_agent",
        "agents.coder_agent.coder_agent_a",
        "agents.coder_agent.coder_agent_b",
    ],
    "tags": ["agent-execution", "intelligence", "messaging", "testing", "utility"],
    "keywords": [
        "agent",
        "agents",
        "based",
        "implementer",
        "meta",
        "primary",
        "quality",
        "role",
    ],
    "business_value": "ArchitectAgentA: Primary system designer ArchitectAgentB: Challenger and validator CoderAgentA: Primary implementer CoderAgentB: Secondary implementer (parallel work) QAAgent: Quality assurance and te",
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
