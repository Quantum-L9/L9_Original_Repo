"""
L9 Runtime - WebSocket Orchestrator
=====================================

Manages WebSocket connections from L9 agents.

Responsibilities:
- Accept and validate agent handshakes
- Track connected agents with metadata
- Route incoming messages to the ws_bridge for task conversion
- Dispatch outbound events to specific agents

The module-level singleton `ws_orchestrator` is the canonical instance.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "WebSocket Orchestrator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-21T00:00:34Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "websocket_orchestrator",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "api.server",
            "core.singleton_registry",
            "orchestration.unified_controller",
            "runtime.__init__",
            "tests.runtime.test_websocket_orchestrator_basic",
        ],
    },
}
# ============================================================================

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import structlog

from core.decorators import must_stay_async

# Input segmenter for multi-part directive support (harvested from tokenizer)
from orchestration.input_segmenter import get_segmenter

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = structlog.get_logger(__name__)


# =============================================================================
# WebSocket Authentication (REQUIRED - Single Source of Truth)
# =============================================================================


@must_stay_async("callers use await")
async def verify_ws_token(websocket: WebSocket, token: str | None = None) -> bool:
    """
    Verify WebSocket authentication token.

    ENFORCED SECURITY GATE - All WebSocket connections MUST pass this check.

    Contract:
    - Requires L9_EXECUTOR_API_KEY to be set (fail-fast if missing)
    - Token can come from query param OR handshake message
    - Returns False on ANY validation failure (no exceptions thrown)

    Token sources (priority order):
    1. Explicit `token` parameter (passed from handshake or explicit parameter)
    2. Query parameter: ws://host/endpoint?token=...

    Args:
        websocket: Active WebSocket connection (not yet accepted)
        token: Optional token from handshake or explicit parameter

    Returns:
        True if token is valid, False otherwise

    Security:
    - NEVER accepts empty/null tokens
    - NEVER logs token values (only "valid" or "invalid")
    - ALWAYS checks L9_EXECUTOR_API_KEY is configured
    """
    from api.auth import EXECUTOR_API_KEY

    # Fail-fast: API key must be configured
    if not EXECUTOR_API_KEY:
        logger.critical(
            "verify_ws_token: L9_EXECUTOR_API_KEY not configured - "
            "refusing ALL WebSocket connections"
        )
        return False

    # Get token from explicit param or query string
    effective_token = token or websocket.query_params.get("token")

    # Validate token exists
    if not effective_token:
        logger.warning(
            "verify_ws_token: No token provided",
            remote=websocket.client.host if websocket.client else "unknown",
        )
        return False

    # Validate token matches (constant-time comparison would be better for prod)
    if effective_token != EXECUTOR_API_KEY:
        logger.warning(
            "verify_ws_token: Invalid token",
            remote=websocket.client.host if websocket.client else "unknown",
        )
        return False

    logger.debug("verify_ws_token: Token valid")
    return True


class WebSocketOrchestrator:
    """
    Manages live WebSocket connections from L9 agents.

    Thread-safe singleton - use `ws_orchestrator` module-level instance.
    """

    def __init__(self) -> None:
        """Initializes the WebSocketOrchestrator for managing L9 agent WebSocket connections."""
        self._connections: dict[str, WebSocket] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        self._connected_at: dict[str, datetime] = {}
        logger.info("WebSocketOrchestrator initialized")

    # =========================================================================
    # Connection Management
    # =========================================================================

    @must_stay_async("callers use await")
    async def register(
        self,
        agent_id: str,
        websocket: WebSocket,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Register an agent's WebSocket connection.

        Args:
            agent_id: Unique identifier for the agent
            websocket: Active WebSocket connection
            metadata: Optional handshake metadata (capabilities, version, etc.)
        """
        self._connections[agent_id] = websocket
        self._metadata[agent_id] = metadata or {}
        self._connected_at[agent_id] = datetime.now(UTC)
        logger.info(
            "Agent %s registered (metadata=%s)",
            agent_id,
            list((metadata or {}).keys()),
        )

    @must_stay_async("callers use await")
    async def unregister(self, agent_id: str) -> None:
        """
        Unregister an agent and clean up resources.

        Args:
            agent_id: Agent to unregister
        """
        self._connections.pop(agent_id, None)
        self._metadata.pop(agent_id, None)
        self._connected_at.pop(agent_id, None)
        logger.info("Agent %s unregistered", agent_id)

    def is_connected(self, agent_id: str) -> bool:
        """Check if an agent is currently connected."""
        return agent_id in self._connections

    def get_connected_agents(self) -> list[str]:
        """Get list of currently connected agent IDs."""
        return list(self._connections.keys())

    def get_metadata(self, agent_id: str) -> dict[str, Any]:
        """Get metadata for a connected agent."""
        return self._metadata.get(agent_id, {})

    # =========================================================================
    # Message Handling
    # =========================================================================

    @must_stay_async("callers use await")
    async def handle_incoming(self, agent_id: str, data: dict[str, Any]) -> None:
        """
        Handle an incoming message from an agent.

        Routes based on message type:
        - Conversation tasks → handle_conversation_task() → AgentExecutorService
        - Worker agent events → ws_bridge → TaskQueue

        Args:
            agent_id: Agent that sent the message
            data: Raw JSON payload from WebSocket
        """
        # Route conversation tasks to AgentExecutorService
        if data.get("type") == "conversation" or "message" in data:
            response = await self.handle_conversation_task(agent_id, data)
            await self.dispatch_event(agent_id, response)
            return

        # Route worker agent events through ws_bridge (existing behavior)
        from core.schemas.ws_event_stream import EventMessage, EventType
        from orchestrators.ws_bridge import handle_ws_event

        # Convert raw data to EventMessage
        try:
            event_type_str = data.get("type", "log")
            event_type = EventType(event_type_str)
        except ValueError:
            event_type = EventType.LOG

        event = EventMessage(
            type=event_type,
            agent_id=agent_id,
            payload=data.get("payload", data),
            trace_id=data.get("trace_id"),
            correlation_id=data.get("correlation_id"),
        )

        # Route through ws_bridge for task conversion
        envelope = handle_ws_event(event)
        if envelope:
            logger.debug(
                "Created task envelope from agent %s: kind=%s",
                agent_id,
                envelope.task.kind,
            )

    @must_stay_async("callers use await")
    async def handle_conversation_task(
        self, agent_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Handle conversation task routing to AgentExecutorService.

        Routes L-CTO chat interactions through kernel-aware agent stack:
        AgentTask → AgentExecutorService → AIOSRuntime → kernel execution

        Multi-part directive support (harvested from tokenizer):
        - Compound directives like "Deploy RIL, test ToT" are automatically
          segmented and processed as separate tasks.

        Args:
            agent_id: WebSocket client ID (e.g., "lws-12345")
            data: Message payload with required "message" field

        Returns:
            Response dict with task_id, status, reply (combined if multi-part)
        """
        from core.agents.schemas import (
            AgentTask,
            AgentType,
            DuplicateTaskResponse,
            ExecutionResult,
        )

        # Validate message field
        message = data.get("message")
        if not message:
            return {
                "task_id": "",
                "status": "error",
                "reply": "Missing required field: message",
            }

        # Get executor from app.state (injected during startup)
        try:
            from api.server import app

            executor = getattr(app.state, "agent_executor", None)
        except ImportError:
            return {
                "task_id": "",
                "status": "error",
                "reply": "Agent executor not available (import failed)",
            }

        if executor is None:
            return {
                "task_id": "",
                "status": "error",
                "reply": "Agent executor not initialized - check server startup logs",
            }

        thread_id = data.get("thread_id", "ws-default")
        metadata = data.get("metadata", {})

        # === Multi-Part Directive Support (harvested from tokenizer) ===
        segment_enabled = data.get("segment_multi_part", True)
        segmenter = get_segmenter()
        segment_result = segmenter.segment(message)

        if segment_enabled and segment_result.segment_count > 1:
            logger.info(
                "handle_conversation_task: multi-part directive detected",
                segment_count=segment_result.segment_count,
                segments=segment_result.segments,
                agent_id=agent_id,
            )

            replies: list[tuple[str, str, str]] = []  # (segment, status, reply)
            first_task_id = None

            for i, segment in enumerate(segment_result.segments):
                task = AgentTask(
                    agent_id="l-cto",
                    agent_type=AgentType.ASSISTANT,
                    source_id=agent_id,
                    thread_identifier=thread_id,
                    payload={
                        "message": segment,
                        "channel": "ws",
                        "metadata": metadata,
                        "segment_index": i,
                        "total_segments": segment_result.segment_count,
                        "from_multi_part": True,
                        "original_message": message,
                    },
                )

                if first_task_id is None:  # nosemgrep: l9-singleton-requires-lock
                    first_task_id = str(task.id)

                try:
                    result = await executor.start_agent_task(task)

                    if isinstance(result, DuplicateTaskResponse):
                        replies.append((segment, "duplicate", "Duplicate task"))
                    else:
                        replies.append(
                            (
                                segment,
                                result.status,
                                result.result or result.error or "No response",
                            )
                        )
                except Exception as e:
                    logger.exception(
                        "handle_conversation_task: segment %d failed: %s", i, str(e)
                    )
                    replies.append((segment, "error", f"Error: {e!s}"))

            # Combine replies
            successful = [r for s, st, r in replies if st == "completed"]
            all_successful = all(st == "completed" for _, st, _ in replies)

            if all_successful:
                combined_reply = (
                    "\n\n---\n\n".join(successful)
                    if len(successful) > 1
                    else (successful[0] if successful else "All tasks processed")
                )
            else:
                combined_reply = (
                    f"Processed {len(successful)}/{len(replies)} tasks:\n\n"
                )
                for seg, status, reply in replies:
                    icon = "✅" if status == "completed" else "⚠️"
                    combined_reply += (
                        f"{icon} **{seg}**: {reply[:200]}...\n\n"
                        if len(reply) > 200
                        else f"{icon} **{seg}**: {reply}\n\n"
                    )

            return {
                "task_id": first_task_id or "",
                "status": "completed" if all_successful else "partial",
                "reply": combined_reply,
                "was_multi_part": True,
                "segments_processed": segment_result.segment_count,
            }

        # === Single task execution (original behavior) ===
        task = AgentTask(
            agent_id="l-cto",
            agent_type=AgentType.ASSISTANT,
            source_id=agent_id,
            thread_identifier=thread_id,
            payload={
                "message": message,
                "channel": "ws",
                "metadata": metadata,
            },
        )

        logger.info(
            "handle_conversation_task: task_id=%s, thread=%s, source=%s",
            str(task.id),
            thread_id,
            agent_id,
        )

        # Execute task
        try:
            result = await executor.start_agent_task(task)
        except Exception as e:
            logger.exception("handle_conversation_task: execution failed: %s", str(e))
            return {
                "task_id": str(task.id),
                "status": "error",
                "reply": f"Execution error: {e!s}",
            }

        # Handle duplicate detection
        if isinstance(result, DuplicateTaskResponse):
            logger.info(
                "handle_conversation_task: duplicate task: %s", str(result.task_id)
            )
            return {
                "task_id": str(result.task_id),
                "status": "duplicate",
                "reply": "Duplicate task detected",
            }

        # Handle ExecutionResult
        if isinstance(result, ExecutionResult):
            reply = result.result or result.error or "No response"
            return {
                "task_id": str(result.task_id),
                "status": result.status,
                "reply": reply,
            }

        # Fallback (should not happen with proper typing)
        logger.warning(
            "handle_conversation_task: unexpected result type: %s", type(result)
        )
        return {
            "task_id": str(task.id),
            "status": "error",
            "reply": "Unexpected result format",
        }

    async def on_user_message(self, message: str) -> list[str]:
        """
        Handle user message and trigger reactive task generation and dispatch.

        Args:
            message: User message text

        Returns:
            List of task IDs for generated and dispatched tasks
        """
        from uuid import uuid4

        from core.agents.executor import _generate_tasks_from_query
        from runtime.task_queue import QueuedTask, dispatch_task_immediate

        # Generate tasks from query
        task_specs = await _generate_tasks_from_query(message)

        if not task_specs:
            logger.warning(f"No tasks generated from message: {message[:100]}")
            return []

        task_ids = []

        # Dispatch each task immediately
        for spec in task_specs:
            try:
                task = QueuedTask(
                    task_id=str(uuid4()),
                    name=spec["name"],
                    payload=spec["payload"],
                    handler=spec["handler"],
                    agent_id="L",
                    priority=spec.get("priority", 5),
                    tags=["reactive", "user_message"],
                )

                task_id = await dispatch_task_immediate(task)
                task_ids.append(task_id)
                logger.info(f"Dispatched reactive task {task_id} from user message")
            except Exception as e:
                logger.error(
                    f"Failed to dispatch task from message: {e}", exc_info=True
                )

        return task_ids

    # =========================================================================
    # Outbound Dispatch
    # =========================================================================

    async def dispatch_event(self, agent_id: str, event: Any) -> None:
        """
        Send an event to a specific agent.

        Args:
            agent_id: Target agent
            event: EventMessage or dict to send

        Raises:
            RuntimeError: If agent is not connected
        """
        ws = self._connections.get(agent_id)
        if ws is None:
            raise RuntimeError(f"Agent {agent_id} is not connected")

        # Serialize event
        if hasattr(event, "model_dump"):
            payload = event.model_dump(mode="json")
        else:
            payload = dict(event)

        await ws.send_json(payload)
        logger.debug(
            "Dispatched event to agent %s: type=%s", agent_id, payload.get("type")
        )

    async def broadcast(self, event: Any, exclude: list[str] | None = None) -> int:
        """
        Broadcast an event to all connected agents.

        Args:
            event: EventMessage or dict to send
            exclude: Optional list of agent IDs to skip

        Returns:
            Number of agents the event was sent to
        """
        exclude = exclude or []
        count = 0

        for agent_id in list(self._connections.keys()):
            if agent_id in exclude:
                continue
            try:
                await self.dispatch_event(agent_id, event)
                count += 1
            except Exception as e:
                logger.warning("Failed to broadcast to %s: %s", agent_id, e)

        return count


# =============================================================================
# Module-level Singleton
# =============================================================================

ws_orchestrator = WebSocketOrchestrator()

__all__ = ["WebSocketOrchestrator", "verify_ws_token", "ws_orchestrator"]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-013",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.agents.executor",
        "core.decorators",
        "core.schemas.ws_event_stream",
        "runtime.task_queue",
    ],
    "tags": [
        "adapter",
        "api",
        "async",
        "debugging",
        "event-driven",
        "logging",
        "messaging",
        "operations",
        "orchestration",
        "queue",
    ],
    "keywords": [
        "agent",
        "agents",
        "broadcast",
        "connected",
        "dispatch",
        "event",
        "handle",
        "incoming",
    ],
    "business_value": "The module-level singleton `ws_orchestrator` is the canonical instance. Version: 1.0.0",
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
