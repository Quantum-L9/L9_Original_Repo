"""
Email Agent Configuration
=========================

Centralized configuration for Gmail agent paths and settings.
Supports multi-account mode (igor, l) with backward compatibility.

Version: 2.0.0
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

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
ACCOUNTS: Dict[str, AccountConfig] = {
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

# Base data root
GMAIL_DATA_ROOT = Path(os.path.expanduser("~/.l9/gmail"))

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


def ensure_dirs(account: Optional[str] = None):
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
    else:
        # Legacy mode
        GMAIL_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
        return {
            "gmail_data_root": str(GMAIL_DATA_ROOT),
            "tokens_file": str(TOKENS_FILE),
            "client_secret_file": str(CLIENT_SECRET_FILE),
            "attachments_dir": str(ATTACHMENTS_DIR),
        }
