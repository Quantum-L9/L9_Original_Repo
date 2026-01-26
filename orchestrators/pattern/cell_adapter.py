"""
L9 Pattern Orchestrator - Cell Adapter
======================================

Adapts collaborative cells to the AgentProtocol interface used by
PatternOrchestrator.

This enables the pattern orchestrator to use the existing collaborative
cells (ArchitectCell, CoderCell, ReviewerCell, etc.) for node execution.

Usage:
    from orchestrators.pattern import PatternOrchestrator
    from orchestrators.pattern.cell_adapter import CellAgentAdapter

    orchestrator = PatternOrchestrator(
        pattern_path="config/patterns/pipeline_v1.yaml",
        subsystem_config_path="config/subsystems/code_mutation.yaml",
        agent=CellAgentAdapter(),
    )
    result = await orchestrator.execute(user_prompts=["Build X"])

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Cell Adapter",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-16T00:41:22Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "orchestration",
    "module_name": "cell_adapter",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": [
            "orchestrators.pattern.__init__",
            "orchestrators.pattern.cell_adapter",
            "scripts.run_pattern",
            "tests.orchestrators.test_pattern_orchestrator",
        ],
    },
}
# ============================================================================

import json
from typing import Any, Optional, Type

import structlog

from collaborative_cells.base_cell import BaseCell, CellConfig

logger = structlog.get_logger(__name__)


# =============================================================================
# Cell Agent Adapter
# =============================================================================


class CellAgentAdapter:
    """
    Adapts collaborative cells to the AgentProtocol interface.

    Maps role names (e.g., "ArchitectAgent") to cell implementations
    (e.g., ArchitectCell) and translates between interfaces.

    The adapter handles:
    - Role to cell type mapping
    - Task/prompt formatting for cells
    - Result extraction from CellResult
    - Error handling and logging
    """

    # Default role to cell class mapping
    # Lazy imports to avoid circular dependencies
    ROLE_CELL_MAP: dict[str, str] = {
        "ArchitectAgent": "collaborative_cells.architect_cell.ArchitectCell",
        "CoderAgent": "collaborative_cells.coder_cell.CoderCell",
        "QAAgent": "collaborative_cells.reviewer_cell.ReviewerCell",
        "ReviewerAgent": "collaborative_cells.reviewer_cell.ReviewerCell",
        "ReflectionAgent": "collaborative_cells.reflection_cell.ReflectionCell",
        # Pipeline-specific roles
        "CTOAgent": "collaborative_cells.reflection_cell.ReflectionCell",  # L improvement loop
    }

    # Roles that require special handling (not cell-based)
    SPECIAL_ROLES: set[str] = {"HumanGate", "GitWorker"}

    def __init__(
        self,
        cell_config: Optional[CellConfig] = None,
        role_mapping: Optional[dict[str, str]] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
    ):
        """
        Initialize the cell adapter.

        Args:
            cell_config: Configuration for cells (consensus threshold, max rounds, etc.)
            role_mapping: Custom role to cell class mapping (overrides defaults)
            api_key: OpenAI API key (if not set, uses environment variable)
            model: Model to use for LLM calls
        """
        self._cell_config = cell_config or CellConfig(
            max_rounds=3,
            consensus_threshold=0.8,
            model=model,
            api_key=api_key,
        )

        # Merge custom mapping with defaults
        self._role_mapping = {**self.ROLE_CELL_MAP}
        if role_mapping:
            self._role_mapping.update(role_mapping)

        # Cache for instantiated cells
        self._cell_cache: dict[str, BaseCell] = {}

        logger.info(
            "CellAgentAdapter initialized",
            roles_available=list(self._role_mapping.keys()),
            model=model,
        )

    async def invoke(
        self,
        role: str,
        prompt: str,
        input_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Invoke an agent with the given role and prompt.

        This method adapts the cell's execute() interface to the
        AgentProtocol.invoke() interface expected by PatternOrchestrator.

        Args:
            role: Agent role (e.g., "ArchitectAgent", "CoderAgent")
            prompt: Prompt template with instructions
            input_data: Input data for the task
            context: Execution context (trace_id, subsystem, etc.)

        Returns:
            Agent output as dictionary

        Raises:
            ValueError: If role is not mapped to a cell
            RuntimeError: If cell execution fails
        """
        logger.debug(
            "Invoking cell agent",
            role=role,
            trace_id=context.get("trace_id"),
        )

        # Handle special roles that don't use cells
        if role in self.SPECIAL_ROLES:
            return await self._handle_special_role(role, prompt, input_data, context)

        # Get or create cell for role
        cell = self._get_cell_for_role(role)

        # Build task from prompt and input
        task = self._build_task(prompt, input_data, context)

        # Execute cell
        try:
            result = await cell.execute(task=task, context=context)

            logger.info(
                "Cell execution complete",
                role=role,
                success=result.success,
                consensus_reached=result.consensus_reached,
                final_score=result.final_score,
                total_rounds=result.total_rounds,
                duration_ms=result.duration_ms,
            )

            if not result.success:
                error_msg = (
                    "; ".join(result.errors) if result.errors else "Unknown error"
                )
                raise RuntimeError(f"Cell execution failed: {error_msg}")

            # Extract output, with fallback
            output = result.output or {}

            # Add execution metadata
            output["_cell_metadata"] = {
                "cell_id": str(result.cell_id),
                "cell_type": result.cell_type,
                "consensus_reached": result.consensus_reached,
                "final_score": result.final_score,
                "total_rounds": result.total_rounds,
            }

            return output

        except Exception as e:
            logger.error(
                "Cell invocation failed",
                role=role,
                error=str(e),
                trace_id=context.get("trace_id"),
            )
            raise

    async def _handle_special_role(
        self,
        role: str,
        prompt: str,
        input_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle special roles that don't use the cell consensus loop.

        Args:
            role: Special role name
            prompt: Prompt template
            input_data: Input data
            context: Execution context

        Returns:
            Role-specific output
        """
        if role == "HumanGate":
            # Human approval gate - return pending status for human review
            logger.info(
                "HumanGate invoked - awaiting human approval",
                trace_id=context.get("trace_id"),
            )
            return {
                "approved": False,
                "approver": "PENDING_HUMAN_REVIEW",
                "approval_timestamp": "",
                "status": "pending",
                "message": "Awaiting human approval. Review the improvement analysis and TODO plan.",
                "decision_points": input_data.get("decision_points", []),
                "_requires_human_action": True,
            }

        elif role == "GitWorker":
            # Git operations - prepare commands but don't execute
            logger.info(
                "GitWorker invoked - preparing git operations",
                trace_id=context.get("trace_id"),
            )
            impl_artifacts = input_data.get("implementation_artifacts", {})
            test_validation = input_data.get("test_validation", {})

            # Generate branch name and commit message
            subsystem = context.get("subsystem", "unknown")
            trace_id = context.get("trace_id", "unknown")[:8]

            return {
                "commit_sha": "PENDING_EXECUTION",
                "branch_name": f"feature/{subsystem}-{trace_id}",
                "pr_url": "PENDING_PR_CREATION",
                "pr_number": 0,
                "guardrails_passed": test_validation.get("validation_status") == "pass",
                "guardrail_results": [
                    {
                        "check": "test_coverage",
                        "passed": test_validation.get("coverage_pct", 0) >= 80,
                        "details": f"Coverage: {test_validation.get('coverage_pct', 0)}%",
                    },
                    {
                        "check": "tests_passing",
                        "passed": test_validation.get("tests_failed", 1) == 0,
                        "details": f"Passed: {test_validation.get('tests_passed', 0)}, Failed: {test_validation.get('tests_failed', 0)}",
                    },
                ],
                "cmts_tracking_id": f"CMTS-{trace_id}",
                "cmts_record": {
                    "start_timestamp": "",
                    "end_timestamp": "",
                    "files_changed": impl_artifacts.get("files_created", [])
                    + impl_artifacts.get("files_modified", []),
                    "status": "pending",
                    "error_message": None,
                },
                "mutation_notes": "Git operations prepared. Execute via git tool or manual review.",
                "_requires_git_execution": True,
            }

        else:
            raise ValueError(f"Unknown special role: {role}")

    def _get_cell_for_role(self, role: str) -> BaseCell:
        """
        Get or create a cell instance for the given role.

        Args:
            role: Agent role name

        Returns:
            Cell instance

        Raises:
            ValueError: If role is not mapped
        """
        # Check cache first
        if role in self._cell_cache:
            return self._cell_cache[role]

        # Get cell class path
        cell_path = self._role_mapping.get(role)
        if not cell_path:
            available = list(self._role_mapping.keys())
            raise ValueError(f"Unknown role: {role}. Available roles: {available}")

        # Import and instantiate cell
        cell_class = self._import_cell_class(cell_path)
        cell = cell_class(config=self._cell_config)

        # Cache for reuse
        self._cell_cache[role] = cell

        logger.debug(f"Created cell for role {role}: {cell_class.__name__}")

        return cell

    def _import_cell_class(self, class_path: str) -> Type[BaseCell]:
        """
        Dynamically import a cell class from its path.

        Args:
            class_path: Full path like "collaborative_cells.architect_cell.ArchitectCell"

        Returns:
            Cell class
        """
        parts = class_path.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid cell class path: {class_path}")

        module_path, class_name = parts

        try:
            import importlib

            module = importlib.import_module(module_path)
            cell_class = getattr(module, class_name)
            return cell_class
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Failed to import cell class {class_path}: {e}") from e

    def _build_task(
        self,
        prompt: str,
        input_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build a task dictionary for cell execution.

        Converts the prompt/input_data format used by PatternOrchestrator
        into the task format expected by collaborative cells.

        Args:
            prompt: Prompt template
            input_data: Input data
            context: Execution context

        Returns:
            Task dictionary for cell.execute()
        """
        # Extract key fields from input_data
        user_prompts = input_data.get("user_prompts", [])
        subsystem_metadata = input_data.get("subsystem_metadata", {})
        subsystem_goals = input_data.get("subsystem_goals", [])

        # Build task description
        if user_prompts:
            task_description = "\n".join(user_prompts)
        else:
            task_description = prompt

        # Build context string for cells
        context_str = json.dumps(
            {
                "subsystem": context.get("subsystem", "unknown"),
                "metadata": subsystem_metadata,
                "goals": subsystem_goals,
            },
            indent=2,
        )

        return {
            "task": task_description,
            "prompt": prompt,
            "context": context_str,
            "input_data": input_data,
            # Pass through any previous node outputs
            **{
                k: v
                for k, v in input_data.items()
                if k not in ("user_prompts", "subsystem_metadata", "subsystem_goals")
            },
        }

    def register_role(self, role: str, cell_class_path: str) -> None:
        """
        Register a custom role to cell mapping.

        Args:
            role: Role name (e.g., "CustomAgent")
            cell_class_path: Full class path (e.g., "mymodule.MyCell")
        """
        self._role_mapping[role] = cell_class_path
        # Clear cache to pick up new mapping
        self._cell_cache.pop(role, None)

        logger.info(f"Registered role mapping: {role} -> {cell_class_path}")

    def clear_cache(self) -> None:
        """Clear the cell instance cache."""
        self._cell_cache.clear()
        logger.debug("Cell cache cleared")


# =============================================================================
# Direct LLM Agent (Alternative - No Consensus Loop)
# =============================================================================


class DirectLLMAgent:
    """
    Direct LLM agent without consensus loop.

    Simpler alternative to CellAgentAdapter when you don't need
    the producer/critic consensus mechanism.

    Usage:
        agent = DirectLLMAgent(api_key="...", model="gpt-4o")
        result = await agent.invoke("ArchitectAgent", prompt, input_data, context)
    """

    # Role-specific system prompts
    ROLE_PROMPTS: dict[str, str] = {
        "ArchitectAgent": (
            "You are a system architect. Design comprehensive, scalable architectures. "
            "Always respond with valid JSON matching the expected schema."
        ),
        "CoderAgent": (
            "You are a senior software engineer. Write clean, production-ready code. "
            "Always respond with valid JSON matching the expected schema."
        ),
        "QAAgent": (
            "You are a QA engineer. Analyze code for bugs, edge cases, and test coverage. "
            "Always respond with valid JSON matching the expected schema."
        ),
        "ReviewerAgent": (
            "You are a code reviewer. Provide constructive feedback on code quality. "
            "Always respond with valid JSON matching the expected schema."
        ),
        "CTOAgent": (
            "You are L, the CTO of L9. Analyze plans across 10 improvement dimensions: "
            "risk profile, test coverage, memory governance, observability, guardrails, "
            "scalability, approval rigor, instantiation verification, mutation tracking, "
            "and documentation. Calculate yield percentage for each improvement. "
            "If total yield >= 10%, recommend more iterations. If < 10%, approve. "
            "Always respond with valid JSON matching the expected schema."
        ),
        "GitWorker": (
            "You are a git operations agent. Generate git commands and PR descriptions. "
            "Never execute commands directly - output the plan for execution. "
            "Always respond with valid JSON matching the expected schema."
        ),
        "HumanGate": (
            "You are an approval summarizer. Prepare a human-readable summary "
            "of the proposed changes for human review. Include key decision points, "
            "risks, and recommendations. Always respond with valid JSON."
        ),
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """
        Initialize direct LLM agent.

        Args:
            api_key: OpenAI API key (uses env var if not provided)
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

        logger.info("DirectLLMAgent initialized", model=model)

    async def invoke(
        self,
        role: str,
        prompt: str,
        input_data: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Invoke LLM directly without consensus loop.

        Args:
            role: Agent role
            prompt: User prompt
            input_data: Input data
            context: Execution context

        Returns:
            LLM response as dictionary
        """
        system_prompt = self.ROLE_PROMPTS.get(role, f"You are {role}.")

        # Build user message
        user_message = f"{prompt}\n\nInput Data:\n{json.dumps(input_data, indent=2)}"

        logger.debug(
            "Invoking LLM",
            role=role,
            model=self._model,
            trace_id=context.get("trace_id"),
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            logger.info(
                "LLM response received",
                role=role,
                tokens_used=response.usage.total_tokens if response.usage else 0,
            )

            return result

        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON", error=str(e))
            raise RuntimeError(f"LLM response was not valid JSON: {e}") from e
        except Exception as e:
            logger.error("LLM invocation failed", role=role, error=str(e))
            raise


# =============================================================================
# Factory Functions
# =============================================================================


def create_cell_adapter(
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
    max_rounds: int = 3,
    consensus_threshold: float = 0.8,
) -> CellAgentAdapter:
    """
    Factory function to create a CellAgentAdapter with common settings.

    Args:
        api_key: OpenAI API key
        model: Model to use
        max_rounds: Max consensus rounds per cell
        consensus_threshold: Score threshold for consensus

    Returns:
        Configured CellAgentAdapter
    """
    config = CellConfig(
        max_rounds=max_rounds,
        consensus_threshold=consensus_threshold,
        model=model,
        api_key=api_key,
    )
    return CellAgentAdapter(cell_config=config)


def create_direct_agent(
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
) -> DirectLLMAgent:
    """
    Factory function to create a DirectLLMAgent.

    Args:
        api_key: OpenAI API key
        model: Model to use

    Returns:
        Configured DirectLLMAgent
    """
    return DirectLLMAgent(api_key=api_key, model=model)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "ORC-INTE-025",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "adapter",
        "adapter-pattern",
        "api",
        "async",
        "caching",
        "code-quality",
        "debugging",
        "intelligence",
        "llm",
        "logging",
    ],
    "keywords": [
        "adapter",
        "agent",
        "cache",
        "cell",
        "cellagentadapter",
        "cells",
        "clear",
        "collaborative",
    ],
    "business_value": "This enables the pattern orchestrator to use the existing collaborative cells (ArchitectCell, CoderCell, ReviewerCell, etc.) for node execution. from orchestrators.pattern import PatternOrchestrator f",
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
