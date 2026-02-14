# Package Wiring Audit: email_agent

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `email_agent`

Files checked: 8
- WIRED: 1
- PARTIAL: 5
- ORPHAN: 1
- ENTRYPOINT: 1
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `email_agent/client.py` | 2 | 0 | - | Y | OK |
| `email_agent/config.py` | 1 | 1 | - | - | PARTIAL |
| `email_agent/credentials.py` | 0 | 0 | - | Y | PARTIAL |
| `email_agent/gmail_client.py` | 0 | 1 | - | Y | PARTIAL |
| `email_agent/oauth_server.py` | 0 | 0 | - | - | ENTRY |
| `email_agent/parser.py` | 0 | 0 | - | - | ORPHAN |
| `email_agent/router.py` | 1 | 2 | Y | - | PARTIAL |
| `email_agent/triage.py` | 0 | 1 | Y | Y | PARTIAL |

## Level C: API Instantiation — `email_agent`

API Status: **HAS_API**
Symbols checked: 9
- USED: 2
- TEST_ONLY: 2
- UNUSED: 5

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `create_flow` | 0 | 0 | UNUSED |
| `exchange_code_for_tokens` | 0 | 0 | UNUSED |
| `load_client_secrets` | 0 | 0 | UNUSED |
| `load_tokens` | 0 | 1 | TEST_ONLY |
| `run_daily_digest` | 0 | 0 | UNUSED |
| `save_tokens` | 0 | 0 | UNUSED |
| `summarize_inbox` | 0 | 1 | TEST_ONLY |

**API-pattern symbols NOT in `__all__`:**
- `AccountConfig`
- `get_account_config`
- `get_email`
