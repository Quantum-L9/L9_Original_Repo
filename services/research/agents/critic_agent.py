"""
L9 Research Factory - Critic Agent
Version: 1.0.0

Evaluates research quality and provides feedback.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Critic Agent",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "agent_execution",
    "module_name": "critic_agent",
    "type": "agent",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["services.research.agents.__init__"],
    },
}
# ============================================================================

from typing import Any

import structlog

from services.research.agents.base_agent import BaseAgent
from services.research.graph_state import Evidence

logger = structlog.get_logger(__name__)


CRITIC_SYSTEM_PROMPT = """You are a research quality critic. Your job is to evaluate research findings and provide constructive feedback.

Evaluate based on:
1. Completeness: Does the research answer the query fully?
2. Accuracy: Are the findings well-supported by evidence?
3. Depth: Is there sufficient detail and analysis?
4. Sources: Are sources cited and reliable?
5. Clarity: Is the synthesis clear and well-organized?

Respond in JSON format with:
{
  "score": 0.0-1.0,
  "feedback": "Detailed feedback on the research quality",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["How to improve"],
  "approved": true/false
}

Score guide:
- 0.9-1.0: Excellent, comprehensive research
- 0.7-0.89: Good quality, minor gaps
- 0.5-0.69: Acceptable but needs improvement
- Below 0.5: Insufficient, needs retry"""


class CriticAgent(BaseAgent):
    """
    Critic Agent - Evaluates research quality.

    Provides:
    - Quality scoring (0.0-1.0)
    - Detailed feedback
    - Approval/rejection decision
    """

    def __init__(
        self,
        agent_id: str = "research_critic",
        approval_threshold: float = 0.7,
    ):
        """
        Initialize critic agent.

        Args:
            agent_id: Unique agent identifier
            approval_threshold: Minimum score for approval
        """
        super().__init__(agent_id=agent_id)
        self.approval_threshold = approval_threshold

    async def run(
        self,
        query: str,
        evidence: list[Evidence],
        summary: str,
    ) -> dict[str, Any]:
        """
        Evaluate research quality.

        Args:
            query: Original research query
            evidence: Gathered evidence
            summary: Synthesized summary

        Returns:
            Evaluation dict with score, feedback, approved
        """
        logger.info("Critic evaluating research quality")

        # Format evidence for evaluation
        evidence_text = ""
        for i, ev in enumerate(evidence, 1):
            evidence_text += (
                f"\n[Evidence {i}] (confidence: {ev.get('confidence', 0):.2f})\n"
            )
            evidence_text += f"{ev.get('content', '')[:500]}...\n"

        messages = [
            self.format_system_prompt(CRITIC_SYSTEM_PROMPT),
            self.format_user_prompt(
                f"Original Query: {query}\n\n"
                f"Evidence Gathered:{evidence_text}\n\n"
                f"Synthesized Summary:\n{summary}\n\n"
                "Evaluate the quality of this research and respond in JSON format."
            ),
        ]

        response = await self.call_llm_json(messages, max_tokens=1000)

        # Parse evaluation
        score = float(response.get("score", 0.5))
        feedback = response.get("feedback", "No feedback provided")
        approved = score >= self.approval_threshold

        # Override approval based on threshold
        if score < self.approval_threshold:
            approved = False

        evaluation = {
            "score": score,
            "feedback": feedback,
            "strengths": response.get("strengths", []),
            "weaknesses": response.get("weaknesses", []),
            "suggestions": response.get("suggestions", []),
            "approved": approved,
        }

        logger.info(f"Critic score: {score:.2f}, approved: {approved}")
        return evaluation

    async def quick_check(
        self,
        query: str,
        summary: str,
    ) -> tuple[float, str]:
        """
        Quick quality check without full evaluation.

        Args:
            query: Original query
            summary: Summary to check

        Returns:
            Tuple of (score, brief_feedback)
        """
        messages = [
            self.format_system_prompt(
                "Quickly evaluate if this summary adequately answers the query. "
                "Respond with just a score (0.0-1.0) and one sentence of feedback. "
                'Format: {"score": 0.X, "feedback": "..."}'
            ),
            self.format_user_prompt(f"Query: {query}\n\nSummary: {summary[:1000]}"),
        ]

        response = await self.call_llm_json(messages, max_tokens=100)

        score = float(response.get("score", 0.5))
        feedback = response.get("feedback", "Quick check completed")

        return score, feedback


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-013",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["agent", "agent-execution", "async", "logging", "messaging", "operations"],
    "keywords": ["agent", "check", "critic", "quick", "research"],
    "business_value": "Implements CriticAgent for critic agent functionality",
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
