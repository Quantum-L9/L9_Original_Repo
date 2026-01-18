"""
L9 Collaborative Cells - Reviewer Cell
======================================

Collaborative cell for quality assurance and code review.

Uses 2 reviewer agents:
- Reviewer A: Primary QA analyst
- Reviewer B: Secondary checker
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Reviewer Cell",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "collaborative_reasoning",
    "module_name": "reviewer_cell",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": [
            "collaborative_cells.__init__",
            "orchestration.cell_orchestrator",
        ],
    },
}
# ============================================================================

import json
import structlog
from typing import Any, Optional

from openai import AsyncOpenAI

from collaborative_cells.base_cell import BaseCell, CellConfig
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


REVIEWER_A_PROMPT = """You are Reviewer A, the primary QA analyst.

Code to Review:
{code}

Requirements:
{requirements}

Context:
{context}

Perform a comprehensive review:
1. Functionality - Does it meet requirements?
2. Code Quality - Is it clean, readable, maintainable?
3. Security - Are there vulnerabilities?
4. Performance - Any obvious bottlenecks?
5. Testing - Is it testable? What tests are needed?

Return JSON:
{{
    "overall_score": 0.0 to 1.0,
    "functionality": {{
        "score": 0.0 to 1.0,
        "met_requirements": ["..."],
        "unmet_requirements": ["..."],
        "issues": ["..."]
    }},
    "code_quality": {{
        "score": 0.0 to 1.0,
        "strengths": ["..."],
        "issues": [
            {{"severity": "critical|major|minor", "description": "...", "location": "...", "fix": "..."}}
        ]
    }},
    "security": {{
        "score": 0.0 to 1.0,
        "vulnerabilities": [
            {{"type": "...", "description": "...", "severity": "critical|high|medium|low", "remediation": "..."}}
        ]
    }},
    "performance": {{
        "score": 0.0 to 1.0,
        "concerns": ["..."],
        "optimizations": ["..."]
    }},
    "testing": {{
        "testability_score": 0.0 to 1.0,
        "suggested_tests": [
            {{"type": "unit|integration|e2e", "description": "...", "target": "..."}}
        ]
    }},
    "verdict": "approve|request_changes|reject",
    "reasoning": "..."
}}
"""

REVIEWER_B_PROMPT = """You are Reviewer B, the secondary QA checker.

Primary Review:
{primary_review}

Original Code:
{code}

Requirements:
{requirements}

Validate the primary review:
1. Are the findings accurate?
2. Did they miss anything important?
3. Are the severity ratings appropriate?
4. Is the verdict correct?

Return JSON:
{{
    "score": 0.0 to 1.0,
    "agreement_level": 0.0 to 1.0,
    "missed_issues": [
        {{"type": "...", "description": "...", "severity": "..."}}
    ],
    "disagreements": [
        {{"issue": "...", "original_severity": "...", "suggested_severity": "...", "reason": "..."}}
    ],
    "additional_observations": ["..."],
    "final_verdict": "approve|request_changes|reject",
    "consensus": true/false,
    "reasoning": "..."
}}
"""


class ReviewerCell(BaseCell):
    """
    Collaborative cell for code review and QA.

    Coordinates two reviewer agents for thorough quality assessment.
    """

    cell_type = "reviewer"

    def __init__(self, config: Optional[CellConfig] = None):
        """Initialize the reviewer cell."""
        super().__init__(config)
        self._client: Optional[AsyncOpenAI] = None

    def _ensure_client(self) -> AsyncOpenAI:
        """Ensure OpenAI client is initialized."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._config.api_key)
        return self._client

    async def _run_producer(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
        previous_critique: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Run Reviewer A to produce primary review."""
        client = self._ensure_client()

        prompt = REVIEWER_A_PROMPT.format(
            code=json.dumps(task.get("code", {}), indent=2),
            requirements=json.dumps(task.get("requirements", []), indent=2),
            context=json.dumps(context, indent=2),
        )

        try:
            response = await client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Reviewer A, a senior QA engineer. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"Reviewer A failed: {e}")
            return {
                "overall_score": 0.0,
                "verdict": "reject",
                "error": str(e),
            }

    async def _run_critic(
        self,
        output: dict[str, Any],
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run Reviewer B to validate the review."""
        client = self._ensure_client()

        prompt = REVIEWER_B_PROMPT.format(
            primary_review=json.dumps(output, indent=2),
            code=json.dumps(task.get("code", {}), indent=2),
            requirements=json.dumps(task.get("requirements", []), indent=2),
        )

        try:
            response = await client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Reviewer B, validating a code review. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"Reviewer B failed: {e}")
            return {
                "score": 0.5,
                "consensus": False,
                "error": str(e),
            }

    def _apply_revisions(
        self,
        output: dict[str, Any],
        critique: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        """Apply secondary review findings."""
        revisions: list[str] = []

        # Add missed issues
        for issue in critique.get("missed_issues", []):
            output.setdefault("code_quality", {}).setdefault("issues", []).append(
                {
                    "severity": issue.get("severity", "minor"),
                    "description": issue.get("description", ""),
                    "source": "secondary_review",
                }
            )
            revisions.append(f"Added missed issue: {issue.get('description', '')[:50]}")

        # Update severity ratings based on disagreements
        for disagreement in critique.get("disagreements", []):
            issue_desc = disagreement.get("issue", "")
            suggested = disagreement.get("suggested_severity", "")

            for category in ["code_quality", "security"]:
                for issue in output.get(category, {}).get("issues", []):
                    if issue.get("description", "").startswith(issue_desc[:20]):
                        issue["severity"] = suggested
                        issue["severity_adjusted"] = True
                        revisions.append(f"Adjusted severity for: {issue_desc[:30]}")
                        break

        # Add additional observations
        output["additional_observations"] = critique.get("additional_observations", [])

        # Update verdict if reviewers disagree significantly
        if critique.get("final_verdict") != output.get("verdict"):
            output["verdict_disputed"] = True
            output["secondary_verdict"] = critique.get("final_verdict")
            revisions.append("Verdict disputed by secondary reviewer")

        return output, revisions

    @must_stay_async("callers use await")
    async def _validate_output(
        self,
        output: dict[str, Any],
        task: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate the review output."""
        errors: list[str] = []

        # Check for overall score
        if "overall_score" not in output:
            errors.append("Missing overall score")

        # Check for verdict
        if output.get("verdict") not in ["approve", "request_changes", "reject"]:
            errors.append("Invalid or missing verdict")

        # Validate score ranges
        for key in ["overall_score"]:
            score = output.get(key, 0)
            if not (0.0 <= score <= 1.0):
                errors.append(f"Invalid {key} range: {score}")

        return len(errors) == 0, errors

    # ==========================================================================
    # Review-Specific Methods
    # ==========================================================================

    async def review_code(
        self,
        code: dict[str, str],
        requirements: list[str],
        focus_areas: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Review code against requirements.

        Args:
            code: Dict of file_path -> code_content
            requirements: List of requirements
            focus_areas: Optional areas to focus on

        Returns:
            Review result
        """
        task = {
            "code": code,
            "requirements": requirements,
        }

        context = {
            "focus_areas": focus_areas or ["functionality", "security", "quality"],
        }

        result = await self.execute(task, context)
        return result.output or {}

    async def security_audit(
        self,
        code: dict[str, str],
    ) -> dict[str, Any]:
        """
        Perform security-focused review.

        Args:
            code: Dict of file_path -> code_content

        Returns:
            Security audit result
        """
        task = {
            "code": code,
            "requirements": ["Identify all security vulnerabilities"],
        }

        context = {
            "focus_areas": ["security"],
            "mode": "security_audit",
        }

        result = await self.execute(task, context)

        # Extract just security findings
        output = result.output or {}
        return {
            "security_score": output.get("security", {}).get("score", 0),
            "vulnerabilities": output.get("security", {}).get("vulnerabilities", []),
            "verdict": output.get("verdict"),
        }

    async def get_test_suggestions(
        self,
        code: dict[str, str],
    ) -> list[dict[str, Any]]:
        """
        Get suggested tests for code.

        Args:
            code: Dict of file_path -> code_content

        Returns:
            List of suggested tests
        """
        task = {
            "code": code,
            "requirements": ["Identify all testing needs"],
        }

        context = {
            "focus_areas": ["testing"],
            "mode": "test_planning",
        }

        result = await self.execute(task, context)
        output = result.output or {}

        return output.get("testing", {}).get("suggested_tests", [])


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COL-INTE-001",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "code-quality",
        "collaborative-reasoning",
        "intelligence",
        "llm",
        "logging",
        "messaging",
        "serialization",
        "service",
    ],
    "keywords": [
        "audit",
        "cell",
        "collaborative",
        "review",
        "reviewer",
        "security",
        "suggestions",
        "test",
    ],
    "business_value": "Implements ReviewerCell for reviewer cell functionality",
    "last_modified": "2026-01-17T23:47:56Z",
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
