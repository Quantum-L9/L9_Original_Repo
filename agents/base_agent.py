"""
L9 Agents - Base Agent
======================

Abstract base class for all L9 agents.

Provides:
- LLM client management with retry logic
- Message handling
- Memory integration
- Standard interfaces

Version: 2.0.0
- Added retry logic with exponential backoff (uses AgentConfig.retry_count)
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Base Agent",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "intelligence",
    "domain": "data_models",
    "module_name": "base_agent",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": ["episodic_memory", "working_memory"],
        "imported_by": [
            "agents.__init__",
            "agents.architect_agent.architect_agent_a",
            "agents.architect_agent.architect_agent_b",
            "agents.coder_agent.coder_agent_a",
            "agents.coder_agent.coder_agent_b",
            "agents.l_cto",
            "agents.qa_agent",
            "agents.reflection_agent",
            "tests.agents.test_architect_agents",
            "tests.agents.test_base_agent",
        ],
    },
}
# ============================================================================

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import structlog
from openai import AsyncOpenAI

from core.decorators import must_stay_async
from core.governance.rate_limit_policy import rate_limit
from core.resilience.retry import AsyncRetryConfig, async_retry

logger = structlog.get_logger(__name__)


class AgentRole(str, Enum):
    """Agent roles in the system."""

    ARCHITECT_PRIMARY = "architect_primary"
    ARCHITECT_CHALLENGER = "architect_challenger"
    CODER_PRIMARY = "coder_primary"
    CODER_SECONDARY = "coder_secondary"
    QA = "qa"
    REFLECTION = "reflection"


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    api_key: str | None = None
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 4000
    timeout_seconds: int = 120
    retry_count: int = 3
    system_prompt_override: str | None = None


@dataclass
class AgentMessage:
    """A message to/from an agent."""

    message_id: UUID = field(default_factory=uuid4)
    role: str = "user"  # system, user, assistant
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, str]:
        """Convert to OpenAI message format."""
        return {"role": self.role, "content": self.content}


@dataclass
class AgentResponse:
    """Response from an agent."""

    response_id: UUID = field(default_factory=uuid4)
    agent_id: str = ""
    content: str = ""
    structured_output: dict[str, Any] | None = None
    tokens_used: int = 0
    duration_ms: int = 0
    success: bool = True
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": str(self.response_id),
            "agent_id": self.agent_id,
            "content": (
                self.content[:200] + "..." if len(self.content) > 200 else self.content
            ),
            "success": self.success,
            "tokens_used": self.tokens_used,
            "duration_ms": self.duration_ms,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all L9 agents.

    Subclasses must implement:
    - get_system_prompt(): Return the agent's system prompt
    - run(): Execute the agent's primary function
    """

    agent_role: AgentRole = AgentRole.REFLECTION
    agent_name: str = "base_agent"

    def __init__(
        self,
        agent_id: str | None = None,
        config: AgentConfig | None = None,
    ):
        """
        Initialize the agent.

        Args:
            agent_id: Unique identifier (auto-generated if not provided)
            config: Agent configuration
        """
        self._agent_id = agent_id or f"{self.agent_name}_{uuid4().hex[:8]}"
        self._config = config or AgentConfig()
        self._client: AsyncOpenAI | None = None
        self._conversation_history: list[AgentMessage] = []
        self._initialized = False

        logger.info(f"Initialized {self.agent_name} with id={self._agent_id}")

    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return self._agent_id

    @property
    def config(self) -> AgentConfig:
        """Get agent configuration."""
        return self._config

    def _ensure_client(self) -> AsyncOpenAI:
        """Ensure OpenAI client is initialized."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._config.api_key)
        return self._client

    # ==========================================================================
    # Abstract Methods
    # ==========================================================================

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the agent's system prompt.

        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    @must_stay_async("callers use await")
    async def run(
        self, task: dict[str, Any], context: dict[str, Any] | None = None
    ) -> AgentResponse:
        """
        Execute the agent's primary function.

        Args:
            task: Task specification
            context: Optional execution context

        Returns:
            AgentResponse with result
        """
        pass

    # ==========================================================================
    # LLM Interaction
    # ==========================================================================

    @rate_limit("llm.openai")
    async def call_llm(
        self,
        messages: list[AgentMessage],
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> AgentResponse:
        """
        Call the LLM with messages and automatic retry on transient failures.

        Uses retry logic with exponential backoff (configured via AgentConfig.retry_count).
        Rate limited to 60 requests/minute per config/policies/rate_limits.yaml.

        Args:
            messages: List of messages
            temperature: Override temperature
            json_mode: If True, request JSON output

        Returns:
            AgentResponse

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        client = self._ensure_client()
        start_time = datetime.now(timezone.utc)

        # Build message list with system prompt
        api_messages = [{"role": "system", "content": self.get_system_prompt()}]
        api_messages.extend([m.to_dict() for m in messages])

        try:
            kwargs: dict[str, Any] = {
                "model": self._config.model,
                "messages": api_messages,
                "temperature": (
                    temperature if temperature is not None else self._config.temperature
                ),
                "max_tokens": self._config.max_tokens,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            # Create retry config from agent config
            retry_config = AsyncRetryConfig(
                max_retries=self._config.retry_count,
                base_backoff=0.5,
                max_backoff=30.0,
                jitter=0.1,
            )

            async def _make_llm_call():
                """Inner function for retry logic."""
                return await client.chat.completions.create(**kwargs)

            # Execute with retry for transient failures
            response = await async_retry(
                _make_llm_call,
                config=retry_config,
                operation=f"llm_call_{self._agent_id}",
            )

            content = response.choices[0].message.content or ""
            tokens = response.usage.total_tokens if response.usage else 0

            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            # Parse JSON if in json_mode
            structured_output = None
            if json_mode:
                try:
                    structured_output = json.loads(content)
                except json.JSONDecodeError:
                    structured_output = self._extract_json(content)

            return AgentResponse(
                agent_id=self._agent_id,
                content=content,
                structured_output=structured_output,
                tokens_used=tokens,
                duration_ms=duration_ms,
                success=True,
            )

        except Exception as e:
            logger.error(f"LLM call failed for {self._agent_id} after retries: {e}")
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            return AgentResponse(
                agent_id=self._agent_id,
                content="",
                success=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def call_llm_json(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Call LLM and get JSON response.

        Args:
            prompt: User prompt
            context: Optional context to include

        Returns:
            Parsed JSON dict
        """
        full_prompt = prompt
        if context:
            full_prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        messages = [AgentMessage(role="user", content=full_prompt)]
        response = await self.call_llm(messages, json_mode=True)

        return response.structured_output or {}

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from text that may contain extra content."""
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

        logger.warning("Could not extract JSON from response")
        return {}

    # ==========================================================================
    # Conversation Management
    # ==========================================================================

    def add_message(self, message: AgentMessage) -> None:
        """Add a message to conversation history."""
        self._conversation_history.append(message)

    def get_history(self) -> list[AgentMessage]:
        """Get conversation history."""
        return self._conversation_history.copy()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()

    def get_recent_messages(self, count: int = 10) -> list[AgentMessage]:
        """Get recent messages from history."""
        return self._conversation_history[-count:]

    # ==========================================================================
    # Memory Integration
    # ==========================================================================

    def to_packet_payload(self, response: AgentResponse) -> dict[str, Any]:
        """
        Convert response to memory packet payload.

        Args:
            response: Agent response

        Returns:
            Payload for PacketEnvelopeIn
        """
        return {
            "kind": "agent_response",
            "agent_id": self._agent_id,
            "agent_role": self.agent_role.value,
            "response_id": str(response.response_id),
            "success": response.success,
            "tokens_used": response.tokens_used,
            "duration_ms": response.duration_ms,
            "content_length": len(response.content),
        }

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    def format_user_message(self, content: str) -> AgentMessage:
        """Create a user message."""
        return AgentMessage(role="user", content=content)

    def format_assistant_message(self, content: str) -> AgentMessage:
        """Create an assistant message."""
        return AgentMessage(role="assistant", content=content)

    async def health_check(self) -> dict[str, Any]:
        """Check agent health."""
        try:
            response = await self.call_llm(
                [AgentMessage(role="user", content="Reply with 'ok'")],
                temperature=0,
            )
            return {
                "status": "healthy" if response.success else "unhealthy",
                "agent_id": self._agent_id,
                "model": self._config.model,
                "error": response.error,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "agent_id": self._agent_id,
                "error": str(e),
            }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-003",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "core.resilience.retry"],
    "tags": [
        "api",
        "async",
        "data-models",
        "dataclass",
        "intelligence",
        "llm",
        "logging",
        "messaging",
        "serialization",
    ],
    "keywords": [
        "agent",
        "agents",
        "assistant",
        "check",
        "clear",
        "format",
        "health",
        "history",
    ],
    "business_value": "LLM client management with retry logic Message handling Memory integration Standard interfaces Version: 2.0.0 Added retry logic with exponential backoff (uses AgentConfig.retry_count)",
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
