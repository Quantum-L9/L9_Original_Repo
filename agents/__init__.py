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
    "CoderAgentB",
    # L-CTO (Primary)
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
