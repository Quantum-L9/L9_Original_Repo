"""
L9 Research Factory - Configuration Settings
Version: 1.0.0

Pydantic settings for the Research Factory service.
Uses the Memory Substrate for persistence (no separate DB connection).
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class ResearchSettings(BaseSettings):
    """
    Configuration for the L9 Research Factory.

    Environment variables:
    - OPENAI_API_KEY: Required for LLM calls
    - OPENAI_MODEL: Model to use for agents (default: gpt-4-turbo)
    - RESEARCH_TEMPERATURE: LLM temperature for research (default: 0.0)
    - MAX_PARALLEL_RESEARCHERS: Parallel research workers (default: 3)
    - RESEARCH_TIMEOUT_SECONDS: Timeout per research step (default: 120)
    - CRITIC_THRESHOLD: Quality threshold for approval (default: 0.7)
    - MAX_RETRIES: Maximum retry attempts (default: 2)
    """

    # LLM Configuration
    openai_api_key: str = Field(
        ..., alias="OPENAI_API_KEY", description="OpenAI API key for LLM calls"
    )
    openai_model: str = Field(
        default="gpt-4-turbo",
        alias="OPENAI_MODEL",
        description="Model to use for research agents",
    )
    research_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        alias="RESEARCH_TEMPERATURE",
        description="Temperature for research LLM calls",
    )

    # Research Configuration
    max_parallel_researchers: int = Field(
        default=3,
        ge=1,
        le=10,
        alias="MAX_PARALLEL_RESEARCHERS",
        description="Maximum parallel research workers",
    )
    research_timeout_seconds: int = Field(
        default=120,
        ge=10,
        le=600,
        alias="RESEARCH_TIMEOUT_SECONDS",
        description="Timeout per research step",
    )
    critic_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        alias="CRITIC_THRESHOLD",
        description="Quality threshold for critic approval",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        alias="MAX_RETRIES",
        description="Maximum retry attempts on failure",
    )

    # Agent identifiers (for memory substrate tracking)
    planner_agent_id: str = Field(
        default="research_planner",
        alias="PLANNER_AGENT_ID",
        description="Agent ID for planner in substrate",
    )
    researcher_agent_id: str = Field(
        default="research_worker",
        alias="RESEARCHER_AGENT_ID",
        description="Agent ID for researcher in substrate",
    )
    critic_agent_id: str = Field(
        default="research_critic",
        alias="CRITIC_AGENT_ID",
        description="Agent ID for critic in substrate",
    )

    # Perplexity API (optional, for web research)
    perplexity_api_key: Optional[str] = Field(
        default=None,
        alias="PERPLEXITY_API_KEY",
        description="Perplexity API key for web research",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache(maxsize=1)
def get_research_settings() -> ResearchSettings:
    """Get or create research settings singleton. CACHED."""
    return ResearchSettings()


def reset_research_settings() -> None:
    """Reset settings (useful for testing)."""
    get_research_settings.cache_clear()
