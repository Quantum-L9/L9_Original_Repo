"""
L9 Agents - QA Agent
====================

Quality assurance agent.

Responsibilities:
- Test planning
- Test execution review
- Quality assessment
- Bug detection
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "QA Agent",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:57Z",
    "layer": "intelligence",
    "domain": "agent_execution",
    "module_name": "qa_agent",
    "type": "agent",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["agents.__init__"],
    },
}
# ============================================================================

import json
from typing import Any

import structlog

from agents.base_agent import AgentConfig, AgentResponse, AgentRole, BaseAgent

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are the QA Agent for L9, responsible for quality assurance.

Your responsibilities:
1. Plan comprehensive test strategies
2. Review test coverage and quality
3. Identify potential bugs and issues
4. Assess overall code quality
5. Verify requirements are met

Testing focus areas:
- Functionality: Does it work correctly?
- Edge cases: Does it handle unusual inputs?
- Error handling: Does it fail gracefully?
- Performance: Are there bottlenecks?
- Security: Are there vulnerabilities?
- Integration: Does it work with other components?

Be thorough and systematic. Quality is paramount.
"""


class QAAgent(BaseAgent):
    """
    Quality assurance agent.
    """

    agent_role = AgentRole.QA
    agent_name = "qa_agent"

    def __init__(
        self,
        agent_id: str | None = None,
        config: AgentConfig | None = None,
    ):
        """Initialize QA Agent."""
        super().__init__(agent_id, config)

    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return self._config.system_prompt_override or SYSTEM_PROMPT

    async def run(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """
        Execute QA task.

        Args:
            task: Task with 'code' and 'requirements'
            context: Optional context

        Returns:
            AgentResponse with QA results
        """
        code = task.get("code", {})
        requirements = task.get("requirements", [])
        tests = task.get("tests", {})

        prompt = f"""Perform quality assurance review:

Code:
{json.dumps(code, indent=2)}

Requirements:
{json.dumps(requirements, indent=2)}

Existing Tests:
{json.dumps(tests, indent=2) if tests else "None provided"}

Provide comprehensive QA assessment:
{{
    "overall_quality_score": 0.0 to 1.0,
    "verdict": "pass|conditional_pass|fail",
    "requirements_verification": {{
        "met": ["..."],
        "partially_met": ["..."],
        "not_met": ["..."]
    }},
    "test_coverage_assessment": {{
        "score": 0.0 to 1.0,
        "covered_areas": ["..."],
        "gaps": ["..."],
        "recommended_tests": [
            {{"type": "unit|integration|e2e", "target": "...", "description": "..."}}
        ]
    }},
    "bug_detection": [
        {{
            "severity": "critical|major|minor",
            "location": "...",
            "description": "...",
            "reproduction_steps": ["..."],
            "fix_suggestion": "..."
        }}
    ],
    "code_quality_issues": [
        {{"type": "...", "location": "...", "description": "...", "suggestion": "..."}}
    ],
    "security_concerns": ["..."],
    "performance_concerns": ["..."],
    "release_readiness": {{
        "ready": true/false,
        "blockers": ["..."],
        "recommendations": ["..."]
    }},
    "summary": "..."
}}
"""

        if context:
            prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        messages = [self.format_user_message(prompt)]
        response = await self.call_llm(messages, json_mode=True)

        self.add_message(messages[0])
        if response.success:
            self.add_message(self.format_assistant_message(response.content))

        return response

    async def create_test_plan(
        self,
        feature: str,
        code: str,
    ) -> dict[str, Any]:
        """
        Create a test plan for a feature.

        Args:
            feature: Feature description
            code: Implementation code

        Returns:
            Test plan
        """
        prompt = f"""Create a comprehensive test plan:

Feature:
{feature}

Implementation:
```
{code}
```

Provide:
{{
    "test_plan_name": "...",
    "scope": "...",
    "test_levels": {{
        "unit_tests": [
            {{"target": "...", "scenarios": ["..."], "priority": "high|medium|low"}}
        ],
        "integration_tests": [
            {{"components": ["..."], "scenarios": ["..."], "priority": "..."}}
        ],
        "e2e_tests": [
            {{"flow": "...", "steps": ["..."], "priority": "..."}}
        ]
    }},
    "edge_cases": ["..."],
    "error_scenarios": ["..."],
    "performance_tests": ["..."],
    "security_tests": ["..."],
    "test_data_requirements": ["..."],
    "estimated_effort": "...",
    "priorities": ["ordered list of what to test first"]
}}
"""

        return await self.call_llm_json(prompt)

    async def review_test_results(
        self,
        test_output: str,
        expected_behavior: str,
    ) -> dict[str, Any]:
        """
        Review test execution results.

        Args:
            test_output: Test execution output
            expected_behavior: What was expected

        Returns:
            Analysis of results
        """
        prompt = f"""Analyze these test results:

Test Output:
```
{test_output}
```

Expected Behavior:
{expected_behavior}

Provide:
{{
    "analysis": {{
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0
    }},
    "failures": [
        {{
            "test_name": "...",
            "expected": "...",
            "actual": "...",
            "likely_cause": "...",
            "fix_suggestion": "..."
        }}
    ],
    "coverage_gaps": ["..."],
    "false_positives": ["tests that might be wrong"],
    "false_negatives": ["bugs tests might have missed"],
    "recommendations": ["..."],
    "overall_assessment": "..."
}}
"""

        return await self.call_llm_json(prompt)

    async def regression_analysis(
        self,
        old_code: str,
        new_code: str,
        change_description: str,
    ) -> dict[str, Any]:
        """
        Analyze potential regressions from changes.

        Args:
            old_code: Previous code
            new_code: Updated code
            change_description: What changed

        Returns:
            Regression analysis
        """
        prompt = f"""Analyze potential regressions from this change:

Previous Code:
```
{old_code}
```

New Code:
```
{new_code}
```

Change Description:
{change_description}

Provide:
{{
    "regression_risk": "high|medium|low",
    "affected_areas": ["..."],
    "potential_regressions": [
        {{
            "area": "...",
            "risk": "...",
            "description": "...",
            "test_to_verify": "..."
        }}
    ],
    "backward_compatibility": {{
        "maintained": true/false,
        "breaking_changes": ["..."]
    }},
    "recommended_tests": ["..."],
    "safe_to_deploy": true/false,
    "deployment_notes": ["..."]
}}
"""

        return await self.call_llm_json(prompt)

    async def assess_production_readiness(
        self,
        code: dict[str, str],
        tests: dict[str, str],
        documentation: str | None = None,
    ) -> dict[str, Any]:
        """
        Assess if code is production-ready.

        Args:
            code: Code files
            tests: Test files
            documentation: Optional documentation

        Returns:
            Readiness assessment
        """
        prompt = f"""Assess production readiness:

Code:
{json.dumps(code, indent=2)}

Tests:
{json.dumps(tests, indent=2)}

Documentation:
{documentation or "Not provided"}

Provide:
{{
    "production_ready": true/false,
    "readiness_score": 0.0 to 1.0,
    "checklist": {{
        "code_quality": {{"pass": true/false, "notes": "..."}},
        "test_coverage": {{"pass": true/false, "notes": "..."}},
        "error_handling": {{"pass": true/false, "notes": "..."}},
        "logging": {{"pass": true/false, "notes": "..."}},
        "documentation": {{"pass": true/false, "notes": "..."}},
        "security": {{"pass": true/false, "notes": "..."}},
        "performance": {{"pass": true/false, "notes": "..."}}
    }},
    "blockers": ["must fix before production"],
    "recommendations": ["should fix but not blocking"],
    "deployment_checklist": ["things to verify during deployment"],
    "monitoring_recommendations": ["what to monitor post-deployment"]
}}
"""

        return await self.call_llm_json(prompt)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-004",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["agents.base_agent"],
    "tags": [
        "agent",
        "agent-execution",
        "async",
        "code-quality",
        "intelligence",
        "logging",
        "messaging",
        "monitoring",
        "serialization",
    ],
    "keywords": [
        "agent",
        "analysis",
        "assess",
        "create",
        "detection",
        "plan",
        "production",
        "prompt",
    ],
    "business_value": "Implements QAAgent for qa agent functionality",
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
