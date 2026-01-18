"""
Gmail OAuth Credentials Handler
===============================

Handles OAuth2 flow for Gmail API authentication.
Supports multi-account mode (igor, l) with backward compatibility.

Version: 2.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Credentials",
    "module_version": "2.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "integration",
    "domain": "email_integration",
    "module_name": "credentials",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "email_agent.__init__",
            "email_agent.gmail_client",
            "email_agent.oauth_server",
        ],
    },
}
# ============================================================================

import json
import structlog
from typing import Optional, Dict, Any

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    GMAIL_AUTH_AVAILABLE = True
except ImportError:
    GMAIL_AUTH_AVAILABLE = False
    Credentials = None  # Type hint placeholder
    structlog.get_logger(__name__).warning("Gmail OAuth libraries not available")

from email_agent.config import (
    TOKENS_FILE,
    CLIENT_SECRET_FILE,
    SCOPES,
    ensure_dirs,
    get_account_config,
)

logger = structlog.get_logger(__name__)

# Ensure legacy directories exist on import
ensure_dirs()


def load_client_secrets(account: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Load OAuth client secrets.

    Args:
        account: Account name ("igor" or "l"). If None, uses legacy path.

    Returns:
        Client secrets dictionary or None if not found
    """
    if account:
        config = get_account_config(account)
        secret_file = config.client_secret_file
    else:
        secret_file = CLIENT_SECRET_FILE  # Legacy

    if not secret_file.exists():
        logger.error(f"Client secrets not found at {secret_file}")
        if account:
            logger.info("Run: python scripts/setup_gmail_accounts.py")
        else:
            logger.info("Please download OAuth2 credentials from Google Cloud Console")
            logger.info("Save as: ~/.l9/gmail/client_secret.json")
        return None

    try:
        with open(secret_file, "r") as f:
            secrets = json.load(f)
        logger.info(f"Loaded client secrets from {secret_file}")
        return secrets
    except Exception as e:
        logger.error(f"Failed to load client secrets: {e}")
        return None


def create_flow(
    redirect_uri: Optional[str] = None, account: Optional[str] = None
) -> Optional[Any]:
    """
    Create OAuth2 flow for Gmail authentication.

    Args:
        redirect_uri: Optional redirect URI (defaults to localhost)
        account: Account name ("igor" or "l"). If None, uses legacy path.

    Returns:
        InstalledAppFlow instance or None if client secrets not found
    """
    if not GMAIL_AUTH_AVAILABLE:
        logger.error("Gmail OAuth libraries not available")
        return None

    secrets = load_client_secrets(account)
    if not secrets:
        return None

    # Determine secret file path
    if account:
        config = get_account_config(account)
        secret_file = config.client_secret_file
    else:
        secret_file = CLIENT_SECRET_FILE

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(secret_file), SCOPES, redirect_uri=redirect_uri
        )
        return flow
    except Exception as e:
        logger.error(f"Failed to create OAuth flow: {e}")
        return None


def exchange_code_for_tokens(
    authorization_code: str, redirect_uri: str, account: Optional[str] = None
) -> Optional[Credentials]:
    """
    Exchange authorization code for access/refresh tokens.

    Args:
        authorization_code: Authorization code from OAuth callback
        redirect_uri: Redirect URI used in OAuth flow
        account: Account name ("igor" or "l"). If None, uses legacy path.

    Returns:
        Credentials object or None if exchange failed
    """
    if not GMAIL_AUTH_AVAILABLE:
        logger.error("Gmail OAuth libraries not available")
        return None

    try:
        flow = create_flow(redirect_uri=redirect_uri, account=account)
        if not flow:
            return None

        # Exchange code for tokens
        flow.fetch_token(code=authorization_code)
        credentials = flow.credentials

        # Save tokens
        save_tokens(credentials, account)

        account_label = account or "legacy"
        logger.info(
            f"Successfully exchanged authorization code for tokens (account={account_label})"
        )
        return credentials
    except Exception as e:
        logger.error(f"Failed to exchange code for tokens: {e}")
        return None


def save_tokens(credentials: Credentials, account: Optional[str] = None) -> bool:
    """
    Save OAuth tokens.

    Args:
        credentials: Credentials object with tokens
        account: Account name ("igor" or "l"). If None, uses legacy path.

    Returns:
        True if saved successfully
    """
    if not GMAIL_AUTH_AVAILABLE:
        logger.error("Gmail OAuth libraries not available")
        return False

    # Determine tokens file path
    if account:
        config = get_account_config(account)
        tokens_file = config.tokens_file
        # Ensure account directory exists
        config.data_root.mkdir(parents=True, exist_ok=True)
    else:
        tokens_file = TOKENS_FILE  # Legacy

    try:
        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
        }

        with open(tokens_file, "w") as f:
            json.dump(token_data, f, indent=2)

        logger.info(f"Saved tokens to {tokens_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save tokens: {e}")
        return False


def load_tokens(account: Optional[str] = None) -> Optional[Credentials]:
    """
    Load OAuth tokens.

    Args:
        account: Account name ("igor" or "l"). If None, uses legacy path.

    Returns:
        Credentials object or None if not found/invalid
    """
    if not GMAIL_AUTH_AVAILABLE:
        logger.error("Gmail OAuth libraries not available")
        return None

    # Determine tokens file path
    if account:
        config = get_account_config(account)
        tokens_file = config.tokens_file
    else:
        tokens_file = TOKENS_FILE  # Legacy

    if not tokens_file.exists():
        account_label = account or "legacy"
        logger.info(f"No tokens found at {tokens_file} (account={account_label})")
        return None

    try:
        with open(tokens_file, "r") as f:
            token_data = json.load(f)

        credentials = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get(
                "token_uri", "https://oauth2.googleapis.com/token"
            ),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", SCOPES),
        )

        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            logger.info("Tokens expired, refreshing...")
            credentials.refresh(Request())
            save_tokens(credentials, account)

        logger.info(f"Loaded tokens from {tokens_file}")
        return credentials
    except Exception as e:
        logger.error(f"Failed to load tokens: {e}")
        return None


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
        "email-integration",
        "integration",
        "logging",
        "security",
        "serialization",
        "utility",
    ],
    "keywords": [
        "client",
        "create",
        "credentials",
        "exchange",
        "flow",
        "gmail",
        "handler",
        "load",
    ],
    "business_value": "Handles OAuth2 flow for Gmail API authentication. Supports multi-account mode (igor, l) with backward compatibility. Version: 2.0.0",
    "last_modified": "2026-01-14T15:03:00Z",
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
