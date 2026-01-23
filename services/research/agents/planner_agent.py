"""
L9 Research Factory - Planner Agent
Version: 1.0.0

Decomposes research goals into ordered steps with tool assignments.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Planner Agent",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "agent_execution",
    "module_name": "planner_agent",
    "type": "agent",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Perplexity API"],
        "memory_layers": [],
        "imported_by": ["services.research.agents.__init__"],
    },
}
# ============================================================================

import structlog
from typing import Any

from services.research.agents.base_agent import BaseAgent
from services.research.graph_state import ResearchStep

logger = structlog.get_logger(__name__)


PLANNER_SYSTEM_PROMPT = """You are a research planning agent. Your job is to decompose a research query into a clear, ordered plan of steps.

For each step, specify:
1. step_id: A unique identifier (e.g., "step_1", "step_2")
2. agent: Which agent should handle this ("researcher" for gathering info, "critic" for evaluation)
3. description: What this step accomplishes
4. query: The specific query or task for this step
5. tools: Which tools to use (e.g., ["perplexity_search"], ["web_search"])

Guidelines:
- Start with broad research, then narrow down
- Include 2-5 research steps maximum
- Always end with a synthesis step
- Be specific about what information to gather

Respond in JSON format with a "plan" array containing the steps."""


class PlannerAgent(BaseAgent):
    """
    Planner Agent - Decomposes research goals into steps.

    Takes a research query and produces a structured plan with:
    - Ordered steps
    - Tool assignments
    - Clear descriptions
    """

    def __init__(self, agent_id: str = "research_planner"):
        """Initialize planner agent."""
        super().__init__(agent_id=agent_id)

    async def run(
        self,
        query: str,
        context: str = "",
    ) -> list[ResearchStep]:
        """
        Create a research plan from a query.

        Args:
            query: The research query to plan for
            context: Optional additional context

        Returns:
            List of ResearchStep objects
        """
        logger.info(f"Planner creating plan for: {query[:100]}...")

        # Build messages
        messages = [
            self.format_system_prompt(PLANNER_SYSTEM_PROMPT),
            self.format_user_prompt(
                f"Create a research plan for this query:\n\n{query}"
                + (f"\n\nAdditional context:\n{context}" if context else "")
            ),
        ]

        # Call LLM for plan
        response = await self.call_llm_json(messages, max_tokens=1500)

        # Parse plan from response
        plan = self._parse_plan(response)

        logger.info(f"Planner created {len(plan)} steps")
        return plan

    def _parse_plan(self, response: dict[str, Any]) -> list[ResearchStep]:
        """
        Parse LLM response into list of ResearchStep.

        Args:
            response: JSON response from LLM

        Returns:
            List of ResearchStep objects
        """
        steps: list[ResearchStep] = []

        plan_data = response.get("plan", [])
        if not plan_data:
            # Try alternative keys
            plan_data = response.get("steps", response.get("research_plan", []))

        for i, step_data in enumerate(plan_data):
            if isinstance(step_data, dict):
                step = ResearchStep(
                    step_id=step_data.get("step_id", f"step_{i + 1}"),
                    agent=step_data.get("agent", "researcher"),
                    description=step_data.get("description", "Research step"),
                    query=step_data.get("query", ""),
                    tools=step_data.get("tools", ["perplexity_search"]),
                    status="pending",
                    result=None,
                )
                steps.append(step)

        # Ensure at least one step
        if not steps:
            steps = [
                ResearchStep(
                    step_id="step_1",
                    agent="researcher",
                    description="Research the query",
                    query=response.get("query", "research"),
                    tools=["perplexity_search"],
                    status="pending",
                    result=None,
                ),
            ]

        return steps

    async def refine_goal(self, query: str) -> str:
        """
        Refine a research query into a clearer goal.

        Args:
            query: Raw user query

        Returns:
            Refined, clearer research goal
        """
        messages = [
            self.format_system_prompt(
                "You are a research goal clarifier. Rewrite the user's query "
                "as a clear, specific research goal. Keep it concise but complete. "
                "Respond with just the refined goal, no explanation."
            ),
            self.format_user_prompt(f"Refine this research query:\n\n{query}"),
        ]

        refined = await self.call_llm(messages, max_tokens=200)
        return refined.strip()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-012",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["agent", "agent-execution", "async", "logging", "messaging", "operations"],
    "keywords": ["agent", "goal", "planner", "refine", "research"],
    "business_value": "Implements PlannerAgent for planner agent functionality",
    "last_modified": "2026-01-07T13:35:58Z",
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
