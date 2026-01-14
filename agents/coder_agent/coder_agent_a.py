"""
L9 Agents - Coder Agent A
=========================

Primary coder agent.

Responsibilities:
- Implement code from specifications
- Write clean, production-ready code
- Follow best practices
- Handle complex implementations
"""

from __future__ import annotations

import json
import structlog
from typing import Any, Optional

from agents.base_agent import BaseAgent, AgentConfig, AgentResponse, AgentRole

logger = structlog.get_logger(__name__)


SYSTEM_PROMPT = """You are Coder A, the primary implementation engineer for L9.

Your responsibilities:
1. Write clean, production-ready code
2. Implement features according to specifications
3. Follow language and framework best practices
4. Include proper error handling and logging
5. Write testable, maintainable code

Coding standards:
- Use type hints (Python) or type annotations
- Include docstrings for public functions
- Handle errors gracefully
- Log appropriately
- Follow naming conventions
- Keep functions focused and small

When implementing:
- Start with the interface/contract
- Implement core logic first
- Add error handling
- Consider edge cases
- Document assumptions
"""


class CoderAgentA(BaseAgent):
    """
    Primary coder agent for implementation.
    """

    agent_role = AgentRole.CODER_PRIMARY
    agent_name = "coder_a"

    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[AgentConfig] = None,
    ):
        """Initialize Coder Agent A."""
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
        Execute implementation task.

        Args:
            task: Task with 'specification' and 'language'
            context: Optional context

        Returns:
            AgentResponse with implementation
        """
        specification = task.get("specification", "")
        language = task.get("language", "python")
        framework = task.get("framework")
        existing_code = task.get("existing_code", {})

        prompt = f"""Implement the following specification:

Specification:
{specification}

Language: {language}
Framework: {framework or "None specified"}

Existing Code Context:
{json.dumps(existing_code, indent=2) if existing_code else "New implementation"}

Provide implementation as JSON:
{{
    "files": [
        {{
            "path": "path/to/file.py",
            "content": "full file content with proper formatting",
            "language": "{language}",
            "purpose": "description of file purpose"
        }}
    ],
    "dependencies": ["package==version"],
    "environment_variables": ["VAR_NAME"],
    "usage_example": "code showing how to use the implementation",
    "notes": ["important implementation notes"],
    "reasoning": "explanation of implementation decisions"
}}
"""

        if context:
            prompt += f"\n\nAdditional context:\n{json.dumps(context, indent=2)}"

        messages = [self.format_user_message(prompt)]
        response = await self.call_llm(messages, json_mode=True)

        self.add_message(messages[0])
        if response.success:
            self.add_message(self.format_assistant_message(response.content))

        return response

    async def implement_function(
        self,
        name: str,
        signature: str,
        description: str,
        examples: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Implement a specific function.

        Args:
            name: Function name
            signature: Function signature
            description: What it should do
            examples: Usage examples

        Returns:
            Implementation
        """
        prompt = f"""Implement this function:

Name: {name}
Signature: {signature}
Description: {description}

Examples:
{json.dumps(examples, indent=2) if examples else "None provided"}

Provide:
{{
    "implementation": "full function code",
    "tests": ["test case code"],
    "edge_cases_handled": ["..."],
    "complexity": "O(...)",
    "notes": ["..."]
}}
"""

        return await self.call_llm_json(prompt)

    async def implement_class(
        self,
        name: str,
        purpose: str,
        interface: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Implement a class.

        Args:
            name: Class name
            purpose: Class purpose
            interface: Required interface

        Returns:
            Class implementation
        """
        prompt = f"""Implement this class:

Name: {name}
Purpose: {purpose}
Interface:
{json.dumps(interface, indent=2)}

Provide:
{{
    "implementation": "full class code",
    "private_methods": ["helper methods if needed"],
    "tests": ["test case code"],
    "usage_example": "code showing class usage",
    "notes": ["implementation notes"]
}}
"""

        return await self.call_llm_json(prompt)

    async def refactor(
        self,
        code: str,
        goals: list[str],
    ) -> dict[str, Any]:
        """
        Refactor existing code.

        Args:
            code: Code to refactor
            goals: Refactoring goals

        Returns:
            Refactored code
        """
        prompt = f"""Refactor this code according to the goals:

Original Code:
```
{code}
```

Refactoring Goals:
{json.dumps(goals, indent=2)}

Provide:
{{
    "refactored_code": "full refactored code",
    "changes_made": ["description of each change"],
    "improvements": ["what was improved"],
    "potential_issues": ["any concerns with changes"],
    "before_after_comparison": "summary of differences"
}}
"""

        return await self.call_llm_json(prompt)

    async def fix_bug(
        self,
        code: str,
        bug_description: str,
        error_message: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Fix a bug in code.

        Args:
            code: Buggy code
            bug_description: What's wrong
            error_message: Optional error

        Returns:
            Fixed code
        """
        prompt = f"""Fix this bug:

Code:
```
{code}
```

Bug Description: {bug_description}
Error Message: {error_message or "Not provided"}

Provide:
{{
    "fixed_code": "complete fixed code",
    "root_cause": "what caused the bug",
    "fix_explanation": "how the fix works",
    "test_to_verify": "code to test the fix",
    "prevention_suggestion": "how to prevent similar bugs"
}}
"""

        return await self.call_llm_json(prompt)

    async def add_feature(
        self,
        existing_code: str,
        feature_description: str,
    ) -> dict[str, Any]:
        """
        Add a feature to existing code.

        Args:
            existing_code: Current code
            feature_description: Feature to add

        Returns:
            Updated code
        """
        prompt = f"""Add this feature to the existing code:

Existing Code:
```
{existing_code}
```

Feature to Add:
{feature_description}

Provide:
{{
    "updated_code": "complete updated code",
    "new_functions": ["list of new functions/methods added"],
    "modified_functions": ["list of modified functions/methods"],
    "integration_points": ["where new code connects to existing"],
    "usage_example": "how to use the new feature",
    "notes": ["important considerations"]
}}
"""

        return await self.call_llm_json(prompt)
