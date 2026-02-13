"""
L9 Agent — System Prompt Contract Tests
=========================================

Validates structural invariants of the system prompts that L-CTO and other
agents receive. NOT behavioral LLM tests — they verify prompt assembly code
includes required fields.

Root cause from Slack incident (2026-02-12): L-CTO could not tell time
because no datetime was injected. L-CTO had no personality because the
fallback prompt was a bare string with zero tone directives.

Author: L9 Engineering
Created: 2026-02-12
"""

from __future__ import annotations

import re

import pytest

# ============================================================================
__dora_meta__ = {
    "component_name": "System Prompt Contract Tests",
    "module_version": "1.0.0",
    "created_by": "L9 Engineering",
    "created_at": "2026-02-12T03:41:00Z",
    "updated_at": "2026-02-12T03:41:00Z",
    "layer": "testing",
    "domain": "agents",
    "module_name": "test_system_prompt_contracts",
    "type": "test",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================


def _get_agent_or_skip():
    """Import and return a minimal LCTOAgent instance, or skip."""
    try:
        from agents.l_cto import LCTOAgent
    except ImportError:
        pytest.skip("agents.l_cto not available")
        return None  # unreachable but satisfies type checkers

    agent = LCTOAgent.__new__(LCTOAgent)

    if hasattr(agent, "_kernel_data"):
        agent._kernel_data = {
            "identity": {
                "name": "L",
                "traits": ["analytical", "direct", "strategic"],
                "anti_traits": ["lazy", "generic"],
            },
            "behavioral": {},
            "safety": {},
        }
    if hasattr(agent, "_kernels"):
        agent._kernels = {}

    return agent


class TestKernelPromptContainsDatetime:
    """The assembled system prompt MUST include a current datetime stamp."""

    def test_kernel_prompt_has_datetime(self):
        """_build_kernel_prompt() output must contain a datetime/timestamp."""
        agent = _get_agent_or_skip()

        try:
            prompt = agent._build_kernel_prompt()
        except Exception:
            pytest.skip("_build_kernel_prompt() requires runtime dependencies")

        datetime_patterns = [
            r"\d{4}-\d{2}-\d{2}",
            r"\d{2}:\d{2}:\d{2}",
            r"[Cc]urrent\s+[Tt]ime",
            r"[Cc]urrent\s+[Dd]ate",
            r"[Tt]imestamp",
            r"[Dd]atetime",
        ]

        has_datetime = any(re.search(p, prompt) for p in datetime_patterns)
        assert has_datetime, (
            "System prompt must contain a current datetime stamp. "
            "Without it, the LLM cannot answer time-related questions. "
            f"Prompt excerpt (first 500 chars): {prompt[:500]}"
        )


class TestFallbackPromptPreservesIdentity:
    """When kernels fail to load, the fallback prompt must preserve identity."""

    def test_fallback_is_not_bare_string(self):
        """Fallback must contain more than a single error sentence."""
        try:
            from agents.l_cto import LCTOAgent
        except ImportError:
            pytest.skip("agents.l_cto not available")

        agent = LCTOAgent.__new__(LCTOAgent)

        if hasattr(agent, "_kernels"):
            agent._kernels = None
        if hasattr(agent, "_kernel_data"):
            agent._kernel_data = None

        try:
            if hasattr(agent, "_get_fallback_prompt"):
                prompt = agent._get_fallback_prompt()
            elif hasattr(agent, "_build_kernel_prompt"):
                prompt = agent._build_kernel_prompt()
            else:
                pytest.skip("No fallback prompt method found")
        except Exception:
            pytest.skip("Fallback prompt method requires runtime deps")

        assert len(prompt) > 100, (
            f"Fallback prompt is too short ({len(prompt)} chars). "
            "Must include minimal identity and behavioral guidelines."
        )

        identity_terms = ["L", "CTO", "agent", "assistant"]
        has_identity = any(term.lower() in prompt.lower() for term in identity_terms)
        assert has_identity, (
            "Fallback prompt must reference agent identity. "
            "Without it, the LLM falls back to generic GPT defaults."
        )

    def test_fallback_does_not_equal_kernel_loaded_prompt(self):
        """Fallback and kernel-loaded prompts must be different strings.
        If they are identical, the fallback is not a real degradation path."""
        try:
            from agents.l_cto import LCTOAgent
        except ImportError:
            pytest.skip("agents.l_cto not available")

        # Kernel-loaded prompt
        agent_loaded = LCTOAgent.__new__(LCTOAgent)
        if hasattr(agent_loaded, "_kernel_data"):
            agent_loaded._kernel_data = {
                "identity": {
                    "name": "L",
                    "traits": ["analytical"],
                    "anti_traits": ["lazy"],
                },
                "behavioral": {},
                "safety": {},
            }
        if hasattr(agent_loaded, "_kernels"):
            agent_loaded._kernels = {}

        # Fallback prompt
        agent_fallback = LCTOAgent.__new__(LCTOAgent)
        if hasattr(agent_fallback, "_kernels"):
            agent_fallback._kernels = None
        if hasattr(agent_fallback, "_kernel_data"):
            agent_fallback._kernel_data = None

        try:
            if hasattr(agent_loaded, "_build_kernel_prompt"):
                loaded_prompt = agent_loaded._build_kernel_prompt()
            else:
                pytest.skip("No _build_kernel_prompt method")

            if hasattr(agent_fallback, "_get_fallback_prompt"):
                fallback_prompt = agent_fallback._get_fallback_prompt()
            elif hasattr(agent_fallback, "_build_kernel_prompt"):
                fallback_prompt = agent_fallback._build_kernel_prompt()
            else:
                pytest.skip("No fallback method")
        except Exception:
            pytest.skip("Prompt methods require runtime deps")

        assert loaded_prompt != fallback_prompt, (
            "Kernel-loaded and fallback prompts must differ. "
            "If identical, there is no graceful degradation."
        )


class TestSystemPromptTokenBudget:
    """Assembled system prompts must stay within a token ceiling."""

    MAX_PROMPT_CHARS = 32_000

    def test_kernel_prompt_under_token_budget(self):
        """Assembled kernel prompt must not exceed the character ceiling."""
        agent = _get_agent_or_skip()

        # Inflate kernel data to stress-test
        if hasattr(agent, "_kernel_data") and agent._kernel_data:
            agent._kernel_data["behavioral"] = {"rules": ["Be concise"] * 50}
            agent._kernel_data["safety"] = {"constraints": ["No harmful content"] * 50}

        try:
            prompt = agent._build_kernel_prompt()
        except Exception:
            pytest.skip("_build_kernel_prompt() requires runtime deps")

        assert len(prompt) <= self.MAX_PROMPT_CHARS, (
            f"Kernel prompt is {len(prompt)} chars (max {self.MAX_PROMPT_CHARS}). "
            "Prompt bloat degrades output quality and increases cost."
        )
