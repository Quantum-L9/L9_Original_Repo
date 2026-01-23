"""
L9 Research Factory - Agents Module
Version: 1.0.0

Research agents for the multi-agent orchestration:
- BaseAgent: Shared LLM wrapper and utilities
- PlannerAgent: Decomposes research goals into steps
- ResearcherAgent: Gathers evidence via tools
- CriticAgent: Evaluates research quality
"""

from services.research.agents.base_agent import BaseAgent
from services.research.agents.critic_agent import CriticAgent
from services.research.agents.planner_agent import PlannerAgent
from services.research.agents.researcher_agent import ResearcherAgent

__all__ = [
    "BaseAgent",
    "PlannerAgent",
    "ResearcherAgent",
    "CriticAgent",
]
