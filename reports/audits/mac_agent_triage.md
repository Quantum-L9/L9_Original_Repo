# Dead Code Triage: `mac_agent`

**Date:** 2026-02-14 05:42 UTC

## Symbol Classification

**USED** (3): `AgentConfig`, `AutomationExecutor`, `EventType`
**ZERO_REF** (2): `MacAgentClient`, `TaskExecutor`

## File Classification

**WIRED** (1):
- `mac_agent/executor.py`
**INTERNAL_ONLY** (1):
- `mac_agent/config.py`
**ASPIRATIONAL** (2):
- `mac_agent/runner.py`
- `mac_agent/websocket_client.py`

## Recommended Actions

### Review 2 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.
