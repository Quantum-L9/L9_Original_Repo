# Slack Integration – L9 Subsystem README

> **Location:** `api/` (Slack-related files)
> **Status:** ✅ Production
> **Last Updated:** 2026-01-06
> **Owner:** L9 Core Team

---

## Subsystem Overview

The L9 Slack integration provides bidirectional communication between Slack workspaces and the L9 AI runtime. It handles inbound events (messages, mentions, commands) and outbound responses (replies in thread).

This integration fits into the larger L9 system as a **primary user interface** — the main way Igor and team interact with L9 agents via natural language.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SLACK WORKSPACE                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│  │ #l9-channel │   │ @L9 mention │   │  /l9 cmd    │   │   DM to L9  │      │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘      │
│         │                 │                 │                 │              │
│         └─────────────────┴─────────────────┴─────────────────┘              │
│                                    │                                         │
│                                    ▼                                         │
│                        ┌──────────────────────┐                              │
│                        │   Slack Events API   │                              │
│                        │   (webhook POST)     │                              │
│                        └──────────┬───────────┘                              │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    │ HTTPS POST to /slack/events
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              L9 API SERVER                                   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      api/routes/slack.py                                │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │ │
│  │  │ POST /slack/     │  │ POST /slack/     │  │ GET /slack/      │      │ │
│  │  │ events           │  │ commands         │  │ health           │      │ │
│  │  └────────┬─────────┘  └────────┬─────────┘  └──────────────────┘      │ │
│  │           │                     │                                       │ │
│  │           ▼                     ▼                                       │ │
│  │  ┌────────────────────────────────────────┐                             │ │
│  │  │         SIGNATURE VERIFICATION          │                             │ │
│  │  │    (HMAC-SHA256 via signing secret)     │                             │ │
│  │  └────────────────────┬───────────────────┘                             │ │
│  │                       │                                                  │ │
│  │                       ▼                                                  │ │
│  │  ┌────────────────────────────────────────┐                             │ │
│  │  │         api/slack_adapter.py            │                             │ │
│  │  │  ┌──────────────────────────────────┐  │                             │ │
│  │  │  │    SlackRequestValidator         │  │                             │ │
│  │  │  │    - verify(body, ts, sig)       │  │                             │ │
│  │  │  │    - HMAC-SHA256 comparison      │  │                             │ │
│  │  │  │    - 5-min timestamp tolerance   │  │                             │ │
│  │  │  └──────────────────────────────────┘  │                             │ │
│  │  │  ┌──────────────────────────────────┐  │                             │ │
│  │  │  │    SlackRequestNormalizer        │  │                             │ │
│  │  │  │    - parse_event_callback()      │  │                             │ │
│  │  │  │    - parse_command()             │  │                             │ │
│  │  │  │    - thread UUID generation      │  │                             │ │
│  │  │  └──────────────────────────────────┘  │                             │ │
│  │  └────────────────────────────────────────┘                             │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    memory/slack_ingest.py                               │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    SlackIngestService                             │  │ │
│  │  │  - Deduplication (idempotent processing)                         │  │ │
│  │  │  - Rate limiting (100 events/min per team)                       │  │ │
│  │  │  - Permission checks (channel allowlist)                         │  │ │
│  │  │  - Packet creation → Memory Substrate                            │  │ │
│  │  │  - AIOS runtime invocation                                       │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                          ┌─────────┴─────────┐                               │
│                          ▼                   ▼                               │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐   │
│  │    Memory Substrate         │  │         AIOS Runtime                 │   │
│  │  - PacketEnvelope storage   │  │  - Agent reasoning loop              │   │
│  │  - Neo4j event graph        │  │  - Tool dispatch                     │   │
│  │  - Thread context           │  │  - Response generation               │   │
│  └─────────────────────────────┘  └─────────────────┬───────────────────┘   │
│                                                      │                       │
│                                                      ▼                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      api/slack_client.py                                │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                      SlackAPIClient                               │  │ │
│  │  │  - post_message(channel, text, thread_ts)                        │  │ │
│  │  │  - Block Kit support                                              │  │ │
│  │  │  - Error handling                                                 │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     │ POST chat.postMessage
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SLACK WORKSPACE                                 │
│                                                                              │
│                        ┌──────────────────────┐                              │
│                        │   Reply in Thread    │                              │
│                        │   (L9 response)      │                              │
│                        └──────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Responsibilities and Boundaries

### ✅ Supported Responsibilities

| Responsibility                               | Owner File               |
| -------------------------------------------- | ------------------------ |
| Webhook signature verification (HMAC-SHA256) | `api/slack_adapter.py`   |
| Request normalization (events, commands)     | `api/slack_adapter.py`   |
| Rate limiting (per-team)                     | `memory/slack_ingest.py` |
| Deduplication (idempotent event processing)  | `memory/slack_ingest.py` |
| Channel permission checks                    | `memory/slack_ingest.py` |
| Packet creation and memory storage           | `memory/slack_ingest.py` |
| Reply posting to Slack                       | `api/slack_client.py`    |
| Thread context management                    | `api/routes/slack.py`    |

### ❌ Explicit Non-Responsibilities

| Not Handled                | Why                                |
| -------------------------- | ---------------------------------- |
| Slack OAuth flow           | Handled by Slack app configuration |
| User identity management   | Uses Slack user IDs directly       |
| Workspace provisioning     | Manual setup required              |
| Interactive modals/buttons | Not implemented (future work)      |
| File uploads               | Not implemented                    |

### Dependencies

| Direction    | Dependency       | Purpose             |
| ------------ | ---------------- | ------------------- |
| **Inbound**  | Slack Events API | Receives webhooks   |
| **Outbound** | Slack Web API    | Posts messages      |
| **Internal** | Memory Substrate | Stores packets      |
| **Internal** | AIOS Runtime     | Agent reasoning     |
| **Internal** | Neo4j            | Event graph storage |

---

## Directory Layout

```
api/
├── routes/
│   └── slack.py          # FastAPI router (344 lines)
│                         # - POST /slack/events
│                         # - POST /slack/commands
│                         # - GET /slack/health
│
├── slack_adapter.py      # Request validation (296 lines)
│                         # - SlackRequestValidator
│                         # - SlackRequestNormalizer
│
├── slack_client.py       # Slack API client (146 lines)
│                         # - SlackAPIClient
│
└── server.py             # Wires slack_router

memory/
└── slack_ingest.py       # Business logic (742 lines)
                          # - SlackIngestService
                          # - Deduplication
                          # - Rate limiting
                          # - AIOS invocation
```

---

## Key Components

### `api/routes/slack.py` (Router)

The FastAPI router handling all Slack endpoints.

| Endpoint          | Method | Purpose                           |
| ----------------- | ------ | --------------------------------- |
| `/slack/events`   | POST   | Receive Slack Events API webhooks |
| `/slack/commands` | POST   | Handle `/l9` slash commands       |
| `/slack/health`   | GET    | Health check for monitoring       |

**Key behaviors:**

- URL verification challenge response (for Slack app setup)
- Signature verification before processing
- Rate limit checking (100 events/min/team)
- Background task dispatch for async processing

### `api/slack_adapter.py` (Validation)

Core security layer for Slack webhooks.

| Class                             | Purpose                                |
| --------------------------------- | -------------------------------------- |
| `SlackRequestValidator`           | HMAC-SHA256 signature verification     |
| `SlackRequestNormalizer`          | Parse events/commands into typed dicts |
| `SlackSignatureVerificationError` | Custom exception for auth failures     |

**Security guarantees:**

- 5-minute timestamp tolerance (replay attack prevention)
- Constant-time signature comparison (timing attack prevention)
- Fail-closed: invalid signature = 401, no processing

### `api/slack_client.py` (Outbound)

Async client for posting messages back to Slack.

| Class              | Purpose                           |
| ------------------ | --------------------------------- |
| `SlackAPIClient`   | Wrapper for `chat.postMessage`    |
| `SlackClientError` | Custom exception for API failures |

**Features:**

- Thread reply support (`thread_ts`)
- Block Kit formatting support
- 10-second timeout with explicit error handling

### `memory/slack_ingest.py` (Business Logic)

The brain of Slack integration.

| Function                      | Purpose                                   |
| ----------------------------- | ----------------------------------------- |
| `SlackIngestService.ingest()` | Main entry point                          |
| Deduplication                 | Prevent duplicate processing via event_id |
| Rate limiting                 | 100 events/min per team_id                |
| Permission check              | Channel allowlist enforcement             |
| AIOS dispatch                 | Invoke agent runtime for response         |

---

## Data Models and Contracts

### Normalized Event (Internal)

```python
{
    "team_id": "T...",
    "enterprise_id": "E...",
    "channel_id": "C...",
    "channel_type": "public" | "private" | "unknown",
    "user_id": "U...",
    "ts": "1234567890.123456",
    "thread_ts": "1234567890.123456",
    "thread_uuid": "uuid-v5-deterministic",
    "thread_string": "slack:T...:C...:1234567890.123456",
    "event_id": "Ev...",
    "event_type": "message" | "app_mention",
    "text": "...",
    "raw_event": {...}
}
```

### Invariants

| Rule                           | Enforcement                        |
| ------------------------------ | ---------------------------------- |
| `thread_uuid` is deterministic | UUIDv5 from team:channel:thread_ts |
| Timestamps are Unix epoch      | Slack format preserved             |
| `event_id` is unique per event | Used for deduplication             |
| All IDs are Slack-native       | No internal ID translation         |

---

## Configuration

### Environment Variables

| Variable                 | Required | Purpose                              |
| ------------------------ | -------- | ------------------------------------ |
| `SLACK_SIGNING_SECRET`   | ✅       | HMAC signing secret from Slack app   |
| `SLACK_BOT_TOKEN`        | ✅       | Bot token (`xoxb-...`) for API calls |
| `SLACK_APP_ENABLED`      | ❌       | Feature flag (default: true)         |
| `SLACK_RATE_LIMIT`       | ❌       | Events/min per team (default: 100)   |
| `SLACK_ALLOWED_CHANNELS` | ❌       | Comma-separated channel IDs          |

### Feature Flags

| Flag         | Default | Purpose                           |
| ------------ | ------- | --------------------------------- |
| `_has_slack` | True    | Enables Slack router in server.py |

---

## Observability

### Logs

| Log Event                | Level | Contains                      |
| ------------------------ | ----- | ----------------------------- |
| `slack_event_received`   | INFO  | event_id, team_id, channel_id |
| `slack_signature_valid`  | DEBUG | timestamp, duration           |
| `slack_signature_failed` | WARN  | reason, headers               |
| `slack_message_posted`   | INFO  | channel, ts, thread_ts        |
| `slack_rate_limited`     | WARN  | team_id, current_count        |

### Metrics (via Prometheus)

| Metric                        | Type      | Labels                      |
| ----------------------------- | --------- | --------------------------- |
| `slack_events_total`          | Counter   | team_id, event_type, status |
| `slack_event_latency_seconds` | Histogram | team_id                     |
| `slack_rate_limit_hits_total` | Counter   | team_id                     |

---

## Failure Modes and Resilience

| Failure               | Detection           | Recovery             |
| --------------------- | ------------------- | -------------------- |
| Invalid signature     | 401 response        | Slack retries 3x     |
| Rate limit exceeded   | 429 response        | Automatic backoff    |
| AIOS timeout          | Error packet logged | Message not replied  |
| Slack API error       | Exception logged    | Retry with backoff   |
| Memory substrate down | Circuit breaker     | Graceful degradation |

### Retry Policy

- Slack retries webhooks 3 times with exponential backoff
- L9 does NOT retry outbound messages (idempotency concern)
- Rate limit window resets every 60 seconds

---

## Working with AI on This Subsystem

### Files AI May Edit

| File                     | Scope                          |
| ------------------------ | ------------------------------ |
| `api/routes/slack.py`    | Add endpoints, modify handlers |
| `memory/slack_ingest.py` | Modify business logic          |
| Tests in `tests/`        | Add/modify test cases          |

### Files AI Should NOT Edit Without Review

| File                   | Reason                                   |
| ---------------------- | ---------------------------------------- |
| `api/slack_adapter.py` | Security-critical signature verification |
| `api/slack_client.py`  | External API contract                    |
| `api/server.py`        | Core server wiring                       |

### Required Pre-Reading

1. This README
2. `api/slack_adapter.py` (understand signature verification)
3. `memory/slack_ingest.py` (understand business logic)

### Guardrails

1. **Never disable signature verification** — security critical
2. **Preserve idempotency** — don't process same event_id twice
3. **Respect rate limits** — don't remove rate limiting
4. **Thread context required** — always reply in thread

---

## Testing Strategy

### Unit Tests

```bash
pytest tests/api/test_slack_adapter.py -v
pytest tests/memory/test_slack_ingest.py -v
```

### Integration Tests

```bash
pytest tests/integration/test_slack_flow.py -v
```

### Manual Testing

1. Send message to L9 in Slack
2. Verify signature validation in logs
3. Verify response appears in thread
4. Check packet in memory substrate

---

## Changelog

| Date       | Change                                                           |
| ---------- | ---------------------------------------------------------------- |
| 2026-01-06 | Deleted unused v2.6 stub adapter (`api/adapters/slack_adapter/`) |
| 2025-12-XX | Added rate limiting and permission checks                        |
| 2025-12-XX | Initial Slack v2.0+ implementation                               |

---

## See Also

- [L9 Memory Substrate](../memory/README.md)
- [AIOS Runtime](../core/agents/README.md)
- [Slack API Documentation](https://api.slack.com/)
