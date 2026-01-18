"""
L9 Meta Orchestrator - Blueprint Adapter
Version: 1.0.0

Adapter for LLM-based blueprint evaluation and improvement suggestions.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Blueprint Adapter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "adapter",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import structlog
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

from .interface import (
    Blueprint,
    BlueprintEvaluation,
    BlueprintScore,
    EvaluationCriteria,
)

logger = structlog.get_logger(__name__)


class BlueprintAdapter:
    """
    Adapter for LLM-based blueprint evaluation.

    Uses GPT-4 to:
    - Score blueprints against criteria
    - Generate improvement suggestions
    - Provide detailed rationales
    """

    def __init__(self, openai_client: AsyncOpenAI, model: str = "gpt-4"):
        """Initialize blueprint adapter."""
        self._client = openai_client
        self._model = model
        logger.info(f"BlueprintAdapter initialized with model: {model}")

    async def score_blueprint(
        self,
        blueprint: Blueprint,
        criteria: List[EvaluationCriteria],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[BlueprintScore]:
        """Score a blueprint against all criteria using LLM."""
        logger.info(f"Scoring blueprint: {blueprint.id}")

        prompt = self._build_scoring_prompt(blueprint, criteria, context)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert architectural evaluator. Score blueprints objectively against criteria.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        scores = self._parse_scores(response.choices[0].message.content, criteria)
        return scores

    async def generate_improvements(
        self, blueprint: Blueprint, evaluation: BlueprintEvaluation
    ) -> List[str]:
        """Generate improvement suggestions using LLM."""
        logger.info(f"Generating improvements for: {blueprint.id}")

        prompt = self._build_improvement_prompt(blueprint, evaluation)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert architectural consultant. Provide actionable improvement suggestions.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        suggestions = self._parse_suggestions(response.choices[0].message.content)
        return suggestions

    def _build_scoring_prompt(
        self,
        blueprint: Blueprint,
        criteria: List[EvaluationCriteria],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build prompt for scoring."""
        prompt = f"""
# Blueprint Evaluation

## Blueprint Details
- **ID:** {blueprint.id}
- **Type:** {blueprint.type}
- **Name:** {blueprint.name}
- **Description:** {blueprint.description}

## Blueprint Content
```json
{blueprint.content}
```

## Evaluation Criteria
"""
        for criterion in criteria:
            prompt += f"\n### {criterion.name} (weight: {criterion.weight})\n"
            prompt += f"{criterion.description}\n"

        if context:
            prompt += f"\n## Additional Context\n{context}\n"

        prompt += """
## Task
For each criterion, provide:
1. A score from 0.0 to 1.0
2. A brief rationale (1-2 sentences)

Format your response as:
CRITERION_NAME: SCORE | RATIONALE
"""
        return prompt

    def _build_improvement_prompt(
        self, blueprint: Blueprint, evaluation: BlueprintEvaluation
    ) -> str:
        """Build prompt for improvement suggestions."""
        prompt = f"""
# Blueprint Improvement Analysis

## Blueprint
- **ID:** {blueprint.id}
- **Current Score:** {evaluation.weighted_total:.2f}

## Weaknesses Identified
"""
        for weakness in evaluation.weaknesses:
            prompt += f"- {weakness}\n"

        prompt += "\n## Low-Scoring Criteria\n"
        for score in evaluation.scores:
            if score.score < 0.6:
                prompt += (
                    f"- **{score.criterion}:** {score.score:.2f} - {score.rationale}\n"
                )

        prompt += """
## Task
Provide 3-5 specific, actionable improvement suggestions that would address the weaknesses and improve low-scoring criteria.

Format each suggestion as:
- [Suggestion]: [Rationale]
"""
        return prompt

    def _parse_scores(
        self, llm_response: str, criteria: List[EvaluationCriteria]
    ) -> List[BlueprintScore]:
        """Parse LLM response into structured scores."""
        scores = []
        lines = llm_response.strip().split("\n")

        for line in lines:
            if ":" not in line or "|" not in line:
                continue
            try:
                criterion_part, rest = line.split(":", 1)
                score_part, rationale = rest.split("|", 1)

                criterion_name = criterion_part.strip()
                score_value = float(score_part.strip())
                rationale_text = rationale.strip()

                if not any(c.name == criterion_name for c in criteria):
                    continue

                scores.append(
                    BlueprintScore(
                        criterion=criterion_name,
                        score=min(1.0, max(0.0, score_value)),
                        rationale=rationale_text,
                    )
                )
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse score line: {line} - {e}")
                continue

        for criterion in criteria:
            if not any(s.criterion == criterion.name for s in scores):
                scores.append(
                    BlueprintScore(
                        criterion=criterion.name,
                        score=0.5,
                        rationale="No evaluation provided",
                    )
                )

        return scores

    def _parse_suggestions(self, llm_response: str) -> List[str]:
        """Parse LLM response into list of suggestions."""
        suggestions = []
        lines = llm_response.strip().split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                suggestion = line.lstrip("-*").strip()
                if suggestion:
                    suggestions.append(suggestion)

        return suggestions


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-008",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "adapter",
        "adapter-pattern",
        "async",
        "intelligence",
        "llm",
        "logging",
        "messaging",
        "orchestration",
        "rest-api",
    ],
    "keywords": [
        "adapter",
        "blueprint",
        "generate",
        "improvements",
        "orchestrator",
        "score",
    ],
    "business_value": "Implements BlueprintAdapter for adapter functionality",
    "last_modified": "2026-01-07T13:35:57Z",
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
