"""
L9 Unified Integration Toggle Settings
Version: 1.0.0

Centralized configuration for all external integrations.
All integrations can be toggled on/off via environment variables.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Settings",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "configuration",
    "module_name": "settings",
    "type": "schema",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Neo4j", "OpenAI API", "Slack API"],
        "memory_layers": [],
        "imported_by": [
            "_archived.legacy_slack.webhook_slack",
            "api.e2e_slack_audit",
            "api.server",
            "api.server_memory",
            "config.__init__",
            "mac_agent.runner",
            "memory.slack_ingest",
            "orchestrators.agent_execution.orchestrator",
            "services.slack_files",
            "tests.api.test_e2e_slack_audit",
        ],
    },
}
# ============================================================================

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class IntegrationSettings(BaseSettings):
    """
    Configuration for L9 external integrations.

    Environment variables:
    - SLACK_APP_ENABLED: Enable Slack integration (default: true)
    - MAC_AGENT_ENABLED: Enable Mac Agent integration (default: false)
    - EMAIL_ENABLED: Enable Email integration (default: false)
    - INBOX_PARSER_ENABLED: Enable Inbox Parser integration (default: false)
    - TWILIO_ENABLED: Enable Twilio integration (default: false)
    - WABA_ENABLED: Enable WABA integration (default: false)
    """

    # Integration toggles
    slack_app_enabled: bool = Field(
        default=True,
        alias="SLACK_APP_ENABLED",
        description="Enable Slack Events API integration",
    )

    mac_agent_enabled: bool = Field(
        default=True,
        alias="MAC_AGENT_ENABLED",
        description="Enable Mac Agent task execution",
    )

    email_enabled: bool = Field(
        default=False,
        alias="EMAIL_ENABLED",
        description="Enable Email integration (legacy)",
    )

    email_agent_enabled: bool = Field(
        default=True,
        alias="EMAIL_AGENT_ENABLED",
        description="Enable Email Agent (Gmail multi-account). Set False to disable.",
    )

    inbox_parser_enabled: bool = Field(
        default=False,
        alias="INBOX_PARSER_ENABLED",
        description="Enable Inbox Parser integration",
    )

    twilio_enabled: bool = Field(
        default=False,
        alias="TWILIO_ENABLED",
        description="Enable Twilio SMS/WhatsApp integration",
    )

    waba_enabled: bool = Field(
        default=False,
        alias="WABA_ENABLED",
        description="Enable WABA (WhatsApp Business Account) integration",
    )

    # Feature flags for legacy route migration
    # REMOVED: l9_enable_legacy_chat - legacy /chat endpoint deleted
    # REMOVED: l9_enable_legacy_slack_router - legacy Slack router deleted
    # All routing now uses AgentExecutorService via unified orchestrator

    # Feature flags for L9 runtime modules
    l9_new_agent_init: bool = Field(
        default=True,
        alias="L9_NEW_AGENT_INIT",
        description="Enable new agent initialization (v3.0+ paradigm shift).",
    )

    l9_stage3_modules: bool = Field(
        default=True,
        alias="L9_STAGE3_MODULES",
        description="Enable Stage 3 modules: Tool Audit, Event Queue, Virtual Context, Evaluator.",
    )

    l9_graph_agent_state: bool = Field(
        default=True,
        alias="L9_GRAPH_AGENT_STATE",
        description="Enable Stage 5: Graph-Backed Agent State (Neo4j for mutable agent state).",
    )

    l9_observability: bool = Field(
        default=True,
        alias="L9_OBSERVABILITY",
        description="Enable Five-Tier Observability (v3.3+ GMP-OBS-DEPLOY).",
    )

    l9_skip_startup_checks: bool = Field(
        default=False,
        alias="L9_SKIP_STARTUP_CHECKS",
        description="Skip startup checks (for container environments with broken symlinks).",
    )

    l9_stage4_consolidation: bool = Field(
        default=True,
        alias="L9_STAGE4_CONSOLIDATION",
        description="Enable Stage 4: Memory Consolidation (background cleanup).",
    )

    l9_consolidation_interval_hours: int = Field(
        default=4,
        alias="L9_CONSOLIDATION_INTERVAL_HOURS",
        description="Memory consolidation interval in hours.",
    )

    l9_graph_wm_sync: bool = Field(
        default=True,
        alias="L9_GRAPH_WM_SYNC",
        description="Enable UKG Phase 3: Graph to World Model Sync.",
    )

    l9_tool_pattern_extraction: bool = Field(
        default=True,
        alias="L9_TOOL_PATTERN_EXTRACTION",
        description="Enable UKG Phase 4: Tool Pattern Extraction (6h interval).",
    )

    l9_gmp_learning_enabled: bool = Field(
        default=False,
        alias="L9_GMP_LEARNING_ENABLED",
        description="Enable GMP v2.0 Meta-Learning Engine (requires migration 0021).",
    )

    l9_memory_warming_enabled: bool = Field(
        default=True,
        alias="L9_MEMORY_WARMING_ENABLED",
        description="Enable Stage 5: Predictive Memory Warming (gap detection + cache warming).",
    )

    # Dynamic Tool Discovery (GMP-78 Phase 2)
    l9_dynamic_tool_discovery: bool = Field(
        default=True,
        alias="L9_DYNAMIC_TOOL_DISCOVERY",
        description="Enable dynamic tool discovery: semantic search for relevant tools per-task instead of static binding.",
    )

    l9_tool_discovery_top_k: int = Field(
        default=5,
        alias="L9_TOOL_DISCOVERY_TOP_K",
        description="Maximum number of tools to discover per task (default: 5).",
    )

    l9_tool_discovery_min_similarity: float = Field(
        default=0.3,
        alias="L9_TOOL_DISCOVERY_MIN_SIMILARITY",
        description="Minimum cosine similarity threshold for tool discovery (default: 0.3).",
    )

    l9_tool_discovery_max_tokens: int = Field(
        default=2000,
        alias="L9_TOOL_DISCOVERY_MAX_TOKENS",
        description="Maximum tokens to allocate for discovered tools (default: 2000).",
    )

    l9_tool_cache_ttl: int = Field(
        default=300,
        alias="L9_TOOL_CACHE_TTL",
        description="TTL in seconds for cached tool discoveries (multi-turn, default: 300s/5min).",
    )

    # ------------------------------------------------------------------
    # Core Runtime Settings (ADR-0008 centralization)
    # ------------------------------------------------------------------
    l9_executor_api_key: str | None = Field(
        default=None,
        alias="L9_EXECUTOR_API_KEY",
        description="API key for L9 executor authentication.",
    )

    l9_llm_model: str = Field(
        default="gpt-4o",
        alias="L9_LLM_MODEL",
        description="Default LLM model for agent reasoning (gpt-4o, claude-3-opus, etc).",
    )

    l9_project_id: str = Field(
        default="l9-default",
        alias="L9_PROJECT_ID",
        description="Project identifier for multi-tenant deployments.",
    )

    l9_use_kernels: bool = Field(
        default=True,
        alias="L9_USE_KERNELS",
        description="Enable kernel stack loading from YAML files.",
    )

    l9_api_url: str = Field(
        default="http://localhost:8000",
        alias="L9_API_URL",
        description="Base URL for L9 API server.",
    )

    l9_memory_scope: str = Field(
        default="user",
        alias="L9_MEMORY_SCOPE",
        description="Memory scope: 'user', 'tenant', or 'global'.",
    )

    l9_repo_root: str = Field(
        default="",
        alias="L9_REPO_ROOT",
        description="Repository root path (auto-detected if not set).",
    )

    l9_env: str = Field(
        default="development",
        alias="L9_ENV",
        description="Environment: 'development', 'staging', or 'production'.",
    )

    l9_tenant_id: str = Field(
        default="73350468-3158-5d0f-9b8c-9b193d96fc4b",
        alias="L9_TENANT_ID",
        description="Default tenant UUID for RLS.",
    )

    # ------------------------------------------------------------------
    # Tool Feedback Learning (GMP-TFL-001)
    # ------------------------------------------------------------------
    l9_tool_feedback_enabled: bool = True
    l9_tool_exploration_rate: float = 0.1
    l9_tool_feedback_buffer_size: int = 50
    l9_tool_feedback_lookback_days: int = 30
    l9_tool_success_neutral_prior: float = 0.5
    l9_tool_alert_success_threshold: float = 0.5
    l9_tool_learning_daily_hour_utc: int = 2
    l9_tool_learning_daily_minute_utc: int = 0
    # ==========================================================================
    # Secrets Provider Configuration (GMP-122)
    # ==========================================================================

    l9_secrets_provider: str = Field(
        default="env",
        alias="L9_SECRETS_PROVIDER",
        description="Secrets provider: 'env' (default) or 'aws' (AWS Secrets Manager).",
    )

    aws_region: str = Field(
        default="us-east-1",
        alias="AWS_REGION",
        description="AWS region for Secrets Manager (default: us-east-1).",
    )

    aws_secrets_prefix: str = Field(
        default="l9",
        alias="AWS_SECRETS_PREFIX",
        description="Secret name prefix in AWS (default: l9).",
    )

    aws_secrets_cache_ttl: int = Field(
        default=3600,
        alias="AWS_SECRETS_CACHE_TTL",
        description="Cache TTL for secrets in seconds (default: 3600 = 1 hour).",
    )

    aws_secrets_fallback_to_env: bool = Field(
        default=True,
        alias="AWS_SECRETS_FALLBACK_TO_ENV",
        description="Fall back to env vars if AWS secret not found (default: True in non-prod).",
    )

    # Development mode
    local_dev: bool = Field(
        default=False,
        alias="LOCAL_DEV",
        description="Enable local development mode (relaxed validation).",
    )

    # Storage configuration
    l9_data_root: str = Field(
        default=os.path.expanduser("~/.l9"),
        alias="L9_DATA_ROOT",
        description="Root directory for L9 data storage",
    )

    slack_files_dir: str = Field(
        default="",  # Will be computed from l9_data_root
        alias="SLACK_FILES_DIR",
        description="Directory for Slack file storage (auto-computed if not set)",
    )

    # Slack-specific configuration
    slack_app_id: str | None = Field(
        default=None,
        alias="SLACK_APP_ID",
        description="Slack app ID (for future OAuth flows)",
    )

    slack_bot_token: str | None = Field(
        default=None,
        alias="SLACK_BOT_TOKEN",
        description="Slack bot OAuth token (xoxb-...)",
    )

    slack_signing_secret: str | None = Field(
        default=None,
        alias="SLACK_SIGNING_SECRET",
        description="Slack app signing secret for HMAC verification",
    )

    slack_client_id: str | None = Field(
        default=None,
        alias="SLACK_CLIENT_ID",
        description="Slack OAuth client ID (for future OAuth flows)",
    )

    slack_client_secret: str | None = Field(
        default=None,
        alias="SLACK_CLIENT_SECRET",
        description="Slack OAuth client secret (for future OAuth flows)",
    )

    slack_verification_token: str | None = Field(
        default=None,
        alias="SLACK_VERIFICATION_TOKEN",
        description="Slack verification token (legacy, for future OAuth flows)",
    )

    # Igor's Slack user ID for owner authentication
    igor_slack_user_id: str = Field(
        default="U0A3JGS0UCV",
        alias="IGOR_SLACK_USER_ID",
        description="Igor's Slack user ID for owner authentication and approval gates",
    )

    class Config:
        """
        Config class manages centralized external integration toggles via environment variables for the L9 Unified Integration system.

        Args:
            env_file: Path to the environment file containing configuration variables.
            env_file_encoding: Encoding used to read the environment file.
            case_sensitive: Whether environment variable names are case-sensitive.
            extra: Policy for handling unknown environment variables.

        Returns:
            An instance of Config with loaded settings for integration toggles.
        """

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Singleton instance
@lru_cache(maxsize=1)
def get_integration_settings() -> IntegrationSettings:
    """Get or create integration settings singleton. CACHED."""
    return IntegrationSettings()


def reset_integration_settings() -> None:
    """Reset settings (useful for testing)."""
    get_integration_settings.cache_clear()


# Convenience accessor
settings = get_integration_settings()


def get_slack_files_dir() -> str:
    """
    Get the Slack files directory path.

    Uses SLACK_FILES_DIR if set, otherwise computes from L9_DATA_ROOT.
    Directory structure: ~/.l9/slack_files/

    Returns:
        Absolute path to Slack files directory
    """
    integration_settings = get_integration_settings()

    # If explicitly set, use it
    if integration_settings.slack_files_dir:
        return os.path.abspath(os.path.expanduser(integration_settings.slack_files_dir))

    # Otherwise compute from L9_DATA_ROOT
    data_root = os.path.abspath(os.path.expanduser(integration_settings.l9_data_root))
    slack_files_dir = os.path.join(data_root, "slack_files")

    # Ensure directory exists
    Path(slack_files_dir).mkdir(parents=True, exist_ok=True)

    return slack_files_dir


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CON-FOUN-005",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "caching",
        "configuration",
        "event-driven",
        "filesystem",
        "foundation",
        "migration",
        "queue",
        "schema",
    ],
    "keywords": ["dir", "files", "integration", "integrations", "reset", "slack"],
    "business_value": "Provides settings components including IntegrationSettings, Config",
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
