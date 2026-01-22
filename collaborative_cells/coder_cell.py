"""
L9 Collaborative Cells - Coder Cell
===================================

Collaborative cell for code implementation.

Uses 2 coder agents:
- Coder A: Primary implementer
- Coder B: Reviewer and improver
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Coder Cell",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "collaborative_reasoning",
    "module_name": "coder_cell",
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
from typing import Any, Optional

import structlog
from openai import AsyncOpenAI

from collaborative_cells.base_cell import BaseCell, CellConfig
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


CODER_A_PROMPT = """You are Coder A, the primary implementer.

Task: {task}

Previous review (if any):
{critique}

Context:
{context}

Implement the code following these guidelines:
1. Write clean, production-ready code
2. Include type hints and docstrings
3. Handle errors appropriately
4. Follow best practices for the language/framework
5. Consider edge cases

Return JSON:
{{
    "files": [
        {{
            "path": "path/to/file.py",
            "content": "...",
            "language": "python",
            "purpose": "..."
        }}
    ],
    "dependencies": ["..."],
    "environment_variables": ["..."],
    "testing_notes": "...",
    "reasoning": "..."
}}
"""

CODER_B_PROMPT = """You are Coder B, the code reviewer.

Proposed Implementation:
{code}

Original Task:
{task}

Context:
{context}

Review the code critically:
1. Does it fulfill all requirements?
2. Are there bugs or edge cases not handled?
3. Is the code clean and maintainable?
4. Are there security concerns?
5. What improvements would you suggest?

Return JSON:
{{
    "score": 0.0 to 1.0,
    "issues": [
        {{
            "severity": "critical|major|minor",
            "file": "...",
            "line": 0,
            "description": "...",
            "suggestion": "..."
        }}
    ],
    "improvements": [
        {{
            "file": "...",
            "current": "...",
            "suggested": "...",
            "reason": "..."
        }}
    ],
    "security_concerns": ["..."],
    "missing_requirements": ["..."],
    "consensus": true/false,
    "reasoning": "..."
}}
"""


class CoderCell(BaseCell):
    """
    Collaborative cell for code implementation.

    Coordinates two coder agents to write robust, reviewed code.
    """

    cell_type = "coder"

    def __init__(self, config: Optional[CellConfig] = None):
        """Initialize the coder cell."""
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
        """Run Coder A to produce implementation."""
        client = self._ensure_client()

        prompt = CODER_A_PROMPT.format(
            task=json.dumps(task, indent=2),
            critique=(
                json.dumps(previous_critique, indent=2) if previous_critique else "None"
            ),
            context=json.dumps(context, indent=2),
        )

        try:
            response = await client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Coder A, a senior software engineer. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"Coder A failed: {e}")
            return {
                "files": [],
                "error": str(e),
            }

    async def _run_critic(
        self,
        output: dict[str, Any],
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run Coder B to review the implementation."""
        client = self._ensure_client()

        prompt = CODER_B_PROMPT.format(
            code=json.dumps(output, indent=2),
            task=json.dumps(task, indent=2),
            context=json.dumps(context, indent=2),
        )

        try:
            response = await client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Coder B, a meticulous code reviewer. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except Exception as e:
            logger.error(f"Coder B failed: {e}")
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
        """Apply review revisions to code."""
        revisions: list[str] = []

        # Apply improvements
        for improvement in critique.get("improvements", []):
            file_path = improvement.get("file", "")
            suggested = improvement.get("suggested", "")

            for file_obj in output.get("files", []):
                if file_obj.get("path") == file_path and suggested:
                    # Note: In production, would apply more sophisticated patching
                    file_obj.setdefault("review_notes", []).append(
                        {
                            "suggestion": suggested,
                            "reason": improvement.get("reason", ""),
                        }
                    )
                    revisions.append(f"Improvement noted for {file_path}")
                    break

        # Add security notes
        for concern in critique.get("security_concerns", []):
            output.setdefault("security_notes", []).append(concern)
            revisions.append(f"Added security concern: {concern[:50]}")

        # Track issues for reference
        critical_issues = [
            i for i in critique.get("issues", []) if i.get("severity") == "critical"
        ]
        if critical_issues:
            output["critical_issues"] = critical_issues
            revisions.append(f"Flagged {len(critical_issues)} critical issues")

        return output, revisions

    @must_stay_async("callers use await")
    async def _validate_output(
        self,
        output: dict[str, Any],
        task: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate the code implementation."""
        errors: list[str] = []

        # Check for files
        if not output.get("files"):
            errors.append("No files generated")
            return False, errors

        # Validate each file
        for idx, file_obj in enumerate(output.get("files", [])):
            if not file_obj.get("path"):
                errors.append(f"File {idx} missing path")
            if not file_obj.get("content"):
                errors.append(f"File {file_obj.get('path', idx)} has no content")

        # Check for critical issues
        if output.get("critical_issues"):
            errors.append(
                f"Has {len(output['critical_issues'])} unresolved critical issues"
            )

        return len(errors) == 0, errors

    # ==========================================================================
    # Coder-Specific Methods
    # ==========================================================================

    async def implement(
        self,
        specification: str,
        language: str = "python",
        framework: Optional[str] = None,
        existing_code: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Implement code from specification.

        Args:
            specification: What to implement
            language: Programming language
            framework: Optional framework
            existing_code: Existing code to extend

        Returns:
            Implementation result
        """
        task = {
            "specification": specification,
            "language": language,
            "framework": framework,
        }

        context = {
            "existing_code": existing_code or {},
            "mode": "extend" if existing_code else "new",
        }

        result = await self.execute(task, context)
        return result.output or {}

    async def refactor(
        self,
        code: str,
        file_path: str,
        goals: list[str],
    ) -> dict[str, Any]:
        """
        Refactor existing code.

        Args:
            code: Code to refactor
            file_path: File path
            goals: Refactoring goals

        Returns:
            Refactored code
        """
        task = {
            "action": "refactor",
            "goals": goals,
        }

        context = {
            "existing_code": {file_path: code},
            "mode": "refactor",
        }

        result = await self.execute(task, context)
        return result.output or {}

    async def fix_bug(
        self,
        code: str,
        file_path: str,
        bug_description: str,
        error_message: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Fix a bug in code.

        Args:
            code: Code with bug
            file_path: File path
            bug_description: Description of the bug
            error_message: Optional error message

        Returns:
            Fixed code
        """
        task = {
            "action": "fix_bug",
            "bug_description": bug_description,
            "error_message": error_message,
        }

        context = {
            "existing_code": {file_path: code},
            "mode": "bugfix",
        }

        result = await self.execute(task, context)
        return result.output or {}


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COL-INTE-005",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "async",
        "collaborative-reasoning",
        "intelligence",
        "llm",
        "logging",
        "messaging",
        "serialization",
        "service",
        "testing",
    ],
    "keywords": [
        "bug",
        "cell",
        "coder",
        "collaborative",
        "fix",
        "implement",
        "refactor",
    ],
    "business_value": "Implements CoderCell for coder cell functionality",
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
