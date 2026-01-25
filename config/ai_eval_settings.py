"""
L9 AI Evaluation Settings
=========================

Pydantic settings for AI guardrails CI checks.
Environment variables prefixed with AI_EVAL_.

Usage:
    from config.ai_eval_settings import get_ai_eval_settings
    settings = get_ai_eval_settings()
"""
# Python 3.12+ required (L9 standard)

# ============================================================================
__dora_meta__ = {
    "component_name": "AI Eval Settings",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T00:00:00Z",
    "updated_at": "2026-01-25T00:00:00Z",
    "layer": "foundation",
    "domain": "configuration",
    "module_name": "ai_eval_settings",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": ["ci.ai_guardrails.runner"],
    },
}
# ============================================================================

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class HallucinationSettings(BaseSettings):
    """Hallucination detection settings."""

    enabled: bool = Field(default=True, description="Enable hallucination checks")
    confidence_threshold: float = Field(
        default=0.85, description="Minimum confidence score to pass"
    )
    kb_endpoint: str | None = Field(
        default=None,
        alias="AI_EVAL_KB_ENDPOINT",
        description="Knowledge base endpoint for fact verification",
    )
    use_kb_verification: bool = Field(
        default=False, description="Use KB for fact checking"
    )

    class Config:
        env_prefix = "AI_EVAL_HALLUCINATION_"


class BiasSettings(BaseSettings):
    """Bias detection settings."""

    enabled: bool = Field(default=True, description="Enable bias checks")
    sensitive_attributes: list[str] = Field(
        default=["gender", "ethnicity", "age", "disability_status"],
        description="Attributes to test for bias",
    )
    divergence_threshold: float = Field(
        default=0.2, description="Maximum allowed score divergence"
    )

    class Config:
        env_prefix = "AI_EVAL_BIAS_"


class EvalSettings(BaseSettings):
    """Golden dataset evaluation settings."""

    enabled: bool = Field(default=True, description="Enable evaluation suite")
    golden_dataset_path: str = Field(
        default="tests/ai/golden_set.jsonl", description="Path to golden dataset"
    )
    pass_rate_threshold: float = Field(
        default=0.90, description="Minimum pass rate to succeed"
    )
    grading_rubric: str = Field(
        default="semantic_match", description="Default grading rubric"
    )

    class Config:
        env_prefix = "AI_EVAL_EVAL_"


class SecuritySettings(BaseSettings):
    """Security check settings."""

    enabled: bool = Field(default=True, description="Enable security checks")
    prompt_injection_enabled: bool = Field(
        default=True, description="Enable prompt injection tests"
    )
    pii_scan_enabled: bool = Field(default=True, description="Enable PII scanning")
    pii_patterns: list[str] = Field(
        default=[
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{3}\b",  # Credit card
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        ],
        description="Regex patterns for PII detection",
    )

    class Config:
        env_prefix = "AI_EVAL_SECURITY_"


class AIEvalSettings(BaseSettings):
    """
    Master configuration for AI evaluation guardrails.

    All settings can be overridden via environment variables:
    - AI_EVAL_DRY_RUN=true
    - AI_EVAL_HALLUCINATION_ENABLED=false
    - etc.
    """

    # General
    dry_run: bool = Field(
        default=False,
        alias="AI_EVAL_DRY_RUN",
        description="Run without actual model calls",
    )
    verbose: bool = Field(
        default=False, alias="AI_EVAL_VERBOSE", description="Verbose output"
    )

    # Sub-settings (nested)
    hallucination: HallucinationSettings = Field(default_factory=HallucinationSettings)
    bias: BiasSettings = Field(default_factory=BiasSettings)
    eval: EvalSettings = Field(default_factory=EvalSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # Test case paths
    hallucination_cases_path: str = Field(
        default="tests/ai/hallucination_cases.yaml",
        description="Path to hallucination test cases",
    )
    bias_cases_path: str = Field(
        default="tests/ai/bias_cases.yaml", description="Path to bias test cases"
    )
    security_cases_path: str = Field(
        default="tests/ai/security_injection_cases.yaml",
        description="Path to security test cases",
    )

    class Config:
        env_prefix = "AI_EVAL_"
        env_nested_delimiter = "__"


@lru_cache
def get_ai_eval_settings() -> AIEvalSettings:
    """Get cached AI evaluation settings."""
    return AIEvalSettings()


def reset_ai_eval_settings() -> None:
    """Clear cached settings (for testing)."""
    get_ai_eval_settings.cache_clear()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CONFIG-FOUND-007",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["config", "ai", "evaluation", "guardrails", "ci"],
    "keywords": ["hallucination", "bias", "security", "eval", "settings"],
    "business_value": "Configuration for AI guardrails CI checks",
    "last_modified": "2026-01-25T00:00:00Z",
    "modified_by": "GMP-AI-CI",
    "change_summary": "Initial creation for AI guardrails integration",
}
# ============================================================================
