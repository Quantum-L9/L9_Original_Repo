# Dead Code Triage: `email_agent`

**Date:** 2026-02-14 05:42 UTC

## Symbol Classification

**USED** (2): `GmailClient`, `execute_email_task`
**INTERNAL_ONLY** (3): `create_flow`, `exchange_code_for_tokens`, `load_tokens`
**TEST_ONLY** (1): `summarize_inbox`
**ZERO_REF** (3): `load_client_secrets`, `run_daily_digest`, `save_tokens`

## File Classification

**WIRED** (5):
- `email_agent/client.py`
- `email_agent/config.py`
- `email_agent/gmail_client.py`
- `email_agent/router.py`
- `email_agent/triage.py`
**INTERNAL_ONLY** (1):
- `email_agent/credentials.py`
**ASPIRATIONAL** (2):
- `email_agent/oauth_server.py`
- `email_agent/parser.py`

## Recommended Actions

### Remove 3 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Review 3 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.
