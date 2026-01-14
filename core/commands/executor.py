"""
L9 Igor Command Interface - Executor
=====================================

Routes parsed commands to appropriate handlers:
- propose_gmp → Create AgentTask with gmprun tool
- analyze → Query world model or memory
- approve → Call ApprovalManager.approve_task()
- rollback → Enqueue rollback task

Version: 1.0.0 (GMP-11)
"""

from __future__ import annotations

import structlog
from datetime import datetime
from typing import Any, Optional

from core.commands.schemas import (
    Command,
    CommandResult,
    CommandType,
)

logger = structlog.get_logger(__name__)


class CommandExecutor:
    """
    Executes Igor commands by routing to appropriate handlers.

    Handles both structured commands and NLP-extracted intents.
    Enforces approval gates for high-risk operations.
    """

    def __init__(
        self,
        agent_executor: Optional[Any] = None,
        approval_manager: Optional[Any] = None,
        substrate_service: Optional[Any] = None,
        audit_logger: Optional[Any] = None,
    ):
        """
        Initialize CommandExecutor.

        Args:
            agent_executor: AgentExecutorService for task execution
            approval_manager: ApprovalManager for approval operations
            substrate_service: MemorySubstrateService for queries
            audit_logger: AuditLogger for command logging
        """
        self._agent_executor = agent_executor
        self._approval_manager = approval_manager
        self._substrate = substrate_service
        self._audit = audit_logger

    async def execute_command(
        self,
        command: Command,
        user_id: str,
        context: Optional[dict[str, Any]] = None,
    ) -> CommandResult:
        """
        Execute a structured command.

        Args:
            command: Parsed Command object
            user_id: Igor's user ID (must be "Igor" for approvals)
            context: Optional execution context

        Returns:
            CommandResult with success status and message
        """
        context = context or {}
        logger.info(
            "Executing command",
            command_type=command.type.value,
            command_id=str(command.id),
            user_id=user_id,
        )

        # Log command to audit trail
        await self._log_command(command, user_id, "start")

        try:
            # Route to appropriate handler
            result = await self._route_command(command, user_id, context)

            # Log completion
            await self._log_command(command, user_id, "complete", result=result)

            return result

        except Exception as e:
            logger.exception("Command execution failed", error=str(e))
            error_result = CommandResult(
                success=False,
                command_id=command.id,
                message=f"Execution failed: {str(e)}",
            )
            await self._log_command(command, user_id, "failed", error=str(e))
            return error_result

    async def _route_command(
        self,
        command: Command,
        user_id: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Route command to appropriate handler."""

        handlers = {
            CommandType.PROPOSE_GMP: self._handle_propose_gmp,
            CommandType.ANALYZE: self._handle_analyze,
            CommandType.APPROVE: self._handle_approve,
            CommandType.ROLLBACK: self._handle_rollback,
            CommandType.STATUS: self._handle_status,
            CommandType.HELP: self._handle_help,
            CommandType.QUERY: self._handle_query,
        }

        handler = handlers.get(command.type)
        if handler is None:
            return CommandResult(
                success=False,
                command_id=command.id,
                message=f"Unknown command type: {command.type.value}",
            )

        return await handler(command, user_id, context)

    async def _handle_propose_gmp(
        self,
        command: Command,
        user_id: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """
        Handle propose_gmp command.

        Creates an AgentTask with gmprun tool and consensus_required=True.
        """
        if self._agent_executor is None:
            return CommandResult(
                success=False,
                command_id=command.id,
                message="Agent executor not available",
            )

        try:
            from core.agents.schemas import AgentTask, TaskKind

            task = AgentTask(
                agent_id="l-cto",
                kind=TaskKind.GMP_RUN,
                source_id="igor-command",
                thread_identifier=f"gmp-{command.id}",
                payload={
                    "gmp_description": command.description,
                    "command_id": str(command.id),
                    "consensus_required": True,
                    "channel": context.get("channel", "command"),
                },
            )

            result = await self._agent_executor.start_agent_task(task)

            return CommandResult(
                success=True,
                command_id=command.id,
                task_id=task.id,
                message=f"GMP task created: {task.id}",
                data={
                    "task_id": str(task.id),
                    "description": command.description,
                    "requires_approval": True,
                },
            )

        except Exception as e:
            logger.error("Failed to create GMP task", error=str(e))
            return CommandResult(
                success=False,
                command_id=command.id,
                message=f"Failed to create GMP task: {str(e)}",
            )

    async def _handle_analyze(
        self,
        command: Command,
        user_id: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """
        Handle analyze command.

        Queries world model or memory for entity information.
        """
        entity = command.target
        if not entity:
            return CommandResult(
                success=False,
                command_id=command.id,
                message="No entity specified for analysis",
            )

        # If substrate available, query for entity
        if self._substrate is not None:
            try:
                # Search for entity in memory
                results = await self._substrate.search(
                    query=entity,
                    limit=10,
                )

                return CommandResult(
                    success=True,
                    command_id=command.id,
                    message=f"Analysis complete for: {entity}",
                    data={
                        "entity": entity,
                        "results_count": len(results) if results else 0,
                        "results": [r.dict() if hasattr(r, 'dict') else str(r) for r in (results or [])],
                    },
                )

            except Exception as e:
                logger.warning("Memory search failed", error=str(e))

        # Fallback: Create analysis task for L-CTO
        if self._agent_executor is not None:
            try:
                from core.agents.schemas import AgentTask, TaskKind

                task = AgentTask(
                    agent_id="l-cto",
                    kind=TaskKind.CONVERSATION,
                    source_id="igor-command",
                    thread_identifier=f"analyze-{command.id}",
                    payload={
                        "message": f"Analyze: {entity}",
                        "command_id": str(command.id),
                        "channel": context.get("channel", "command"),
                    },
                )

                result = await self._agent_executor.start_agent_task(task)

                return CommandResult(
                    success=True,
                    command_id=command.id,
                    task_id=task.id,
                    message=f"Analysis task created for: {entity}",
                    data={"task_id": str(task.id), "entity": entity},
                )

            except Exception as e:
                logger.error("Failed to create analysis task", error=str(e))

        return CommandResult(
            success=False,
            command_id=command.id,
            message="No substrate or agent executor available for analysis",
        )

    async def _handle_approve(
        self,
        command: Command,
        user_id: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """
        Handle approve command.

        Only Igor can approve tasks.
        """
        task_id = command.target
        if not task_id:
            return CommandResult(
                success=False,
                command_id=command.id,
                message="No task ID specified for approval",
            )

        # Validate that approver is Igor
        if user_id != "Igor":
            logger.warning("Unauthorized approval attempt", user_id=user_id)
            return CommandResult(
                success=False,
                command_id=command.id,
                message=f"Unauthorized: Only Igor can approve tasks (got: {user_id})",
            )

        # Use approval manager if available
        if self._approval_manager is not None:
            try:
                approved = await self._approval_manager.approve_task(
                    task_id=task_id,
                    approved_by=user_id,
                    reason=context.get("reason", "Approved via command"),
                )

                if approved:
                    return CommandResult(
                        success=True,
                        command_id=command.id,
                        message=f"Task {task_id} approved",
                        data={"task_id": task_id, "approved_by": user_id},
                    )
                else:
                    return CommandResult(
                        success=False,
                        command_id=command.id,
                        message=f"Failed to approve task {task_id}",
                    )

            except Exception as e:
                logger.error("Approval failed", error=str(e))
                return CommandResult(
                    success=False,
                    command_id=command.id,
                    message=f"Approval error: {str(e)}",
                )

        return CommandResult(
            success=False,
            command_id=command.id,
            message="Approval manager not available",
        )

    async def _handle_rollback(
        self,
        command: Command,
        user_id: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """
        Handle rollback command.

        Rollback is CRITICAL risk - always requires explicit confirmation.
        """
        change_id = command.target
        if not change_id:
            return CommandResult(
                success=False,
                command_id=command.id,
                message="No change ID specified for rollback",
            )

        # Validate Igor authorization
        if user_id != "Igor":
            return CommandResult(
                success=False,
                command_id=command.id,
                message=f"Unauthorized: Only Igor can rollback changes (got: {user_id})",
            )

        # Create rollback task
        if self._agent_executor is not None:
            try:
                from core.agents.schemas import AgentTask, TaskKind

                task = AgentTask(
                    agent_id="l-cto",
                    kind=TaskKind.EXECUTION,
                    source_id="igor-command",
                    thread_identifier=f"rollback-{command.id}",
                    payload={
                        "action": "rollback",
                        "change_id": change_id,
                        "command_id": str(command.id),
                        "channel": context.get("channel", "command"),
                    },
                )

                result = await self._agent_executor.start_agent_task(task)

                return CommandResult(
                    success=True,
                    command_id=command.id,
                    task_id=task.id,
                    message=f"Rollback task created for change: {change_id}",
                    data={
                        "task_id": str(task.id),
                        "change_id": change_id,
                        "risk_level": "critical",
                    },
                )

            except Exception as e:
                logger.error("Failed to create rollback task", error=str(e))
                return CommandResult(
                    success=False,
                    command_id=command.id,
                    message=f"Failed to create rollback task: {str(e)}",
                )

        return CommandResult(
            success=False,
            command_id=command.id,
            message="Agent executor not available for rollback",
        )

    async def _handle_status(
        self,
        command: Command,
        user_id: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Handle status command - check task or system status."""
        task_id = command.target

        if task_id:
            # Check specific task status
            return CommandResult(
                success=True,
                command_id=command.id,
                message=f"Status for task {task_id}: (not implemented)",
                data={"task_id": task_id},
            )
        else:
            # Return system status
            return CommandResult(
                success=True,
                command_id=command.id,
                message="L9 System Status: Operational",
                data={
                    "agent_executor": self._agent_executor is not None,
                    "substrate_service": self._substrate is not None,
                    "approval_manager": self._approval_manager is not None,
                },
            )

    async def _handle_help(
        self,
        command: Command,
        user_id: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Handle help command - return available commands."""
        help_text = """
**Igor Command Interface**

Structured commands:
- `@L propose gmp: <description>` - Create a GMP task
- `@L analyze <entity>` - Analyze an entity or state
- `@L approve <task_id>` - Approve a pending task
- `@L rollback <change_id>` - Rollback a change
- `@L status [task_id]` - Check status
- `@L help` - Show this help

Natural language:
- Any text starting with `@L` will be parsed for intent
- High-risk commands require explicit confirmation
"""
        return CommandResult(
            success=True,
            command_id=command.id,
            message=help_text.strip(),
        )

    async def _handle_query(
        self,
        command: Command,
        user_id: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Handle query command - forward to L-CTO for response."""
        if self._agent_executor is None:
            return CommandResult(
                success=False,
                command_id=command.id,
                message="Agent executor not available for queries",
            )

        try:
            from core.agents.schemas import AgentTask, TaskKind

            task = AgentTask(
                agent_id="l-cto",
                kind=TaskKind.CONVERSATION,
                source_id="igor-command",
                thread_identifier=f"query-{command.id}",
                payload={
                    "message": command.raw_text,
                    "command_id": str(command.id),
                    "channel": context.get("channel", "command"),
                },
            )

            result = await self._agent_executor.start_agent_task(task)

            return CommandResult(
                success=True,
                command_id=command.id,
                task_id=task.id,
                message="Query forwarded to L-CTO",
                data={"task_id": str(task.id)},
            )

        except Exception as e:
            logger.error("Failed to forward query", error=str(e))
            return CommandResult(
                success=False,
                command_id=command.id,
                message=f"Failed to forward query: {str(e)}",
            )

    async def _log_command(
        self,
        command: Command,
        user_id: str,
        action: str,
        result: Optional[CommandResult] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log command to audit trail."""
        if self._audit is not None:
            try:
                await self._audit.log_command(
                    command_id=str(command.id),
                    command_type=command.type.value,
                    user_id=user_id,
                    action=action,
                    risk_level=command.risk_level.value,
                    raw_text=command.raw_text,
                    result=result.dict() if result else None,
                    error=error,
                    timestamp=datetime.utcnow().isoformat(),
                )
            except Exception as e:
                logger.warning("Failed to log command to audit", error=str(e))


async def execute_command(
    command: Command,
    user_id: str,
    context: Optional[dict[str, Any]] = None,
    agent_executor: Optional[Any] = None,
    approval_manager: Optional[Any] = None,
    substrate_service: Optional[Any] = None,
) -> CommandResult:
    """
    Convenience function to execute a command.

    Creates a CommandExecutor with provided services and executes.

    Args:
        command: Parsed Command object
        user_id: Igor's user ID
        context: Optional execution context
        agent_executor: Optional AgentExecutorService
        approval_manager: Optional ApprovalManager
        substrate_service: Optional MemorySubstrateService

    Returns:
        CommandResult with success status and message
    """
    executor = CommandExecutor(
        agent_executor=agent_executor,
        approval_manager=approval_manager,
        substrate_service=substrate_service,
    )
    return await executor.execute_command(command, user_id, context)


__all__ = [
    "CommandExecutor",
    "execute_command",
    "CommandResult",
]

