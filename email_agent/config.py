"""
Email Agent Configuration
=========================

Centralized configuration for Gmail agent paths and settings.
Supports multi-account mode (igor, l) with backward compatibility.

Version: 2.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Config",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-13T13:58:04Z",
    "layer": "integration",
    "domain": "email_integration",
    "module_name": "config",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "email_agent.credentials",
            "email_agent.gmail_client",
            "email_agent.oauth_server",
            "email_agent.router",
            "scripts.setup_gmail_accounts",
            "tests.email_agent.test_email_router",
        ],
    },
}
# ============================================================================

import os
from dataclasses import dataclass
from pathlib import Path

# Feature flag for multi-account mode
L9_EMAIL_MULTI_ACCOUNT = os.getenv("L9_EMAIL_MULTI_ACCOUNT", "true").lower() == "true"


@dataclass
class AccountConfig:
    """Configuration for a Gmail account."""

    name: str
    email: str
    data_root: Path

    def __post_init__(self):
        """Validate and normalize config after initialization."""
        if isinstance(self.data_root, str):
            self.data_root = Path(self.data_root).expanduser()
        else:
            self.data_root = self.data_root.expanduser()
        if not self.name.isalnum():
            raise ValueError(f"Account name must be alphanumeric: {self.name}")

    @property
    def tokens_file(self) -> Path:
        """Path to tokens.json for this account."""
        return self.data_root / "tokens.json"

    @property
    def client_secret_file(self) -> Path:
        """Path to client_secret.json for this account."""
        return self.data_root / "client_secret.json"

    @property
    def attachments_dir(self) -> Path:
        """Path to attachments directory for this account."""
        return self.data_root / "attachments"


# Multi-account registry
ACCOUNTS: dict[str, AccountConfig] = {
    "igor": AccountConfig(
        name="igor",
        email="igor@quantumaipartners.com",
        data_root=Path("~/.l9/gmail/igor"),
    ),
    "l": AccountConfig(
        name="l",
        email="l@quantumaipartners.com",
        data_root=Path("~/.l9/gmail/l"),
    ),
}

# Valid account names for validation
VALID_ACCOUNTS = list(ACCOUNTS.keys())

# =============================================================================
# Legacy paths (backward compatibility)
# =============================================================================

# Base data root - respect L9_DATA_ROOT env var for containers
# Use /app/data in container environments (when /app exists), else use ~/.l9
if os.environ.get("L9_DATA_ROOT"):
    _data_root = os.environ["L9_DATA_ROOT"]
elif os.path.isdir("/app/data"):
    # Running in container - use container-safe path
    _data_root = "/app/data/.l9"
else:
    # Running locally - use home directory
    _data_root = os.path.expanduser("~/.l9")
GMAIL_DATA_ROOT = Path(_data_root) / "gmail"

# File paths
TOKENS_FILE = GMAIL_DATA_ROOT / "tokens.json"
CLIENT_SECRET_FILE = GMAIL_DATA_ROOT / "client_secret.json"
ATTACHMENTS_DIR = GMAIL_DATA_ROOT / "attachments"

# Gmail account (legacy)
GMAIL_ACCOUNT = "nc@scrapmanagement.com"

# Gmail API scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_account_config(account: str) -> AccountConfig:
    """
    Get account configuration by name.

    Args:
        account: Account name ("igor" or "l")

    Returns:
        AccountConfig for the specified account

    Raises:
        ValueError: If account name is not recognized
    """
    if account not in ACCOUNTS:
        raise ValueError(f"Unknown account: {account}. Valid: {VALID_ACCOUNTS}")
    return ACCOUNTS[account]


def ensure_dirs(account: str | None = None):
    """
    Ensure all required directories exist.
    Creates directories if they don't exist.

    Args:
        account: If provided, creates dirs for specific account.
                 If None, creates legacy dirs.

    Returns:
        Dict with path information
    """
    if account and account in ACCOUNTS:
        config = ACCOUNTS[account]
        config.data_root.mkdir(parents=True, exist_ok=True)
        config.attachments_dir.mkdir(parents=True, exist_ok=True)
        return {
            "gmail_data_root": str(config.data_root),
            "tokens_file": str(config.tokens_file),
            "client_secret_file": str(config.client_secret_file),
            "attachments_dir": str(config.attachments_dir),
        }
    # Legacy mode
    GMAIL_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "gmail_data_root": str(GMAIL_DATA_ROOT),
        "tokens_file": str(TOKENS_FILE),
        "client_secret_file": str(CLIENT_SECRET_FILE),
        "attachments_dir": str(ATTACHMENTS_DIR),
    }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "EMA-INTE-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "dataclass",
        "email-integration",
        "filesystem",
        "integration",
        "security",
    ],
    "keywords": [
        "account",
        "agent",
        "attachments",
        "client",
        "configuration",
        "dir",
        "dirs",
        "ensure",
    ],
    "business_value": "Implements AccountConfig for config functionality",
    "last_modified": "2026-01-13T13:58:04Z",
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
