"""
L9 Research Factory - Base Agent
Version: 1.0.0

Shared LLM wrapper and utilities for all research agents.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Base Agent",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "research_services",
    "module_name": "base_agent",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": [
            "services.research.agents.__init__",
            "services.research.agents.critic_agent",
            "services.research.agents.planner_agent",
            "services.research.agents.researcher_agent",
        ],
    },
}
# ============================================================================

import json
from abc import ABC, abstractmethod
from typing import Any, Optional

import structlog
from openai import AsyncOpenAI

from config.research_settings import get_research_settings
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """
    Base class for all research agents.

    Provides:
    - LLM client initialization
    - Chat completion wrapper
    - Response parsing utilities
    - Logging integration
    """

    def __init__(
        self,
        agent_id: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize base agent.

        Args:
            agent_id: Unique identifier for this agent
            model: LLM model to use (defaults to settings)
            temperature: LLM temperature (defaults to settings)
        """
        self.agent_id = agent_id

        settings = get_research_settings()
        self.model = model or settings.openai_model
        self.temperature = (
            temperature if temperature is not None else settings.research_temperature
        )

        # Initialize OpenAI client
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

        logger.info(f"Initialized {self.__class__.__name__} with model={self.model}")

    async def call_llm(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: int = 2000,
        response_format: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Call the LLM with messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override temperature for this call
            max_tokens: Maximum tokens in response
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            Generated text response
        """
        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": (
                    temperature if temperature is not None else self.temperature
                ),
                "max_tokens": max_tokens,
            }

            if response_format:
                kwargs["response_format"] = response_format

            response = await self._client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content or ""

            logger.debug(f"LLM response for {self.agent_id}: {len(content)} chars")
            return content

        except Exception as e:
            logger.error(f"LLM call failed for {self.agent_id}: {e}")
            raise

    async def call_llm_json(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """
        Call LLM and parse JSON response.

        Args:
            messages: List of message dicts
            temperature: Override temperature
            max_tokens: Maximum tokens

        Returns:
            Parsed JSON dict
        """
        response = await self.call_llm(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {self.agent_id}: {e}")
            # Try to extract JSON from response
            return self._extract_json(response)

    def _extract_json(self, text: str) -> dict[str, Any]:
        """
        Attempt to extract JSON from text that may contain extra content.

        Args:
            text: Text that may contain JSON

        Returns:
            Extracted JSON dict, or empty dict on failure
        """
        # Try to find JSON object in text
        try:
            # Find first { and last }
            start = text.find("{")
            end = text.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        logger.warning("Could not extract JSON from response, returning empty dict")
        return {}

    @abstractmethod
    @must_stay_async("callers use await")
    async def run(self, *args, **kwargs) -> Any:
        """
        Execute the agent's primary function.

        Must be implemented by subclasses.
        """

    def format_system_prompt(self, instructions: str) -> dict[str, str]:
        """Create a system message."""
        return {"role": "system", "content": instructions}

    def format_user_prompt(self, content: str) -> dict[str, str]:
        """Create a user message."""
        return {"role": "user", "content": content}

    def format_assistant_prompt(self, content: str) -> dict[str, str]:
        """Create an assistant message."""
        return {"role": "assistant", "content": content}


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-010",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "adapter",
        "api",
        "async",
        "debugging",
        "llm",
        "logging",
        "messaging",
        "operations",
        "research-services",
        "serialization",
    ],
    "keywords": [
        "agent",
        "assistant",
        "format",
        "json",
        "llm",
        "prompt",
        "research",
        "system",
    ],
    "business_value": "Implements BaseAgent for base agent functionality",
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
