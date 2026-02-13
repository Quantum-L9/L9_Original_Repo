"""
L9 API - Commands Router
========================

POST /commands/execute endpoint for Igor command interface.

Parses structured commands or extracts intent from NLP,
confirms high-risk operations, and executes via CommandExecutor.

Version: 1.0.0 (GMP-11)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Commands Router",
    "module_version": "1.0.0 (GMP-11)",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "commands",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [
            "POST /execute",
            "POST /parse",
            "POST /intent",
            "GET /help",
            "POST /governance/feedback",
        ],
        "datasources": [],
        "memory_layers": ["working_memory"],
        "imported_by": ["api.server"],
    },
}
# ============================================================================

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import verify_api_key
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/commands", tags=["commands"])

# AUTO-REGISTRATION (Phase 2 Auto-Wiring)
from api.routes.registry import router_registry

router_registry.register(
    router=router,
    prefix="",  # Router already has prefix="/commands"
    tags=["commands"],
    module_id="commands",
    display_name="Igor Commands",
)


# =============================================================================
# Request/Response Models
# =============================================================================


class CommandExecuteRequest(BaseModel):
    """Request to execute an Igor command."""

    command_text: str = Field(..., description="Command text (structured or NLP)")
    user_id: str = Field(
        default="Igor", description="User ID (must be Igor for approvals)"
    )
    context: dict[str, Any] = Field(
        default_factory=dict, description="Optional execution context"
    )


class CommandExecuteResponse(BaseModel):
    """Response from command execution."""

    success: bool = Field(..., description="Whether command executed successfully")
    command_id: str = Field(..., description="Command identifier")
    task_id: str | None = Field(None, description="Created task ID if applicable")
    message: str = Field(..., description="Result message")
    data: dict[str, Any] = Field(default_factory=dict, description="Result data")
    requires_confirmation: bool = Field(
        default=False, description="Whether command requires confirmation"
    )


class IntentExtractResponse(BaseModel):
    """Response from intent extraction."""

    intent_type: str = Field(..., description="Extracted intent type")
    confidence: float = Field(..., description="Confidence score")
    entities: dict[str, Any] = Field(
        default_factory=dict, description="Extracted entities"
    )
    ambiguities: list[str] = Field(
        default_factory=list, description="Ambiguous elements"
    )
    is_ambiguous: bool = Field(..., description="Whether intent is ambiguous")
    suggested_command: dict[str, Any] | None = Field(
        None, description="Suggested structured command"
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/execute", response_model=CommandExecuteResponse)
@must_stay_async("callers use await")
async def execute_command(
    request: CommandExecuteRequest,
    req: Request,
    _: bool = Depends(verify_api_key),
):
    """
    Execute an Igor command.

    Parses the command text, extracts intent if NLP, confirms high-risk
    operations, and executes via CommandExecutor.

    Requires Igor authentication for approval and rollback commands.
    """
    from core.commands.executor import CommandExecutor
    from core.commands.intent_extractor import confirm_intent, extract_intent
    from core.commands.parser import Command, NLPPrompt, parse_command
    from core.compliance.audit_log import AuditLogger

    logger.info(
        "Execute command request",
        command_text=request.command_text[:100],
        user_id=request.user_id,
    )

    # Get services from app state
    agent_executor = getattr(req.app.state, "agent_executor", None)
    substrate_service = getattr(req.app.state, "substrate_service", None)

    # Initialize approval manager if substrate available
    approval_manager = None
    if substrate_service is not None:
        try:
            from core.governance.approvals import ApprovalManager

            approval_manager = ApprovalManager(substrate_service)
        except ImportError:
            logger.warning("ApprovalManager not available")

    # Initialize audit logger
    audit_logger = AuditLogger(substrate_service)

    # Parse command
    parsed = parse_command(request.command_text)

    if isinstance(parsed, Command):
        # Structured command - execute directly
        logger.debug("Parsed as structured command", command_type=parsed.type.value)

        # Check if confirmation required
        if parsed.requires_confirmation:
            # For now, return confirmation required response
            # In a full implementation, this would trigger confirmation flow
            return CommandExecuteResponse(
                success=False,
                command_id=str(parsed.id),
                message=f"High-risk command requires confirmation: {parsed.type.value}",
                requires_confirmation=True,
                data={
                    "command_type": parsed.type.value,
                    "risk_level": parsed.risk_level.value,
                    "raw_text": parsed.raw_text,
                },
            )

        # Execute command
        executor = CommandExecutor(
            agent_executor=agent_executor,
            approval_manager=approval_manager,
            substrate_service=substrate_service,
            audit_logger=audit_logger,
        )

        result = await executor.execute_command(
            command=parsed,
            user_id=request.user_id,
            context=request.context,
        )

        return CommandExecuteResponse(
            success=result.success,
            command_id=str(result.command_id),
            task_id=str(result.task_id) if result.task_id else None,
            message=result.message,
            data=result.data,
            requires_confirmation=False,
        )

    if isinstance(parsed, NLPPrompt):
        # NLP prompt - extract intent first
        logger.debug("Parsed as NLP prompt, extracting intent")

        intent = await extract_intent(parsed)

        if intent.is_ambiguous:
            # Return ambiguous response for clarification
            return CommandExecuteResponse(
                success=False,
                command_id=str(intent.id),
                message=f"Ambiguous command (confidence: {intent.confidence:.2f}). Please clarify.",
                data={
                    "intent_type": intent.intent_type.value,
                    "confidence": intent.confidence,
                    "ambiguities": intent.ambiguities,
                    "entities": intent.entities,
                },
            )

        # If intent has suggested command, execute it
        if intent.suggested_command is not None:
            command = intent.suggested_command

            # Check if confirmation required
            if command.requires_confirmation:
                confirmation = await confirm_intent(
                    intent,
                    user_context={
                        "user_id": request.user_id,
                        "channel": request.context.get("channel"),
                    },
                )

                if not confirmation.confirmed:
                    return CommandExecuteResponse(
                        success=False,
                        command_id=str(command.id),
                        message=confirmation.reason or "Awaiting confirmation",
                        requires_confirmation=True,
                        data={
                            "command_type": command.type.value,
                            "risk_level": command.risk_level.value,
                            "intent_type": intent.intent_type.value,
                        },
                    )

            # Execute the suggested command
            executor = CommandExecutor(
                agent_executor=agent_executor,
                approval_manager=approval_manager,
                substrate_service=substrate_service,
                audit_logger=audit_logger,
            )

            result = await executor.execute_command(
                command=command,
                user_id=request.user_id,
                context=request.context,
            )

            return CommandExecuteResponse(
                success=result.success,
                command_id=str(result.command_id),
                task_id=str(result.task_id) if result.task_id else None,
                message=result.message,
                data=result.data,
                requires_confirmation=False,
            )

        # No suggested command - forward to L-CTO as query
        if agent_executor is not None:
            try:
                from core.agents.schemas import AgentTask, AgentType

                task = AgentTask(
                    agent_id="l-cto",
                    agent_type=AgentType.ASSISTANT,
                    source_id="igor-command",
                    thread_identifier=f"nlp-{intent.id}",
                    payload={
                        "message": parsed.raw_text,
                        "intent": intent.dict(),
                        "channel": request.context.get("channel", "command"),
                    },
                )

                result = await agent_executor.start_agent_task(task)

                return CommandExecuteResponse(
                    success=True,
                    command_id=str(intent.id),
                    task_id=str(task.id),
                    message="Command forwarded to L-CTO",
                    data={
                        "intent_type": intent.intent_type.value,
                        "confidence": intent.confidence,
                    },
                )

            except Exception as e:
                logger.error("Failed to forward to L-CTO", error=str(e))

        return CommandExecuteResponse(
            success=False,
            command_id=str(intent.id),
            message="Could not execute command: no suggested action and no agent executor",
            data={"intent_type": intent.intent_type.value},
        )

    # Should not happen
    raise HTTPException(status_code=500, detail="Unexpected parse result type")


@router.post("/parse")
@must_stay_async("FastAPI/ASGI route handler")
async def parse_command_endpoint(
    request: CommandExecuteRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Parse a command without executing.

    Useful for debugging and testing command parsing.
    """
    from core.commands.parser import Command, NLPPrompt, parse_command

    parsed = parse_command(request.command_text)

    if isinstance(parsed, Command):
        return {
            "type": "structured",
            "command": parsed.dict(),
        }
    if isinstance(parsed, NLPPrompt):
        return {
            "type": "nlp",
            "prompt": parsed.dict(),
        }
    raise HTTPException(status_code=500, detail="Unexpected parse result")


@router.post("/intent")
@must_stay_async("callers use await")
async def extract_intent_endpoint(
    request: CommandExecuteRequest,
    _: bool = Depends(verify_api_key),
) -> IntentExtractResponse:
    """
    Extract intent from NLP text without executing.

    Useful for debugging and testing intent extraction.
    """
    from core.commands.intent_extractor import extract_intent
    from core.commands.parser import NLPPrompt, parse_command

    parsed = parse_command(request.command_text)

    # If already structured, return as-is
    if not isinstance(parsed, NLPPrompt):
        return IntentExtractResponse(
            intent_type="structured_command",
            confidence=1.0,
            entities={},
            ambiguities=[],
            is_ambiguous=False,
            suggested_command=parsed.dict() if hasattr(parsed, "dict") else None,
        )

    intent = await extract_intent(parsed)

    return IntentExtractResponse(
        intent_type=intent.intent_type.value,
        confidence=intent.confidence,
        entities=intent.entities,
        ambiguities=intent.ambiguities,
        is_ambiguous=intent.is_ambiguous,
        suggested_command=(
            intent.suggested_command.dict() if intent.suggested_command else None
        ),
    )


@router.get("/help")
@must_stay_async("FastAPI/ASGI route handler")
async def get_help():
    """
    Get available commands and usage.
    """
    return {
        "commands": {
            "@L propose gmp: <description>": "Create a GMP task",
            "@L analyze <entity>": "Analyze an entity or state",
            "@L approve <task_id>": "Approve a pending task (Igor only)",
            "@L rollback <change_id>": "Rollback a change (Igor only, critical risk)",
            "@L status [task_id]": "Check status",
            "@L help": "Show help",
        },
        "nlp": "Any text starting with @L will be parsed for intent",
        "confirmation": "High-risk commands (propose_gmp, rollback) require explicit confirmation",
    }


# =============================================================================
# Governance Approval Feedback Endpoint (GMP-16: Closed-Loop Learning)
# =============================================================================


class ApprovalFeedbackRequest(BaseModel):
    """Request to record approval/rejection feedback."""

    task_id: str = Field(..., description="Task identifier")
    decision: str = Field(..., description="'approved' or 'rejected'")
    reason: str = Field(..., description="Reason for decision")
    approver: str = Field(default="Igor", description="Who made the decision")
    tool_name: str | None = Field(None, description="Tool involved")
    task_type: str | None = Field(None, description="Type of task")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )


class ApprovalFeedbackResponse(BaseModel):
    """Response from approval feedback."""

    success: bool = Field(..., description="Whether feedback was recorded")
    pattern_created: bool = Field(
        ..., description="Whether a governance pattern was created"
    )
    message: str = Field(..., description="Result message")


@router.post("/governance/feedback", response_model=ApprovalFeedbackResponse)
@must_stay_async("callers use await")
async def record_approval_feedback(
    request: ApprovalFeedbackRequest,
    req: Request,
    _: bool = Depends(verify_api_key),
) -> ApprovalFeedbackResponse:
    """
    Record approval/rejection feedback for closed-loop learning.

    This endpoint allows Igor to explicitly record approval decisions,
    which are then used to create governance patterns for adaptive prompting.

    Only Igor can submit feedback.
    """
    if request.approver != "Igor":
        raise HTTPException(
            status_code=403,
            detail="Only Igor can submit approval feedback",
        )

    try:
        # Get substrate service
        substrate_service = getattr(req.app.state, "substrate_service", None)
        if substrate_service is None:
            raise HTTPException(
                status_code=503,
                detail="Memory substrate not available",
            )

        from core.governance.approvals import ApprovalManager

        approval_manager = ApprovalManager(substrate_service)

        if request.decision == "approved":
            success = await approval_manager.approve_task(
                task_id=request.task_id,
                approved_by=request.approver,
                reason=request.reason,
                tool_name=request.tool_name,
                task_type=request.task_type,
                context=request.context,
            )
        elif request.decision == "rejected":
            success = await approval_manager.reject_task(
                task_id=request.task_id,
                rejected_by=request.approver,
                reason=request.reason,
                tool_name=request.tool_name,
                task_type=request.task_type,
                context=request.context,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision: {request.decision}. Must be 'approved' or 'rejected'",
            )

        return ApprovalFeedbackResponse(
            success=success,
            pattern_created=success,  # Pattern is created on approve/reject
            message=f"Feedback recorded: {request.decision} for task {request.task_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to record approval feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record feedback: {e!s}",
        ) from e


__all__ = ["router"]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "API-OPER-024",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "api.auth",
        "core.agents.schemas",
        "core.commands.executor",
        "core.commands.intent_extractor",
        "core.commands.parser",
    ],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "debugging",
        "endpoint",
        "logging",
        "messaging",
        "operations",
        "pydantic",
    ],
    "keywords": [
        "approval",
        "command",
        "commands",
        "endpoint",
        "execute",
        "extract",
        "feedback",
        "help",
    ],
    "business_value": "Provides commands components including CommandExecuteRequest, CommandExecuteResponse, IntentExtractResponse",
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
