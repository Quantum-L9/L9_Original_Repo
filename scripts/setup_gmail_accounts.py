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

# Add project root to path
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

    print(f"\n[{account_name}] Setting up at {config.data_root}")

    # Create directories
    try:
        config.data_root.mkdir(parents=True, exist_ok=True)
        config.attachments_dir.mkdir(parents=True, exist_ok=True)
        print("  + Created directories")
    except Exception as e:
        status["errors"].append(f"Failed to create directories: {e}")
        print(f"  ! Error creating directories: {e}")
        return status

    # Copy client_secret from gmail/{account}/client_secret.json or gmail/google_oauth_{account}.json
    source_secret = GMAIL_REPO_DIR / f"google_oauth_{account_name}.json"
    dest_secret = config.client_secret_file

    if source_secret.exists():
        try:
            shutil.copy2(source_secret, dest_secret)
            status["copied"] = True
            status["client_secret_exists"] = True
            print(f"  + Copied {source_secret.name} -> {dest_secret}")
        except Exception as e:
            status["errors"].append(f"Failed to copy client secret: {e}")
            print(f"  ! Error copying client secret: {e}")
    elif dest_secret.exists():
        status["client_secret_exists"] = True
        print(f"  + Client secret already exists: {dest_secret}")
    else:
        status["errors"].append(f"Missing source: {source_secret}")
        print(f"  ! Missing {source_secret}")
        print(
            f"    Expected: email_agent/private_auth/google_oauth_{account_name}.json"
        )

    # Check for tokens
    if config.tokens_file.exists():
        status["tokens_exist"] = True
        print(f"  + Tokens exist: {config.tokens_file}")
    else:
        print(f"  - Tokens missing: {config.tokens_file}")
        print(f"    Run: python -m email_agent.oauth_server --account {account_name}")

    return status


def main():
    """Main entry point."""
    print("=" * 60)
    print("Gmail Multi-Account Setup")
    print("=" * 60)
    print(f"\nProject root: {PROJECT_ROOT}")
    print(f"Gmail repo dir: {GMAIL_REPO_DIR}")
    print(f"Accounts: {VALID_ACCOUNTS}")

    # Check gmail repo dir
    if not GMAIL_REPO_DIR.exists():
        print(f"\n! Warning: Gmail repo directory not found: {GMAIL_REPO_DIR}")
        print("  OAuth client secrets should be placed there.")

    # Setup each account
    results = []
    for account_name in VALID_ACCOUNTS:
        result = setup_account(account_name)
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_ready = True
    need_oauth = []

    for result in results:
        account = result["account"]
        if result["client_secret_exists"] and result["tokens_exist"]:
            print(f"  [{account}] ✅ Ready")
        elif result["client_secret_exists"] and not result["tokens_exist"]:
            print(f"  [{account}] ⚠️  Need OAuth flow")
            need_oauth.append(account)
            all_ready = False
        else:
            print(f"  [{account}] ❌ Missing client secret")
            all_ready = False

    # Next steps
    print("\n" + "=" * 60)
    print("Next Steps")
    print("=" * 60)

    if all_ready:
        print("\n✅ All accounts are configured!")
        print("\nTest endpoints:")
        print("  curl -X POST http://localhost:8000/email/igor/query \\")
        print('    -H "Authorization: Bearer $L9_EXECUTOR_API_KEY" \\')
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'{"query": "is:unread", "max_results": 5}\'')
    else:
        if need_oauth:
            print("\n1. Run OAuth flow for accounts needing tokens:")
            for account in need_oauth:
                print(f"   python -m email_agent.oauth_server --account {account}")
                print("   Then visit: http://localhost:8080/oauth/start")
                print()

        missing_secrets = [r for r in results if not r["client_secret_exists"]]
        if missing_secrets:
            print("\n2. Add missing OAuth client secrets:")
            for result in missing_secrets:
                print(
                    f"   - email_agent/private_auth/google_oauth_{result['account']}.json"
                )
            print("\n   Get these from Google Cloud Console:")
            print("   https://console.cloud.google.com/apis/credentials")

        print("\n3. After OAuth, test endpoints:")
        print("   curl -X POST http://localhost:8000/email/igor/query \\")
        print('     -H "Authorization: Bearer $L9_EXECUTOR_API_KEY" \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"query": "is:unread", "max_results": 5}\'')


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
