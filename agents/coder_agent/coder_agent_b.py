"""
L9 Agents - Coder Agent B
=========================

Secondary coder agent for parallel work and review.

Responsibilities:
- Implement parallel tasks
- Provide code review
- Suggest improvements
- Handle auxiliary implementations
"""

from __future__ import annotations

import json
import structlog
from typing import Any, Optional

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse, AgentRole

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are Coder B, the secondary implementation engineer for L9.

Your responsibilities:
1. Implement parallel tasks to speed up development
2. Review code from Coder A
3. Suggest improvements and optimizations
4. Handle auxiliary implementations (tests, utilities, configs)

When reviewing:
- Check for correctness
- Look for potential bugs
- Suggest performance improvements
- Verify error handling
- Check code style consistency

When implementing:
- Follow the same standards as the primary coder
- Ensure consistency with existing code
- Focus on quality over speed
"""


class CoderAgentB(BaseAgent):
    """
    Secondary coder agent for parallel work and review.
    """

    agent_role = AgentRole.CODER_SECONDARY
    agent_name = "coder_b"

    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[AgentConfig] = None,
    ):
        """Initialize Coder Agent B."""
        super().__init__(agent_id, config)

    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return self._config.system_prompt_override or SYSTEM_PROMPT

    async def run(
        self,
        task: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        Execute task (implementation or review).

        Args:
            task: Task with 'type' (implement/review) and details
            context: Optional context

        Returns:
            AgentResponse with result
        """
        task_type = task.get("type", "implement")

        if task_type == "review":
            return await self._review_code(task, context)
        else:
            return await self._implement(task, context)

    async def _implement(
        self,
        task: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """Implement code."""
        specification = task.get("specification", "")
        language = task.get("language", "python")

        prompt = f"""Implement the following (as secondary/parallel implementation):

Specification:
{specification}

Language: {language}

Ensure consistency with existing codebase patterns.

Provide:
{{
    "files": [
        {{
            "path": "...",
            "content": "...",
            "purpose": "..."
        }}
    ],
    "dependencies": ["..."],
    "notes": ["..."]
}}
"""

        if context:
            prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        messages = [self.format_user_message(prompt)]
        return await self.call_llm(messages, json_mode=True)

    async def _review_code(
        self,
        task: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """Review code from another coder."""
        code = task.get("code", {})
        requirements = task.get("requirements", "")

        prompt = f"""Review this code implementation:

Code:
{json.dumps(code, indent=2)}

Requirements:
{requirements}

Provide thorough review:
{{
    "score": 0.0 to 1.0,
    "correctness": {{
        "score": 0.0 to 1.0,
        "issues": ["..."]
    }},
    "code_quality": {{
        "score": 0.0 to 1.0,
        "issues": [
            {{"severity": "critical|major|minor", "location": "...", "issue": "...", "suggestion": "..."}}
        ]
    }},
    "performance": {{
        "score": 0.0 to 1.0,
        "concerns": ["..."],
        "optimizations": ["..."]
    }},
    "improvements": [
        {{"current": "...", "suggested": "...", "reason": "..."}}
    ],
    "consensus": true/false,
    "summary": "..."
}}
"""

        if context:
            prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        messages = [self.format_user_message(prompt)]
        return await self.call_llm(messages, json_mode=True)

    async def write_tests(
        self,
        code: str,
        framework: str = "pytest",
    ) -> dict[str, Any]:
        """
        Write tests for code.

        Args:
            code: Code to test
            framework: Test framework

        Returns:
            Test code
        """
        prompt = f"""Write comprehensive tests for this code:

Code:
```
{code}
```

Test Framework: {framework}

Provide:
{{
    "test_file": "complete test file content",
    "test_cases": [
        {{"name": "...", "tests": "...", "coverage": "..."}}
    ],
    "fixtures_needed": ["..."],
    "mocks_needed": ["..."],
    "edge_cases_covered": ["..."],
    "coverage_estimate": "percentage"
}}
"""

        return await self.call_llm_json(prompt)

    async def write_documentation(
        self,
        code: str,
        doc_type: str = "api",
    ) -> dict[str, Any]:
        """
        Write documentation for code.

        Args:
            code: Code to document
            doc_type: Type of documentation

        Returns:
            Documentation
        """
        prompt = f"""Write {doc_type} documentation for this code:

Code:
```
{code}
```

Provide:
{{
    "documentation": "full documentation content",
    "sections": [
        {{"title": "...", "content": "..."}}
    ],
    "examples": ["usage examples"],
    "api_reference": "if applicable"
}}
"""

        return await self.call_llm_json(prompt)

    async def implement_utilities(
        self,
        main_code: str,
        utilities_needed: list[str],
    ) -> dict[str, Any]:
        """
        Implement utility functions for main code.

        Args:
            main_code: Main implementation
            utilities_needed: List of utilities to implement

        Returns:
            Utility implementations
        """
        prompt = f"""Implement these utilities to support the main code:

Main Code:
```
{main_code}
```

Utilities Needed:
{json.dumps(utilities_needed, indent=2)}

Provide:
{{
    "utilities": [
        {{
            "name": "...",
            "code": "...",
            "purpose": "...",
            "usage": "..."
        }}
    ],
    "helper_file": "combined utilities file if needed",
    "notes": ["..."]
}}
"""

        return await self.call_llm_json(prompt)

    async def create_config(
        self,
        application: str,
        environment: str = "development",
    ) -> dict[str, Any]:
        """
        Create configuration files.

        Args:
            application: Application description
            environment: Target environment

        Returns:
            Configuration files
        """
        prompt = f"""Create configuration for this application:

Application: {application}
Environment: {environment}

Provide:
{{
    "config_files": [
        {{
            "path": "...",
            "format": "yaml|json|env|toml",
            "content": "...",
            "purpose": "..."
        }}
    ],
    "environment_variables": [
        {{"name": "...", "description": "...", "default": "...", "required": true/false}}
    ],
    "secrets_needed": ["..."],
    "notes": ["..."]
}}
"""

        return await self.call_llm_json(prompt)
