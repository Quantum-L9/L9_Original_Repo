"""
L9 Unified Integration Toggle Settings
Version: 1.0.0

Centralized configuration for all external integrations.
All integrations can be toggled on/off via environment variables.
"""

import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class IntegrationSettings(BaseSettings):
    """
    Configuration for L9 external integrations.

    Environment variables:
    - SLACK_APP_ENABLED: Enable Slack integration (default: false)
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
        default=False, alias="EMAIL_ENABLED", description="Enable Email integration (legacy)"
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
    l9_enable_legacy_chat: bool = Field(
        default=False,
        alias="L9_ENABLE_LEGACY_CHAT",
        description="Enable legacy /chat route (direct OpenAI). Set False to disable.",
    )

    l9_enable_legacy_slack_router: bool = Field(
        default=False,
        alias="L9_ENABLE_LEGACY_SLACK_ROUTER",
        description="Enable legacy Slack routing. Set False to use AgentTask routing.",
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
    slack_app_id: Optional[str] = Field(
        default=None,
        alias="SLACK_APP_ID",
        description="Slack app ID (for future OAuth flows)",
    )

    slack_bot_token: Optional[str] = Field(
        default=None,
        alias="SLACK_BOT_TOKEN",
        description="Slack bot OAuth token (xoxb-...)",
    )

    slack_signing_secret: Optional[str] = Field(
        default=None,
        alias="SLACK_SIGNING_SECRET",
        description="Slack app signing secret for HMAC verification",
    )

    slack_client_id: Optional[str] = Field(
        default=None,
        alias="SLACK_CLIENT_ID",
        description="Slack OAuth client ID (for future OAuth flows)",
    )

    slack_client_secret: Optional[str] = Field(
        default=None,
        alias="SLACK_CLIENT_SECRET",
        description="Slack OAuth client secret (for future OAuth flows)",
    )

    slack_verification_token: Optional[str] = Field(
        default=None,
        alias="SLACK_VERIFICATION_TOKEN",
        description="Slack verification token (legacy, for future OAuth flows)",
    )

    class Config:
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
    global _settings
    _settings = None


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
