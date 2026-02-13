"""
L9 Core Agents - Agent Instance
===============================

Represents a running agent instance with its configuration and bound tools.

The AgentInstance class manages:
- Agent configuration and state
- Tool bindings (approved by governance)
- Context assembly for AIOS calls
- Conversation history within a task

This class does NOT:
- Execute reasoning (that's AIOS runtime)
- Execute tools (that's tool registry)
- Define agent personalities (that's loaded from registry)

L Memory Usage Rules
====================

For agent L (agent_id="L"), the following memory usage rules apply:

1. governance_meta:
   - Use memory_search(governance_meta, ...) to look up rules, authority, policies
   - Use memory_write(governance_meta, ...) to record new governance rules (rare)
   - Example: "What are the approval requirements for GMP runs?"

2. project_history:
   - Use memory_search(project_history, ...) before executing long plans
   - Use memory_write(project_history, ...) after major decisions or milestones
   - Example: "What architecture decisions were made for the tool system?"

3. tool_audit:
   - Automatically populated by tool call logging (ToolGraph.log_tool_call)
   - Use memory_search(tool_audit, ...) to review past actions
   - Example: "What tools did I call in the last session?"

4. session_context:
   - Use memory_write(session_context, ...) to store current session state
   - Use memory_search(session_context, ...) to retrieve session context
   - Example: "What was I working on in this session?"

Tool Call Logging:
- All tool calls (internal, MCP, Mac Agent, GMP) must call ToolGraph.log_tool_call
- This automatically populates tool_audit segment
- Use tool_call_wrapper() helper to ensure consistent logging

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
# DORA HEADER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_meta__ = {
    "component_id": "COR-FOUN-001",
    "component_name": "Agent Instance",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-18T01:57:15Z",
    "layer": "foundation",
    "domain": "agent_execution",
    "module_name": "agent_instance",
    "type": "utility",
    "status": "active",
    "purpose": "Represents a running agent instance with its configuration and bound tools.",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "PostgreSQL", "Redis"],
        "memory_layers": ["working_memory", "episodic_memory", "semantic_memory"],
        "imported_by": [
            "core.agents.__init__",
            "core.agents.bootstrap.orchestrator",
            "core.agents.executor",
            "tests.integration.test_governance_tracking_e2e",
            "tests.unit.test_guarded_execution",
        ],
    },
}
# ============================================================================

import hashlib
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import structlog

from core.agents.schemas import AgentConfig, AgentTask, ExecutorState, ToolBinding

logger = structlog.get_logger(__name__)

_OPENAI_TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class AgentInstance:
    """
    Represents a running agent instance.

    Manages the agent's configuration, state, and context during task execution.
    This class is instantiated by the AgentExecutorService for each task.

    Attributes:
        instance_id: Unique instance identifier
        config: Agent configuration
        task: The task being executed
        state: Current executor state
        iteration: Current iteration in execution loop
        history: Message history for this task
        tool_results: Results from tool calls
        created_at: Instance creation timestamp
    """

    def __init__(
        self,
        config: AgentConfig,
        task: AgentTask,
    ):
        """
        Initialize a new agent instance.

        Args:
            config: Agent configuration with personality and tools
            task: The task to execute
        """
        self._instance_id = uuid4()
        self._config = config
        self._task = task
        self._state = ExecutorState.INITIALIZING
        self._iteration = 0
        self._history: list[dict[str, Any]] = []
        self._tool_results: list[dict[str, Any]] = []
        self._created_at = datetime.now(UTC)
        self._total_tokens = 0
        self._tool_name_map: dict[str, str] = {}
        self._tool_name_reverse_map: dict[str, str] = {}
        self._user_corrections: list[dict[str, Any]] = []
        self._governance_blocks: list[dict[str, Any]] = []
        self._discovered_tools: list[dict[str, Any]] | None = (
            None  # Dynamic discovery cache
        )

        logger.info(
            "AgentInstance created",
            extra={
                "instance_id": str(self._instance_id),
                "agent_id": config.agent_id,
                "task_id": str(task.id),
            },
        )

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def instance_id(self) -> UUID:
        """Get instance ID."""
        return self._instance_id

    @property
    def config(self) -> AgentConfig:
        """Get agent configuration."""
        return self._config

    @property
    def task(self) -> AgentTask:
        """Get the task being executed."""
        return self._task

    @property
    def state(self) -> ExecutorState:
        """Get current executor state."""
        return self._state

    @property
    def iteration(self) -> int:
        """Get current iteration number."""
        return self._iteration

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self._total_tokens

    @property
    def thread_id(self) -> UUID:
        """Get the thread ID for this task."""
        return self._task.get_thread_id()

    @property
    def tool_results(self) -> list[dict[str, Any]]:
        """Get list of tool call results."""
        return self._tool_results.copy()

    @property
    def user_corrections(self) -> list[dict[str, Any]]:
        """Get list of user corrections tracked during execution."""
        return self._user_corrections.copy()

    @property
    def governance_blocks(self) -> list[dict[str, Any]]:
        """Get list of governance blocks tracked during execution."""
        return self._governance_blocks.copy()

    # =========================================================================
    # State Management
    # =========================================================================

    def transition_to(self, new_state: ExecutorState) -> None:
        """
        Transition to a new state.

        Args:
            new_state: Target state
        """
        old_state = self._state
        self._state = new_state

        logger.debug(
            f"State transition: {old_state.value} -> {new_state.value}",
            extra={
                "instance_id": str(self._instance_id),
                "task_id": str(self._task.id),
            },
        )

    def increment_iteration(self) -> int:
        """
        Increment iteration counter.

        Returns:
            New iteration number
        """
        self._iteration += 1
        return self._iteration

    def add_tokens(self, tokens: int) -> None:
        """Add to total token count."""
        self._total_tokens += tokens

    def add_user_correction(
        self, correction: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Track a user correction during execution.

        Used for behavioral gap analysis in self-reflection.

        Args:
            correction: The correction text from user
            metadata: Optional metadata about the correction
        """
        self._user_corrections.append(
            {
                "correction": correction,
                "iteration": self._iteration,
                "timestamp": datetime.now(UTC).isoformat(),
                "metadata": metadata or {},
            }
        )
        logger.debug(
            "User correction tracked",
            extra={
                "instance_id": str(self._instance_id),
                "task_id": str(self._task.id),
                "iteration": self._iteration,
            },
        )

    def add_governance_block(
        self,
        block_type: str,
        violation: str | None = None,
        pattern: str | None = None,
        tool_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Track a governance block during execution.

        Used for behavioral gap analysis in self-reflection.

        Args:
            block_type: Type of block (authority_block, safety_block, tool_approval_block)
            violation: The violation description if applicable
            pattern: The pattern that triggered the block if applicable
            tool_id: The tool ID if this is a tool approval block
            metadata: Optional additional metadata
        """
        block = {
            "type": block_type,
            "agent_id": self._config.agent_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "iteration": self._iteration,
        }
        if violation:
            block["violation"] = violation
        if pattern:
            block["pattern"] = pattern
        if tool_id:
            block["tool_id"] = tool_id
        if metadata:
            block["metadata"] = metadata

        self._governance_blocks.append(block)
        logger.debug(
            f"Governance block tracked: {block_type}",
            extra={
                "instance_id": str(self._instance_id),
                "task_id": str(self._task.id),
                "block_type": block_type,
            },
        )

    # =========================================================================
    # Tool Management
    # =========================================================================

    def get_bound_tools(self) -> list[ToolBinding]:
        """
        Get list of tools bound to this agent.

        Returns:
            List of enabled tool bindings
        """
        return [t for t in self._config.tools if t.enabled]

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Get tool definitions in OpenAI function calling format.

        If dynamic discovery has been run (via prepare_dynamic_tools), returns
        the dynamically discovered tools. Otherwise returns statically bound tools.

        function.name == tool_id (canonical identity, must match exactly).

        Returns:
            List of tool definitions for AIOS
        """
        # Use dynamically discovered tools if available
        if self._discovered_tools is not None:
            logger.debug(
                "Using dynamically discovered tools",
                tool_count=len(self._discovered_tools),
                task_id=str(self._task.id),
            )
            return self._discovered_tools

        # Fallback: static tool binding (DEPRECATED - GMP-78 Phase 2)
        # Static binding is legacy behavior. Dynamic discovery is preferred.
        # Set L9_DYNAMIC_TOOL_DISCOVERY=true (default) to use semantic discovery.
        import warnings

        warnings.warn(
            "Static tool binding is deprecated. Use prepare_dynamic_tools() for "
            "semantic discovery. Set L9_DYNAMIC_TOOL_DISCOVERY=true to enable.",
            DeprecationWarning,
            stacklevel=2,
        )
        logger.debug(
            "Using deprecated static tool binding",
            task_id=str(self._task.id),
            hint="Enable L9_DYNAMIC_TOOL_DISCOVERY=true for semantic discovery",
        )
        definitions = []
        self._build_tool_name_map()
        for tool in self.get_bound_tools():
            openai_name = self._tool_name_reverse_map.get(tool.tool_id, tool.tool_id)
            definitions.append(
                {
                    "type": "function",
                    "function": {
                        "name": openai_name,  # OpenAI-compatible alias
                        "description": tool.description or "",
                        "parameters": tool.input_schema,
                    },
                }
            )
        return definitions

    @must_stay_async("callers use await")
    async def prepare_dynamic_tools(self) -> int:
        """
        Discover and cache relevant tools for this task using semantic search.

        GMP-78 Phase 2: Dynamic Tool Discovery Integration.
        GMP-79: Multi-turn caching via Redis.

        This method:
        1. Checks Redis cache for previously discovered tools (multi-turn)
        2. If cache miss: runs semantic search against tool embeddings
        3. Caches discovered tools in Redis for future turns
        4. Stores locally for get_tool_definitions()

        Call this BEFORE assemble_context() for dynamic tool discovery.
        If not called, get_tool_definitions() returns static bound tools.

        Returns:
            Number of tools discovered
        """
        try:
            from core.tools.dynamic_discovery import (
                cache_tools,
                discover_tools_for_task,
                get_cached_tools,
                is_dynamic_discovery_enabled,
            )

            if not is_dynamic_discovery_enabled():
                logger.debug("Dynamic tool discovery disabled, using static binding")
                return 0

            task_id = str(self._task.id)

            # GMP-79: Check Redis cache first (multi-turn optimization)
            cached = await get_cached_tools(task_id)
            if cached:
                self._discovered_tools = cached
                logger.info(
                    "Using cached tools (multi-turn)",
                    task_id=task_id,
                    tools_cached=len(cached),
                )
                return len(cached)

            # Extract task payload for semantic search
            task_query = self._extract_task_query()
            if not task_query:
                logger.debug("No task query found, using static binding")
                return 0

            # Discover relevant tools via semantic search
            self._discovered_tools = await discover_tools_for_task(task_query)

            # GMP-79: Cache tools for future turns
            if self._discovered_tools:
                await cache_tools(task_id, self._discovered_tools)

            logger.info(
                "Dynamic tool discovery complete",
                task_id=task_id,
                tools_discovered=len(self._discovered_tools),
                task_preview=task_query[:50] if task_query else None,
                cached=True,
            )

            return len(self._discovered_tools)

        except ImportError as e:
            logger.debug(f"Dynamic discovery not available: {e}")
            return 0
        except Exception as e:
            logger.warning(f"Dynamic tool discovery failed, using static binding: {e}")
            self._discovered_tools = None
            return 0

    def _extract_task_query(self) -> str | None:
        """
        Extract the task query/description for semantic tool search.

        Returns:
            Task query string or None if not extractable
        """
        payload = self._task.payload

        # Try common payload fields
        if isinstance(payload, dict):
            # Priority: query > content > message > description
            for field in ["query", "content", "message", "description", "text"]:
                if payload.get(field):
                    return str(payload[field])

        # If payload is a string, use it directly
        if isinstance(payload, str) and payload.strip():
            return payload

        return None

    def clear_discovered_tools(self) -> None:
        """Clear cached discovered tools (revert to static binding)."""
        self._discovered_tools = None

    def has_tool(self, tool_id: str) -> bool:
        """Check if a tool is bound to this agent."""
        resolved_tool_id = self.resolve_tool_id(tool_id)
        return any(
            t.tool_id == resolved_tool_id and t.enabled for t in self._config.tools
        )

    def resolve_tool_id(self, tool_name: str) -> str:
        """Resolve an OpenAI tool name alias back to canonical tool_id."""
        self._build_tool_name_map()
        return self._tool_name_map.get(tool_name, tool_name)

    def _build_tool_name_map(self) -> None:
        """Builds a mapping of tool names to their identifiers for quick lookup."""
        if self._tool_name_map:
            return

        for tool in self.get_bound_tools():
            tool_id = tool.tool_id
            openai_name = tool_id
            if not _OPENAI_TOOL_NAME_PATTERN.match(openai_name):
                openai_name = re.sub(r"[^a-zA-Z0-9_-]", "_", tool_id)
                openai_name = openai_name or "tool"
                if (
                    openai_name in self._tool_name_map
                    and self._tool_name_map[openai_name] != tool_id
                ):
                    suffix = hashlib.sha1(tool_id.encode("utf-8")).hexdigest()[:8]
                    openai_name = f"{openai_name}_{suffix}"
                logger.warning(
                    "tool_name_sanitized",
                    tool_id=tool_id,
                    openai_name=openai_name,
                )
            self._tool_name_map[openai_name] = tool_id
            self._tool_name_reverse_map[tool_id] = openai_name

    # =========================================================================
    # History Management
    # =========================================================================

    def add_user_message(
        self, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Add a user message to history.

        Args:
            content: Message content
            metadata: Optional metadata
        """
        self._history.append(
            {
                "role": "user",
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def add_assistant_message(
        self, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Add an assistant message to history.

        Args:
            content: Message content
            metadata: Optional metadata
        """
        self._history.append(
            {
                "role": "assistant",
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def add_assistant_message_with_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add an assistant message with tool_calls to history.

        OpenAI requires assistant messages with tool_calls to precede
        tool result messages. This method properly formats the message.

        Args:
            tool_calls: List of tool call dicts with id, type, function
            content: Optional message content (usually None for tool calls)
            metadata: Optional metadata
        """
        self._history.append(
            {
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls,
                "metadata": metadata or {},
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def add_tool_result(
        self,
        tool_id: str,
        call_id: str,
        result: Any,
        success: bool = True,
    ) -> None:
        """
        Add a tool result to history.

        Uses tool_id as canonical identity for result tracking.
        Large results are truncated to prevent context overflow.

        Args:
            tool_id: Canonical tool identity
            call_id: Call identifier
            result: Tool result
            success: Whether call succeeded
        """
        # Max chars for tool result content (prevents context overflow)
        MAX_TOOL_RESULT_CHARS = 4000
        TRUNCATION_MARKER = "\n\n[TRUNCATED - result exceeded 4000 chars]"

        # Convert result to string and truncate if needed
        result_str = str(result) if success else f"Error: {result}"
        was_truncated = False
        if len(result_str) > MAX_TOOL_RESULT_CHARS:
            result_str = result_str[:MAX_TOOL_RESULT_CHARS] + TRUNCATION_MARKER
            was_truncated = True
            logger.warning(
                "tool_result_truncated: tool_id=%s, original_len=%d",
                tool_id,
                len(str(result)),
            )

        self._tool_results.append(
            {
                "tool_id": tool_id,
                "call_id": call_id,
                "result": result,  # Store original for internal use
                "success": success,
                "timestamp": datetime.now(UTC).isoformat(),
                "truncated": was_truncated,
            }
        )

        # Also add to history for context (tool_id tagged for re-entry)
        self._history.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "content": result_str,  # Truncated version for LLM
                "metadata": {
                    "tool_id": tool_id,
                    "success": success,
                    "truncated": was_truncated,
                },
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def get_history(self) -> list[dict[str, Any]]:
        """Get message history."""
        return self._history.copy()

    def get_messages_for_aios(self) -> list[dict[str, Any]]:
        """
        Get messages formatted for AIOS call.

        Returns:
            List of message dicts formatted for OpenAI API
        """
        messages = []
        for msg in self._history:
            if msg["role"] == "tool":
                # Format tool results for AIOS
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.get("tool_call_id", ""),
                        "content": msg["content"],
                    }
                )
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                # Assistant message with tool calls - must include tool_calls array
                # OpenAI requires content to be a string (empty string if no content)
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.get("content") or "",  # Empty string, never None
                        "tool_calls": msg["tool_calls"],
                    }
                )
            else:
                messages.append(
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                    }
                )
        return messages

    # =========================================================================
    # Context Assembly
    # =========================================================================

    def _build_dag_context_section(self) -> str:
        """
        Build context section from DAG-stored thread_context and semantic_hits.

        Extracts context from self._task.context (populated by slack_ingest.py)
        and formats it for injection into the system prompt.

        Returns:
            Formatted context string, or empty string if no context available.
        """
        task_context = self._task.context or {}
        thread_context = task_context.get("thread_context", {})
        semantic_hits = task_context.get("semantic_hits", {})

        sections = []

        # Thread context: past messages in this conversation
        packets = thread_context.get("packets", [])
        if packets:
            section_lines = ["## Recent Conversation History"]
            for packet in packets[-5:]:  # Last 5 messages
                payload = packet.get("payload", {})
                # Normalize: support both 'content' and 'text' field names
                text = (payload.get("content") or payload.get("text", ""))[:300]
                user_id = payload.get("user_id", "unknown")
                if text:
                    section_lines.append(f"- [{user_id}]: {text}")
            if len(section_lines) > 1:  # Has content beyond header
                sections.append("\n".join(section_lines))

        # Semantic hits: related knowledge from memory
        results = semantic_hits.get("results", [])
        if results:
            section_lines = ["## Related Knowledge (from memory)"]
            for hit in results[:3]:  # Top 3 hits
                payload = hit.get("payload", {})
                # Normalize: support both 'content' and 'text' field names
                text = (payload.get("content") or payload.get("text", ""))[:200]
                score = hit.get("score", 0)
                if text:
                    section_lines.append(f"- (relevance: {score:.2f}) {text}")
            if len(section_lines) > 1:  # Has content beyond header
                sections.append("\n".join(section_lines))

        if not sections:
            return ""

        # Wrap in clear section delimiters
        header = "\n\n---\n**CONTEXT FROM MEMORY (DAG-injected)**\n"
        footer = "\n---\n"
        return header + "\n\n".join(sections) + footer

    def assemble_context(self) -> dict[str, Any]:
        """
        Assemble full context bundle for AIOS call.

        Injects DAG-stored context (thread_context, semantic_hits) into
        the system prompt for conversation continuity.

        Returns:
            Context dict containing:
            - system_prompt: System prompt for the agent (enriched with DAG context)
            - messages: Conversation history
            - tools: Available tool definitions
            - task: Current task information
            - metadata: Additional context
        """
        # Build enriched system prompt with DAG context
        base_prompt = self._config.system_prompt or ""
        dag_context = self._build_dag_context_section()
        enriched_prompt = base_prompt + dag_context if dag_context else base_prompt

        return {
            "system_prompt": enriched_prompt,
            "messages": self.get_messages_for_aios(),
            "tools": self.get_tool_definitions(),
            "task": {
                "id": str(self._task.id),
                "kind": self._task.kind.value,
                "payload": self._task.payload,
                "context": self._task.context,
            },
            "metadata": {
                "agent_id": self._config.agent_id,
                "personality_id": self._config.personality_id,
                "model": self._config.model,
                "temperature": self._config.temperature,
                "max_tokens": self._config.max_tokens,
                "iteration": self._iteration,
                "thread_id": str(self.thread_id),
            },
        }

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_trace_dict(self) -> dict[str, Any]:
        """
        Serialize instance state for trace logging.

        Returns:
            Dict suitable for packet storage
        """
        return {
            "instance_id": str(self._instance_id),
            "agent_id": self._config.agent_id,
            "task_id": str(self._task.id),
            "thread_id": str(self.thread_id),
            "state": self._state.value,
            "iteration": self._iteration,
            "total_tokens": self._total_tokens,
            "history_length": len(self._history),
            "tool_calls": len(self._tool_results),
            "created_at": self._created_at.isoformat(),
        }


# =============================================================================
# Public API
__all__ = [
    "AgentInstance",
]
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    # === IDENTITY ===
    "component_id": "COR-FOUN-001",
    # === GOVERNANCE ===
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "security_classification": "internal",
    # === DEPENDENCIES ===
    "dependencies": ["core.agents.schemas"],
    # === OPERATIONAL ===
    "execution_mode": "on-demand",
    "timeout_seconds": 30,
    "performance_tier": "batch",
    "retry_policy": "exponential",
    "circuit_breaker_enabled": True,
    "circuit_breaker_threshold": 5,
    # === OBSERVABILITY ===
    "monitoring_required": True,
    "logging_level": "info",
    "success_metrics": {
        "latency_p95_ms": 500,
        "throughput_ops_per_sec": 100,
        "availability_percent": 99.9,
        "error_rate_percent": 0.1,
    },
    # === DISCOVERY ===
    "tags": [
        "agent-execution",
        "cache",
        "foundation",
        "graph-db",
        "llm",
        "logging",
        "utility",
    ],
    "keywords": ["add", "agent", "aios", "assemble", "assistant", "block"],
    "business_value": "Represents a running agent instance with its configuration and bound tools.",
    # === CHANGE TRACKING ===
    "last_modified": "2026-01-18T01:57:15Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================

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
