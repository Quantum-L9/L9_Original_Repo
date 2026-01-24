"""
L9 LLM Module

Unified LLM interfaces implementing the LLMService protocol.

Provides:
- OpenAILLMService: OpenAI GPT models (GPT-4, GPT-4o, GPT-3.5)
- AnthropicLLMService: Anthropic Claude models (future)
- MockLLMService: Testing implementation

Version: 1.0.0
GMP: GMP-116-llm-service-implementation
"""

from core.llm.llm_service import (
    MockLLMService,
    OpenAILLMService,
    create_llm_service,
    get_default_model,
)

__all__ = [
    "MockLLMService",
    "OpenAILLMService",
    "create_llm_service",
    "get_default_model",
]

__version__ = "1.0.0"
