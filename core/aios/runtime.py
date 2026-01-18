"""
L9 Core AIOS - Runtime
======================

The AIOS Runtime handles agent reasoning by calling the LLM with context
and tools. It returns either a final response or a tool call request.

Key responsibilities:
- Assemble messages from context
- Call LLM with tool definitions
- Parse response into AIOSResult
- Handle errors gracefully

This module does NOT:
- Execute tools (that's the executor's job)
- Store packets (that's the executor's job)
- Define agent personalities (those are loaded from registry)

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Runtime",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-14T15:22:16Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "runtime",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": ["api.server", "core.aios.__init__", "tests.core.aios.test_runtime"],
    },
}
# ============================================================================

import json
import structlog
import os
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from openai import AsyncOpenAI

from core.agents.schemas import (
    AIOSResult,
    AIOSResultType,
    ToolCallRequest,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# Default System Prompt
# =============================================================================

DEFAULT_SYSTEM_PROMPT = """You are L, an AI assistant operating within the L9 AI Operating System.

IDENTITY
You are L. Role: Intelligent assistant and task executor.
You operate autonomously within defined boundaries.

CAPABILITIES
- Reasoning: Think step by step about complex problems
- Tool Use: When tools are available, use them to accomplish tasks
- Memory: Your conversation context is managed by the system

BEHAVIOR
- Be concise and direct in responses
- Use tools when they would help accomplish the task
- If unsure, reason through the problem before responding
- Never fabricate information you don't have

RESPONSE FORMAT
- For simple queries: Provide a direct answer
- For complex tasks: Think through the steps, then respond
- When using tools: Call the appropriate tool with correct arguments
"""


# =============================================================================
# AIOS Runtime
# =============================================================================


class AIOSRuntime:
    """
    AIOS Runtime for agent reasoning.

    Handles LLM calls with tool support and returns structured results.

    Attributes:
        model: LLM model to use
        temperature: Default temperature
        max_tokens: Max response tokens
        default_system_prompt: System prompt when none provided
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        default_system_prompt: Optional[str] = None,
    ):
        """
        Initialize AIOS Runtime.

        Args:
            api_key: OpenAI API key (from env if not provided)
            model: LLM model (from env if not provided)
            temperature: Default temperature
            max_tokens: Default max tokens
            default_system_prompt: Default system prompt
        """
        # Get API key (read at init, not import time per spec)
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            logger.warning("OPENAI_API_KEY not set - AIOS runtime will fail on calls")

        # Configuration
        self._model = model or os.getenv("L9_LLM_MODEL", "gpt-4o")
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._default_system_prompt = default_system_prompt or DEFAULT_SYSTEM_PROMPT

        # Initialize client (lazy)
        self._client: Optional[AsyncOpenAI] = None

        logger.info(
            "AIOSRuntime initialized: model=%s, temperature=%.1f, max_tokens=%d",
            self._model,
            self._temperature,
            self._max_tokens,
        )

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def model(self) -> str:
        """Get model name."""
        return self._model

    @property
    def temperature(self) -> float:
        """Get default temperature."""
        return self._temperature

    # =========================================================================
    # Client Management
    # =========================================================================

    def _get_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("OPENAI_API_KEY not configured")
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    # =========================================================================
    # Main API
    # =========================================================================

    async def execute_reasoning(
        self,
        context: dict[str, Any],
    ) -> AIOSResult:
        """
        Execute reasoning with the given context.

        This is the main entry point called by AgentExecutorService.

        Args:
            context: Context bundle from AgentInstance.assemble_context()
                - system_prompt: Optional system prompt override
                - messages: Conversation history
                - tools: Available tool definitions
                - task: Current task info
                - metadata: Agent metadata

        Returns:
            AIOSResult with response or tool call
        """
        start_time = datetime.utcnow()

        try:
            # Extract context
            system_prompt = context.get("system_prompt") or self._default_system_prompt
            messages = context.get("messages", [])
            tools = context.get("tools", [])
            metadata = context.get("metadata", {})

            # Build messages list
            api_messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history
            for msg in messages:
                if msg.get("role") == "tool":
                    # Tool results need special formatting
                    api_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": msg.get("tool_call_id", ""),
                            "content": msg.get("content", ""),
                        }
                    )
                elif msg.get("role") == "assistant" and msg.get("tool_calls"):
                    # Assistant message with tool_calls - MUST include tool_calls array
                    # OpenAI requires assistant messages that precede tool results
                    # to have the tool_calls that generated those results
                    api_messages.append(
                        {
                            "role": "assistant",
                            "content": msg.get("content") or "",  # Empty string, never None
                            "tool_calls": msg.get("tool_calls"),
                        }
                    )
                else:
                    api_messages.append(
                        {
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", ""),
                        }
                    )

            # Get model params from metadata or use defaults
            model = metadata.get("model", self._model)
            temperature = metadata.get("temperature", self._temperature)
            max_tokens = metadata.get("max_tokens", self._max_tokens)

            # Build API call kwargs
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": api_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Add tools if available
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            # Call LLM
            client = self._get_client()
            response = await client.chat.completions.create(**kwargs)

            # Parse response
            choice = response.choices[0]
            message = choice.message
            tokens_used = response.usage.total_tokens if response.usage else 0
            finish_reason = choice.finish_reason

            # Check for tool calls
            if message.tool_calls and len(message.tool_calls) > 0:
                # Extract first tool call (handle one at a time)
                tool_call = message.tool_calls[0]

                # Parse tool arguments
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    # Fail loudly: explicit error logging and raise
                    logger.error(
                        "AIOS tool_call.json_decode_failed",
                        tool_id=tool_call.function.name,
                        raw_arguments=tool_call.function.arguments,
                        error=str(e),
                        exc_info=True,
                    )
                    raise ValueError(
                        f"Failed to parse tool call arguments for {tool_call.function.name}: {str(e)}"
                    ) from e

                # Create tool call request
                # function.name IS the tool_id (canonical identity)
                tool_request = ToolCallRequest(
                    call_id=uuid4(),  # Generate our own ID for tracking
                    tool_id=tool_call.function.name,  # function.name == tool_id
                    arguments=arguments,
                    task_id=UUID(metadata.get("task_id", str(uuid4()))),
                    iteration=metadata.get("iteration", 0),
                )

                logger.info(
                    "AIOS tool call: tool_id=%s, arguments=%s",
                    tool_request.tool_id,
                    tool_request.arguments,
                )

                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                logger.info(
                    "AIOS tool_call completed",
                    tool_id=tool_request.tool_id,
                    duration_ms=duration_ms,
                    tokens_used=tokens_used,
                )
                return AIOSResult.tool_request(tool_request, tokens_used=tokens_used)

            # No tool call - return response
            content = message.content or ""
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.info(
                "AIOS response completed",
                chars=len(content),
                tokens=tokens_used,
                finish_reason=finish_reason,
                duration_ms=duration_ms,
            )

            return AIOSResult(
                result_type=AIOSResultType.RESPONSE,
                content=content,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
            )

        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.exception("AIOS reasoning failed", error=str(e), duration_ms=duration_ms)
            return AIOSResult.error_result(str(e))

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Check AIOS runtime health.

        Returns:
            Health status dict
        """
        try:
            client = self._get_client()

            # Simple test call
            response = await client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "Reply with 'ok'"}],
                max_tokens=10,
            )

            return {
                "status": "healthy",
                "model": self._model,
                "response": response.choices[0].message.content,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "model": self._model,
                "error": str(e),
            }


# =============================================================================
# Factory Function
# =============================================================================


def create_aios_runtime(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> AIOSRuntime:
    """
    Factory function to create an AIOS runtime.

    Args:
        api_key: OpenAI API key
        model: LLM model name
        **kwargs: Additional runtime options

    Returns:
        Configured AIOSRuntime
    """
    return AIOSRuntime(
        api_key=api_key,
        model=model,
        **kwargs,
    )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "AIOSRuntime",
    "create_aios_runtime",
    "DEFAULT_SYSTEM_PROMPT",
]

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-031",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.agents.schemas"],
    "tags": ["api", "async", "core", "engine", "foundation", "llm", "logging", "messaging", "serialization", "testing"],
    "keywords": ["agent", "aios", "check", "create", "execute", "executor", "health", "model"],
    "business_value": "The AIOS Runtime handles agent reasoning by calling the LLM with context and tools. It returns either a final response or a tool call request.",
    "last_modified": "2026-01-14T15:22:16Z",
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
