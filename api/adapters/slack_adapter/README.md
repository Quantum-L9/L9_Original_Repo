# Slack Adapter — ARCHIVED

## Status: ARCHIVED (2026-01-08)

The **SlackWebhookAdapter (v2.6)** was generated but **never deployed** to this directory.

## Active Slack Implementation

Slack integration uses:

| File                     | Role                                                          |
| ------------------------ | ------------------------------------------------------------- |
| `api/routes/slack.py`    | FastAPI routes (`POST /slack/events`, `POST /slack/commands`) |
| `memory/slack_ingest.py` | Event orchestration, memory packets, L-CTO routing            |
| `api/slack_adapter.py`   | Utilities: `SlackRequestValidator`, `SlackRequestNormalizer`  |

## Archived Files

- `_archived/legacy_slack/webhook_slack.py` — Original 960-line legacy handler
- `_archived/codegen_slack_adapter/` — Generated v2.6 adapter (never deployed)

## Configuration

```bash
# Required
SLACK_SIGNING_SECRET=xoxb-...
SLACK_BOT_TOKEN=xoxb-...

# Feature Flags (in config/settings.py)
SLACK_APP_ENABLED=true                  # Master toggle
L9_ENABLE_LEGACY_SLACK_ROUTER=false     # Use L-CTO agent routing (recommended)
```

## Why Not v2.6?

The generated SlackWebhookAdapter was more complex than needed. The current
`api/routes/slack.py` + `memory/slack_ingest.py` combination provides:

- ✅ HMAC-SHA256 signature validation
- ✅ Packet emission to memory substrate
- ✅ L-CTO agent routing via `AgentExecutorService`
- ✅ Slash command support
- ✅ Rate limiting

The v2.6 adapter's additional features (dedupe cache, structured orchestration)
are partially implemented in `memory/slack_ingest.py` or deferred.
