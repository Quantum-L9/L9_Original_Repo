# Package Wiring Audit: mac_agent

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `mac_agent`

Files checked: 4
- WIRED: 0
- PARTIAL: 1
- ORPHAN: 1
- ENTRYPOINT: 2
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `mac_agent/config.py` | 0 | 0 | - | - | ORPHAN |
| `mac_agent/executor.py` | 1 | 1 | Y | - | PARTIAL |
| `mac_agent/runner.py` | 0 | 0 | - | - | ENTRY |
| `mac_agent/websocket_client.py` | 0 | 0 | - | - | ENTRY |

## Level C: API Instantiation — `mac_agent`

API Status: **HAS_API**
Symbols checked: 5
- USED: 3
- TEST_ONLY: 0
- UNUSED: 2

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `MacAgentClient` | 0 | 0 | UNUSED |
| `TaskExecutor` | 0 | 0 | UNUSED |

**API-pattern symbols NOT in `__all__`:**
- `MacAgentConfig`
- `create_error_event`
- `create_handshake`
- `create_heartbeat`
- `create_task_result`
- `get_config`
