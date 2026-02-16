#!/usr/bin/env python3
"""
Setup Gmail Multi-Account Configuration
=======================================

Copies OAuth credentials from gmail/ to account-specific directories
and validates configuration.

Usage:
    python scripts/setup_gmail_accounts.py

This script:
1. Creates account directories (~/.l9/gmail/igor/, ~/.l9/gmail/l/)
2. Copies OAuth client secrets from gmail/ to account directories
3. Reports status and next steps

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Setup Gmail Accounts",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-13T18:30:12Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "setup_gmail_accounts",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import shutil
import sys
from pathlib import Path

import structlog

# Add project root to path

logger = structlog.get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from email_agent.config import VALID_ACCOUNTS, get_account_config

# Gmail OAuth files in repo (private_auth folder)
GMAIL_REPO_DIR = PROJECT_ROOT / "email_agent" / "private_auth"


def setup_account(account_name: str) -> dict:
    """
    Setup credentials for one account.

    Args:
        account_name: Account name ("igor" or "l")

    Returns:
        Dict with status information
    """
    config = get_account_config(account_name)
    status = {
        "account": account_name,
        "email": config.email,
        "data_root": str(config.data_root),
        "client_secret_exists": False,
        "tokens_exist": False,
        "copied": False,
        "errors": [],
    }

    logger.info(
        "\n[account name] setting up at {config.data root}", account_name=account_name
    )

    # Create directories
    try:
        config.data_root.mkdir(parents=True, exist_ok=True)
        config.attachments_dir.mkdir(parents=True, exist_ok=True)
        logger.info("  + created directories")
    except Exception as e:
        status["errors"].append(f"Failed to create directories: {e}")
        logger.error("  ! error creating directories: e", e=e)
        return status

    # Copy client_secret from gmail/{account}/client_secret.json or gmail/google_oauth_{account}.json
    source_secret = GMAIL_REPO_DIR / f"google_oauth_{account_name}.json"
    dest_secret = config.client_secret_file

    if source_secret.exists():
        try:
            shutil.copy2(source_secret, dest_secret)
            status["copied"] = True
            status["client_secret_exists"] = True
            logger.info(
                "  + copied {source secret.name} -> dest secret",
                dest_secret=dest_secret,
            )
        except Exception as e:
            status["errors"].append(f"Failed to copy client secret: {e}")
            logger.error("  ! error copying client secret: e", e=e)
    elif dest_secret.exists():
        status["client_secret_exists"] = True
        logger.info(
            "  + client secret already exists: dest secret", dest_secret=dest_secret
        )
    else:
        status["errors"].append(f"Missing source: {source_secret}")
        logger.info("  ! missing source secret", source_secret=source_secret)
        print(
            f"    Expected: email_agent/private_auth/google_oauth_{account_name}.json"
        )

    # Check for tokens
    if config.tokens_file.exists():
        status["tokens_exist"] = True
        logger.info("  + tokens exist: {config.tokens_file}")
    else:
        logger.info("  - tokens missing: {config.tokens_file}")
        logger.info(
            "    run: python -m email agent.oauth server --account account name",
            account_name=account_name,
        )

    return status


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("gmail multi-account setup")
    logger.info("=" * 60)
    logger.info("\nproject root: project root", PROJECT_ROOT=PROJECT_ROOT)
    logger.info("gmail repo dir: gmail repo dir", GMAIL_REPO_DIR=GMAIL_REPO_DIR)
    logger.info("accounts: valid accounts", VALID_ACCOUNTS=VALID_ACCOUNTS)

    # Check gmail repo dir
    if not GMAIL_REPO_DIR.exists():
        logger.warning(
            "\n! warning: gmail repo directory not found: gmail repo dir",
            GMAIL_REPO_DIR=GMAIL_REPO_DIR,
        )
        logger.info("  oauth client secrets should be placed there.")

    # Setup each account
    results = []
    for account_name in VALID_ACCOUNTS:
        result = setup_account(account_name)
        results.append(result)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("summary")
    logger.info("=" * 60)

    all_ready = True
    need_oauth = []

    for result in results:
        account = result["account"]
        if result["client_secret_exists"] and result["tokens_exist"]:
            logger.info("  [account] ✅ ready", account=account)
        elif result["client_secret_exists"] and not result["tokens_exist"]:
            logger.info("  [account] ⚠️  need oauth flow", account=account)
            need_oauth.append(account)
            all_ready = False
        else:
            logger.info("  [account] ❌ missing client secret", account=account)
            all_ready = False

    # Next steps
    logger.info("\n" + "=" * 60)
    logger.info("next steps")
    logger.info("=" * 60)

    if all_ready:
        logger.info("\n✅ all accounts are configured!")
        logger.info("\ntest endpoints:")
        logger.info("  curl -x post http://localhost:8000/email/igor/query \\")
        logger.info('    -h "authorization: bearer $l9_executor_api_key" \\')
        logger.info('    -h "content-type: application/json" \\')
        logger.info('    -d \'{"query": "is:unread", "max_results": 5}\'')
    else:
        if need_oauth:
            logger.info("\n1. run oauth flow for accounts needing tokens:")
            for account in need_oauth:
                logger.info(
                    "   python -m email agent.oauth server --account account",
                    account=account,
                )
                logger.info("   then visit: http://localhost:8080/oauth/start")
        missing_secrets = [r for r in results if not r["client_secret_exists"]]
        if missing_secrets:
            logger.info("\n2. add missing oauth client secrets:")
            for result in missing_secrets:
                print(
                    f"   - email_agent/private_auth/google_oauth_{result['account']}.json"
                )
            logger.info("\n   get these from google cloud console:")
            logger.info("   https://console.cloud.google.com/apis/credentials")

        logger.info("\n3. after oauth, test endpoints:")
        logger.info("   curl -x post http://localhost:8000/email/igor/query \\")
        logger.info('     -h "authorization: bearer $l9_executor_api_key" \\')
        logger.info('     -h "content-type: application/json" \\')
        logger.info('     -d \'{"query": "is:unread", "max_results": 5}\'')


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "cli",
        "filesystem",
        "operations",
        "scripts",
        "security",
        "testing",
    ],
    "keywords": ["account", "accounts", "gmail", "setup"],
    "business_value": "1. Creates account directories (~/.l9/gmail/igor/, ~/.l9/gmail/l/) 2. Copies OAuth client secrets from gmail/ to account directories 3. Reports status and next steps Version: 1.0.0",
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
