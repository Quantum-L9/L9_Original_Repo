# L9 Slack Integration Architecture

## Overview

L9 Slack integration consists of two core modules with distinct responsibilities:

| Module            | Role                                    | Location               |
| ----------------- | --------------------------------------- | ---------------------- |
| **Configuration** | Credentials & feature flags             | `config/settings.py`   |
| **Adapter**       | Security verification & request parsing | `api/slack_adapter.py` |

---

## Module Responsibilities

### `config/settings.py` — Configuration Store

Pydantic model `IntegrationSettings` loads all Slack configuration from environment variables.

#### Feature Flags

| Setting                         | Env Var                         | Default | Description                          |
| ------------------------------- | ------------------------------- | ------- | ------------------------------------ |
| `slack_app_enabled`             | `SLACK_APP_ENABLED`             | `True`  | Enable/disable Slack integration     |
| `l9_enable_legacy_slack_router` | `L9_ENABLE_LEGACY_SLACK_ROUTER` | `False` | Use legacy AIOS routing vs AgentTask |

#### Credentials

| Setting                    | Env Var                    | Description                           |
| -------------------------- | -------------------------- | ------------------------------------- |
| `slack_signing_secret`     | `SLACK_SIGNING_SECRET`     | HMAC verification secret (required)   |
| `slack_bot_token`          | `SLACK_BOT_TOKEN`          | Bot OAuth token `xoxb-...` (required) |
| `slack_app_id`             | `SLACK_APP_ID`             | App ID from Slack dashboard           |
| `slack_client_id`          | `SLACK_CLIENT_ID`          | OAuth client ID (future)              |
| `slack_client_secret`      | `SLACK_CLIENT_SECRET`      | OAuth client secret (future)          |
| `slack_verification_token` | `SLACK_VERIFICATION_TOKEN` | Legacy token (deprecated)             |

#### Storage

| Setting           | Env Var           | Description                                                    |
| ----------------- | ----------------- | -------------------------------------------------------------- |
| `slack_files_dir` | `SLACK_FILES_DIR` | Directory for downloaded files (default: `~/.l9/slack_files/`) |

#### Usage

```python
from config.settings import get_integration_settings

settings = get_integration_settings()
signing_secret = settings.slack_signing_secret
bot_token = settings.slack_bot_token
```

---

### `api/slack_adapter.py` — Runtime Security & Parsing

Two classes handle request processing:

#### `SlackRequestValidator`

HMAC-SHA256 signature verification for webhook security.

```python
from api.slack_adapter import SlackRequestValidator

validator = SlackRequestValidator(signing_secret)
is_valid, error = validator.verify(
    request_body=body,      # Raw bytes
    timestamp_str=ts,       # X-Slack-Request-Timestamp header
    signature=sig,          # X-Slack-Signature header
)

if not is_valid:
    return Response(status_code=401, content=error)
```

**Security Features:**

- HMAC-SHA256 with Slack signing secret
- 300-second timestamp tolerance (replay attack prevention)
- Constant-time comparison (timing attack prevention)
- Fail-closed: invalid/missing signatures → 401

#### `SlackRequestNormalizer`

Parses raw Slack payloads into normalized dictionaries.

```python
from api.slack_adapter import SlackRequestNormalizer

# For event_callback (messages, app_mentions)
normalized = SlackRequestNormalizer.parse_event_callback(payload)
# Returns: team_id, channel_id, user_id, text, thread_uuid, event_type, ...

# For slash commands
normalized = SlackRequestNormalizer.parse_command(payload)
# Returns: team_id, channel_id, user_id, command, text, response_url, ...
```

**Normalization Features:**

- Extracts common fields from different event types
- Generates deterministic UUID v5 for threads (`thread_uuid`)
- Detects channel type (public/private/DM) from prefix
- Preserves raw event for audit trail

---

## Request Flow

```
Slack Event/Command
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  api/routes/slack.py                                        │
│                                                             │
│  1. Load configuration                                      │
│     settings = get_integration_settings()                   │
│     signing_secret = settings.slack_signing_secret          │
│                                                             │
│  2. Verify signature                                        │
│     validator = SlackRequestValidator(signing_secret)       │
│     is_valid, error = validator.verify(body, ts, sig)       │
│     if not is_valid: return 401                             │
│                                                             │
│  3. Normalize payload                                       │
│     normalized = SlackRequestNormalizer.parse_event_callback│
│                                                             │
│  4. Route to handler                                        │
│     → memory/slack_ingest.py (event processing)             │
│     → orchestration/slack_task_router.py (LLM routing)      │
└─────────────────────────────────────────────────────────────┘
```

---

## Related Modules

| Module                               | Purpose                                         |
| ------------------------------------ | ----------------------------------------------- |
| `api/routes/slack.py`                | FastAPI route handlers                          |
| `api/slack_client.py`                | Outbound Slack API client                       |
| `memory/slack_ingest.py`             | Event handler orchestration, memory integration |
| `orchestration/slack_task_router.py` | LLM-based task classification                   |
| `telemetry/slack_metrics.py`         | Prometheus metrics                              |

---

## Environment Setup

Required environment variables:

```bash
# Required
SLACK_SIGNING_SECRET=your_signing_secret
SLACK_BOT_TOKEN=xoxb-your-bot-token

# Optional
SLACK_APP_ID=A0A3MLBJ55Y
SLACK_BOT_USER_ID=U...          # For bot message filtering
SLACK_APP_ENABLED=true          # Default: true
L9_ENABLE_LEGACY_SLACK_ROUTER=false  # Default: false
```

---

## Testing

Run the E2E Slack audit:

```bash
pytest tests/api/test_e2e_slack_audit.py -v
```

Or standalone:

```bash
python -m tests.api.test_e2e_slack_audit
```

---

## Thread UUID Generation

Slack threads are identified by a deterministic UUID v5:

```python
# Namespace: uuid5(NAMESPACE_DNS, "slack.l9.internal")
# Input: "{team_id}:{channel_id}:{thread_ts}"
# Output: Consistent UUID for same thread across requests

thread_uuid = SlackRequestNormalizer._generate_thread_uuid(
    team_id="T123",
    channel_id="C456",
    thread_ts="1234567890.123456"
)
# → "408e0483-..."  (same every time for same inputs)
```

This enables:

- Deduplication of duplicate events
- Thread context retrieval from memory
- Consistent lineage tracking
