# ADR 0008: Feature Flag Gating Pattern

## Status
Accepted

## Pattern
All experimental/legacy features gated by env vars; centralized in `config/settings.py`.

## Files
- `config/settings.py` - Centralized Settings class
- `api/server.py` - Flag usage at startup
- `.env` / `.env.example` - Flag definitions

## Active Feature Flags
| Flag | Default | Purpose |
|------|---------|---------|
| `L9_NEW_AGENT_INIT` | `true` | 7-phase bootstrap |
| `L9_USE_KERNELS` | `true` | Load kernel files |
| `L9_ENABLE_WS_ORCHESTRATOR` | `true` | WebSocket routing |
| `L9_STAGE3_MODULES` | `false` | Stage 3 memory modules |
| `L9_STAGE4_CONSOLIDATION` | `true` | Memory consolidation |
| `L9_GRAPH_WM_SYNC` | `false` | World model sync |
| `L9_OBSERVABILITY` | `true` | Prometheus metrics |
| `L9_SKIP_STARTUP_CHECKS` | `false` | Skip health checks |
| `GOVERNANCE_HARDENING_ENABLED` | `false` | Strict governance |
| `GOVERNANCE_ENFORCEMENT_MODE` | `log_only` | `log_only` or `enforce` |

## Usage Pattern
```python
# In config/settings.py
class Settings(BaseSettings):
    L9_NEW_AGENT_INIT: bool = True
    
# In code
from config.settings import settings

if settings.L9_NEW_AGENT_INIT:
    await bootstrap_agent(config, substrate)
else:
    agent = create_agent_legacy(config)
```

## Rollout Pattern
```
Phase 1: FEATURE_FLAG=false (off, code deployed)
Phase 2: FEATURE_FLAG=log_only (monitoring)
Phase 3: FEATURE_FLAG=true (enabled)
Phase 4: Remove flag (feature permanent)
```

## Rules
1. All new features MUST have a flag
2. Flags defined in `config/settings.py`
3. Default to `false` for risky features
4. Both branches (on/off) must be tested
5. Flag state logged at startup

## AI Guidance
**DO:**
- Add flag to `config/settings.py` Settings class
- Use `settings.FLAG_NAME` not `os.getenv()`
- Log flag state at startup
- Test both flag=true and flag=false

**DO NOT:**
- Hardcode feature availability
- Use `os.getenv()` directly for flags
- Skip testing the flag=false branch
- Remove flag without migration period
