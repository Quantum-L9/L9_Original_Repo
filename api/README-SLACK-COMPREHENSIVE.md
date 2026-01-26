# L9 Slack Integration — Comprehensive Module Documentation

> **Version:** 2.0+ (Active Implementation)
> **Last Updated:** 2026-01-08
> **Status:** ✅ Production
> **Owner:** L9 Core Team

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [File Structure](#file-structure)
4. [Message Flow Diagrams](#message-flow-diagrams)
5. [Component Details](#component-details)
6. [Configuration](#configuration)
7. [Feature Flags](#feature-flags)
8. [Dependencies](#dependencies)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The L9 Slack integration provides **bidirectional communication** between Slack workspaces and the L9 AI runtime. It serves as the **primary user interface** for interacting with L9 agents via natural language.

### Key Capabilities

- ✅ **Inbound Events:** Messages, mentions, slash commands, file attachments
- ✅ **Outbound Responses:** Threaded replies, task status updates
- ✅ **Agent Routing:** L-CTO agent, Mac Agent, Email Agent
- ✅ **Memory Integration:** All events stored as packets in memory substrate
- ✅ **Security:** HMAC-SHA256 signature verification (fail-closed)
- ✅ **Deduplication:** Prevents double-processing of retried events
- ✅ **File Processing:** OCR, PDF extraction, audio transcription

### Supported Event Types

| Event Type         | Handler                   | Description                       |
| ------------------ | ------------------------- | --------------------------------- |
| `app_mention`      | `handle_slack_events()`   | Bot mentioned in channel          |
| `message`          | `handle_slack_events()`   | Direct message or channel message |
| `url_verification` | `slack_events()`          | Slack handshake during setup      |
| `/l9` commands     | `handle_slack_commands()` | Slash command handler             |

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SLACK WORKSPACE                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐│
│  │ #channel     │  │ @L9 mention  │  │ /l9 command  │  │ DM to L9    ││
│  │ + file       │  │ + file        │  │              │  │             ││
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘│
│         │                  │                 │                  │       │
│         └──────────────────┴─────────────────┴──────────────────┘       │
│                                    │                                      │
│                                    ▼                                      │
│                    ┌──────────────────────────────┐                      │
│                    │  Slack Events API Webhook    │                      │
│                    │  (POST /slack/events)        │                      │
│                    └───────────────┬──────────────┘                      │
└────────────────────────────────────┼──────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         L9 API SERVER                                   │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ api/routes/slack.py                                               │ │
│  │  ├─ POST /slack/events                                            │ │
│  │  └─ POST /slack/commands                                          │ │
│  │                                                                   │ │
│  │  Responsibilities:                                               │ │
│  │  • Signature validation (HMAC-SHA256)                            │ │
│  │  • Rate limiting                                                 │ │
│  │  • Request parsing (JSON/form)                                  │ │
│  │  • Route to orchestration layer                                  │ │
│  └───────────────────────┬─────────────────────────────────────────┘ │
│                          │                                             │
│                          ▼                                             │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ api/slack_adapter.py                                              │ │
│  │  ├─ SlackRequestValidator                                         │ │
│  │  └─ SlackRequestNormalizer                                       │ │
│  │                                                                   │ │
│  │  Responsibilities:                                               │ │
│  │  • HMAC signature verification                                   │ │
│  │  • Request normalization                                          │ │
│  │  • Thread UUID generation                                         │ │
│  └───────────────────────┬─────────────────────────────────────────┘ │
│                          │                                             │
└──────────────────────────┼─────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                                   │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ memory/slack_ingest.py                                             │ │
│  │  ├─ handle_slack_events()                                          │ │
│  │  ├─ handle_slack_commands()                                        │ │
│  │  ├─ _check_duplicate()                                             │ │
│  │  ├─ _retrieve_thread_context()                                     │ │
│  │  ├─ _retrieve_semantic_hits()                                      │ │
│  │  ├─ _route_to_mac_task()                                           │ │
│  │  ├─ _route_to_email_task()                                         │ │
│  │  ├─ _handle_mac_command()                                          │ │
│  │  └─ handle_slack_with_l_agent()                                    │ │
│  │                                                                   │ │
│  │  Responsibilities:                                               │ │
│  │  • Event deduplication                                            │ │
│  │  • Thread context retrieval                                       │ │
│  │  • Semantic search                                                │ │
│  │  • Task routing (Mac/Email)                                       │ │
│  │  • L-CTO agent routing                                            │ │
│  │  • Memory packet creation                                         │ │
│  └───────┬───────────────────────────────┬───────────────────────────┘ │
│          │                               │                               │
│          ▼                               ▼                               │
│  ┌──────────────────┐         ┌──────────────────┐                       │
│  │ Task Routing     │         │ L-CTO Agent      │                       │
│  │ (Files/Email)    │         │ (Conversation)  │                       │
│  └──────┬───────────┘         └────────┬─────────┘                       │
│         │                               │                                 │
└─────────┼───────────────────────────────┼─────────────────────────────────┘
          │                               │
          ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      TASK EXECUTION                                      │
│                                                                         │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌───────────────┐ │
│  │ Mac Agent Tasks      │  │ Email Agent Tasks    │  │ L-CTO Agent   │ │
│  │                      │  │                      │  │               │ │
│  │ slack_task_router    │  │ email_task_router    │  │ AgentExecutor │ │
│  │   ↓                  │  │   ↓                  │  │   ↓           │ │
│  │ orchestrators/       │  │ email_agent/          │  │ core/agents/  │ │
│  │   agent_execution/   │  │   client.py           │  │   executor.py │ │
│  │   ↓                  │  │                      │  │               │ │
│  │ mac_agent/           │  │ gmail_client.py       │  │ AIOSRuntime   │ │
│  │   executor.py        │  │                      │  │               │ │
│  └──────────────────────┘  └──────────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

### Core Files (Active)

```
api/
├── routes/
│   └── slack.py                    # FastAPI routes (357 lines)
│                                   # • POST /slack/events
│                                   # • POST /slack/commands
│                                   # • Signature validation
│                                   # • Rate limiting
│
├── slack_adapter.py                # Request validation (296 lines)
│                                   # • SlackRequestValidator (HMAC-SHA256)
│                                   # • SlackRequestNormalizer
│                                   # • Thread UUID generation
│
└── slack_client.py                 # Slack API client (146 lines)
                                    # • SlackAPIClient (async)
                                    # • chat.postMessage wrapper
                                    # • Error handling

memory/
└── slack_ingest.py                 # Orchestration layer (1,380 lines)
                                    # • handle_slack_events()
                                    # • handle_slack_commands()
                                    # • Deduplication
                                    # • Thread context retrieval
                                    # • Semantic search
                                    # • Task routing
                                    # • L-CTO agent routing
                                    # • Memory packet creation

orchestration/
├── slack_task_router.py            # Mac Agent task router (248 lines)
│                                   # • route_slack_message()
│                                   # • LLM-based task planning
│                                   # • ONLY creates mac_task type
│
└── email_task_router.py            # Email Agent task router (248 lines)
                                    # • route_email_task()
                                    # • LLM-based email task planning
                                    # • ONLY creates email_task type

orchestrators/
└── agent_execution/
    ├── __init__.py                 # Module exports
    ├── interface.py                # IAgentExecutionOrchestrator protocol
    ├── orchestrator.py             # AgentExecutionOrchestrator (318 lines)
    │                               # • poll_and_execute() loop
    │                               # • Mac Agent task execution
    │                               # • ONLY handles mac_task
    │
    └── task_queue.py               # File-based task queue (309 lines)
                                    # • enqueue_mac_task_dict()
                                    # • get_next_task()
                                    # • mark_task_completed()
                                    # • ONLY handles mac_task

services/
├── slack_client.py                 # Legacy sync client (312 lines)
│                                   # • slack_post() (sync)
│                                   # • post_result() (task results)
│                                   # • Used by Mac Agent runner
│
└── slack_files.py                  # File processing (432 lines)
                                    # • download_file()
                                    # • process_file_artifact()
                                    # • OCR, PDF, transcription
                                    # • File storage management

email_agent/
└── client.py                       # Email task executor (336 lines)
                                    # • execute_email_task()
                                    # • Gmail API operations
                                    # • Direct execution (no queue)
```

### Archived Files (Reference Only)

```
_archived/legacy_slack/
└── webhook_slack.py                # DEPRECATED (960 lines)
                                    # • Never registered in server.py
                                    # • Features ported to slack_ingest.py
                                    # • Archived 2026-01-08

_archived/codegen_slack_adapter/
└── (v2.6 adapter - never deployed)
```

---

## Message Flow Diagrams

### Flow 1: Standard Message → L-CTO Agent

```
┌─────────────┐
│ Slack User  │
│ "What is L9?"│
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Slack Events API                                            │
│ POST /slack/events                                          │
│ {                                                           │
│   "type": "event_callback",                                │
│   "event": {                                                │
│     "type": "app_mention",                                 │
│     "text": "What is L9?",                                 │
│     "user": "U123",                                        │
│     "channel": "C456",                                     │
│     "ts": "1234567890.123456"                              │
│   }                                                         │
│ }                                                           │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ api/routes/slack.py::slack_events()                        │
│                                                             │
│ 1. Validate signature (HMAC-SHA256)                        │
│ 2. Parse JSON payload                                       │
│ 3. Check rate limit                                         │
│ 4. Ignore bot messages                                      │
│ 5. Call handle_slack_events()                               │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ memory/slack_ingest.py::handle_slack_events()               │
│                                                             │
│ 1. Normalize provenance (team_id, channel_id, user_id)      │
│ 2. Generate thread UUID (deterministic)                     │
│ 3. Check duplicate (_check_duplicate())                     │
│ 4. Retrieve thread context (_retrieve_thread_context())     │
│ 5. Retrieve semantic hits (_retrieve_semantic_hits())      │
│ 6. Route to L-CTO agent (handle_slack_with_l_agent())       │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ core/agents/executor.py::AgentExecutorService               │
│                                                             │
│ 1. Create AgentTask (agent_id="l-cto")                     │
│ 2. Load agent kernels                                       │
│ 3. Execute reasoning loop                                   │
│ 4. Generate response                                        │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ memory/slack_ingest.py::handle_slack_with_l_agent()        │
│                                                             │
│ 1. Post reply to Slack (api/slack_client.py)               │
│ 2. Store inbound packet (memory substrate)                  │
│ 3. Store outbound packet (memory substrate)                 │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│ Slack User  │
│ (sees reply)│
└─────────────┘
```

### Flow 2: Message with File → Mac Agent Task

```
┌─────────────┐
│ Slack User  │
│ "Process    │
│  this PDF"  │
│  + file.pdf │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ api/routes/slack.py::slack_events()                         │
│  → memory/slack_ingest.py::handle_slack_events()           │
│                                                             │
│ 1. Detect file attachments                                   │
│ 2. Process files (services/slack_files.py)                  │
│    • Download from Slack                                    │
│    • OCR (if image)                                         │
│    • PDF extraction (if PDF)                                │
│    • Transcription (if audio)                                │
│ 3. Route to Mac Agent (_route_to_mac_task())                │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ orchestration/slack_task_router.py::route_slack_message()   │
│                                                             │
│ 1. LLM call (GPT-4o-mini)                                   │
│ 2. Generate task structure:                                 │
│    {                                                        │
│      "type": "mac_task",                                    │
│      "steps": [                                             │
│        {"action": "goto", "url": "..."},                    │
│        {"action": "click", "selector": "..."}                │
│      ],                                                     │
│      "artifacts": [...],                                    │
│      "metadata": {...}                                      │
│    }                                                        │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ orchestrators/agent_execution/task_queue.py                 │
│                                                             │
│ 1. enqueue_mac_task_dict(task_dict)                         │
│ 2. Write to ~/.l9/mac_tasks/{task_id}.json                  │
│ 3. Ingest packet to memory                                  │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ orchestrators/agent_execution/orchestrator.py               │
│                                                             │
│ 1. poll_and_execute() loop (every 3 seconds)               │
│ 2. get_next_task() → reads from file queue                  │
│ 3. Execute via mac_agent.executor.AutomationExecutor        │
│ 4. Post result to Slack (services/slack_client.py)          │
│ 5. mark_task_completed()                                   │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│ Slack User  │
│ (sees task  │
│  result)    │
└─────────────┘
```

### Flow 3: Email Command → Email Agent

```
┌─────────────┐
│ Slack User  │
│ "email: send│
│  message to │
│  john@ex.com"│
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ memory/slack_ingest.py::handle_slack_events()              │
│                                                             │
│ 1. Detect email command (_is_email_command())               │
│ 2. Route to Email Agent (_route_to_email_task())            │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ orchestration/email_task_router.py::route_email_task()      │
│                                                             │
│ 1. LLM call (GPT-4o-mini)                                   │
│ 2. Generate email task structure:                           │
│    {                                                        │
│      "type": "email_task",                                  │
│      "steps": [                                             │
│        {"action": "draft_email", "to": "...", ...},        │
│        {"action": "send_email", ...}                         │
│      ],                                                     │
│      "metadata": {...}                                      │
│    }                                                        │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ email_agent/client.py::execute_email_task()                 │
│                                                             │
│ 1. Direct execution (no queue)                              │
│ 2. Gmail API operations (gmail_client.py)                   │
│ 3. Return result                                            │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ memory/slack_ingest.py::_route_to_email_task()              │
│                                                             │
│ 1. Post result to Slack                                     │
│ 2. Store packets to memory                                  │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│ Slack User  │
│ (sees email │
│  sent)      │
└─────────────┘
```

### Flow 4: Slash Command → Command Handler

```
┌─────────────┐
│ Slack User  │
│ /l9 do task │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ Slack Events API                                            │
│ POST /slack/commands                                        │
│ (form-encoded)                                              │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ api/routes/slack.py::slack_commands()                      │
│                                                             │
│ 1. Validate signature                                       │
│ 2. Parse form data                                          │
│ 3. Return 200 ACK immediately (< 3 seconds)                 │
│ 4. Process async in background                              │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ memory/slack_ingest.py::handle_slack_commands()             │
│                                                             │
│ 1. Parse command (/l9 do <task>)                            │
│ 2. Route to appropriate handler                            │
│ 3. Post response to Slack (response_url or API)             │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│ Slack User  │
│ (sees       │
│  response)  │
└─────────────┘
```

---

## Component Details

### 1. `api/routes/slack.py` — HTTP Routes

**Purpose:** FastAPI router for Slack webhook endpoints

**Endpoints:**

- `POST /slack/events` — Slack Events API webhook
- `POST /slack/commands` — Slack slash command handler

**Key Functions:**

```python
async def slack_events(...) -> Dict[str, Any]
    # Handles: url_verification, event_callback
    # Validates signature, rate limits, routes to handle_slack_events()

async def slack_commands(...) -> Dict[str, Any]
    # Handles: /l9 commands
    # Returns 200 ACK immediately, processes async
```

**Dependencies:**

- `api.slack_adapter.SlackRequestValidator` — Signature validation
- `memory.slack_ingest.handle_slack_events()` — Event orchestration
- `memory.slack_ingest.handle_slack_commands()` — Command handling

---

### 2. `api/slack_adapter.py` — Request Validation

**Purpose:** HMAC-SHA256 signature verification and request normalization

**Classes:**

```python
class SlackRequestValidator:
    def verify(request_body, timestamp_str, signature) -> Tuple[bool, Optional[str]]
        # Validates HMAC-SHA256 signature
        # Checks timestamp freshness (300s tolerance)
        # Returns (is_valid, error_reason)

class SlackRequestNormalizer:
    def normalize(payload) -> Dict[str, Any]
        # Extracts event details
        # Generates thread UUID
        # Normalizes provenance
```

**Security:**

- Fail-closed: Invalid signature → 401 Unauthorized
- Replay protection: Timestamp must be within 300 seconds
- Constant-time comparison: Prevents timing attacks

---

### 3. `api/slack_client.py` — Slack API Client

**Purpose:** Async wrapper for posting messages to Slack

**Classes:**

```python
class SlackAPIClient:
    async def post_message(
        channel: str,
        text: str,
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]
        # Posts message to Slack channel
        # Supports thread replies
        # Handles errors gracefully
```

**Usage:**

```python
client = SlackAPIClient(bot_token="xoxb-...", http_client=httpx_client)
await client.post_message(
    channel="C123",
    text="Hello!",
    thread_ts="1234567890.123456"
)
```

---

### 4. `memory/slack_ingest.py` — Orchestration Layer

**Purpose:** Core business logic for Slack event processing

**Key Functions:**

#### `handle_slack_events()`

Main entry point for Slack Events API webhooks.

**Flow:**

1. Normalize provenance (team_id, channel_id, user_id)
2. Generate thread UUID (deterministic from team:channel:thread_ts)
3. Check duplicate (`_check_duplicate()`)
4. Retrieve thread context (`_retrieve_thread_context()`)
5. Retrieve semantic hits (`_retrieve_semantic_hits()`)
6. Route based on content:
   - `@L` command → L-CTO agent
   - `!mac` command → Mac Agent
   - Email command → Email Agent
   - Files attached → Mac Agent task
   - Default → L-CTO agent (if legacy flag False) or AIOS /chat

#### `handle_slack_commands()`

Handles slash commands (`/l9 do <task>`).

**Flow:**

1. Parse command text
2. Route to appropriate handler
3. Post response to Slack (response_url or API)

#### `_check_duplicate()`

Prevents double-processing of retried events.

**Implementation:**

- Queries `packet_store` for existing event_id
- Returns early if duplicate found
- Uses event_id as primary key, fallback to team:channel:ts:user

#### `_retrieve_thread_context()`

Fetches conversation history from memory substrate.

**Returns:**

- List of packets in thread (ordered by timestamp)
- Used for conversation continuity

#### `_retrieve_semantic_hits()`

Performs semantic search for related knowledge.

**Returns:**

- List of semantically similar packets
- Used for context injection

#### `_route_to_mac_task()`

Routes messages with files to Mac Agent task queue.

**Flow:**

1. Call `slack_task_router.route_slack_message()`
2. Enqueue via `orchestrators.agent_execution.enqueue_mac_task_dict()`
3. Post acknowledgment to Slack

#### `_route_to_email_task()`

Routes email commands to Email Agent.

**Flow:**

1. Call `email_task_router.route_email_task()`
2. Execute directly via `email_agent.client.execute_email_task()`
3. Post result to Slack

#### `handle_slack_with_l_agent()`

Routes messages to L-CTO agent via AgentExecutorService.

**Flow:**

1. Create `AgentTask` with context
2. Call `AgentExecutorService.start_agent_task()`
3. Post reply to Slack
4. Store packets to memory

---

### 5. `orchestration/slack_task_router.py` — Mac Task Router

**Purpose:** Converts Slack messages into Mac Agent task structures

**Function:**

```python
def route_slack_message(
    text: str,
    artifacts: List[Dict[str, Any]],
    user: str
) -> Dict[str, Any]
    # Uses LLM (GPT-4o-mini) to generate task structure
    # ONLY creates mac_task type
    # Returns: {"type": "mac_task", "steps": [...], ...}
```

**Task Structure:**

```json
{
  "type": "mac_task",
  "steps": [
    {"action": "goto", "url": "https://example.com"},
    {"action": "click", "selector": "text=Submit"},
    {"action": "fill", "selector": "#field", "text": "..."},
    {"action": "upload", "selector": "#file", "file_path": "..."},
    {"action": "screenshot"}
  ],
  "artifacts": [...],
  "metadata": {
    "user": "U123",
    "instructions": "original text",
    "channel": "C456"
  }
}
```

---

### 6. `orchestration/email_task_router.py` — Email Task Router

**Purpose:** Converts Slack messages into Email Agent task structures

**Function:**

```python
def route_email_task(
    text: str,
    artifacts: List[Dict[str, Any]],
    user: str
) -> Dict[str, Any]
    # Uses LLM (GPT-4o-mini) to generate email task structure
    # ONLY creates email_task type
    # Returns: {"type": "email_task", "steps": [...], ...}
```

**Task Structure:**

```json
{
  "type": "email_task",
  "steps": [
    {"action": "draft_email", "to": "...", "subject": "...", "body": "..."},
    {"action": "send_email", "draft_id": "..."}
  ],
  "artifacts": [...],
  "metadata": {
    "user": "U123",
    "instructions": "original text",
    "channel": "C456"
  }
}
```

---

### 7. `orchestrators/agent_execution/` — Mac Agent Orchestrator

**Purpose:** Orchestrates Mac Agent task execution from file-based queue

**Components:**

#### `task_queue.py`

File-based task queue for Mac Agent tasks.

**Functions:**

```python
def enqueue_mac_task_dict(task_dict: Dict[str, Any]) -> str
    # Writes task to ~/.l9/mac_tasks/{task_id}.json
    # Returns UUID string task_id
    # ONLY accepts mac_task type

def get_next_task() -> Optional[Dict[str, Any]]
    # Reads oldest task from queue
    # Moves to in_progress/ directory
    # Returns task dict

def mark_task_completed(task_id: str)
    # Moves task from in_progress/ to completed/
```

#### `orchestrator.py`

Main orchestrator that polls queue and executes tasks.

**Class:**

```python
class AgentExecutionOrchestrator(IAgentExecutionOrchestrator):
    async def poll_and_execute() -> None
        # Polls queue every 3 seconds
        # Executes mac_task via AutomationExecutor
        # Posts results to Slack
        # ONLY handles mac_task type
```

---

### 8. `services/slack_files.py` — File Processing

**Purpose:** Downloads and processes file attachments from Slack

**Functions:**

```python
def download_file(file_id, file_url_private, filename) -> bytes
    # Downloads file from Slack using private URL

def process_file_artifact(file_info) -> Dict[str, Any]
    # Processes file:
    # • OCR (if image)
    # • PDF extraction (if PDF)
    # • Transcription (if audio)
    # • Returns artifact dict with metadata
```

**Storage:**

- Files saved to `~/.l9/slack_files/YYYY/MM/DD/`
- Artifact metadata includes: path, type, OCR data, PDF fields, transcription

---

### 9. `services/slack_client.py` — Legacy Sync Client

**Purpose:** Synchronous Slack client for Mac Agent task results

**Functions:**

```python
def slack_post(channel: str, text: str)
    # Synchronous message posting
    # Used by Mac Agent runner

def post_result(user: str, task: dict, result: dict)
    # Formats and posts task execution results
    # Used by orchestrator after task completion
```

**Note:** This is a legacy sync client. New code should use `api/slack_client.py` (async).

---

## Configuration

### Environment Variables

```bash
# Required
SLACK_SIGNING_SECRET=xoxb-...          # From Slack app Settings > Basic Information
SLACK_BOT_TOKEN=xoxb-...                # From Slack app Settings > Install App

# Optional
SLACK_APP_ENABLED=true                  # Master toggle (default: false)
L9_ENABLE_LEGACY_SLACK_ROUTER=false     # Use L-CTO agent routing (default: true)
L_SLACK_USER_ID=l-cto                   # Bot user ID for filtering own messages
```

### Settings (`config/settings.py`)

```python
class Settings:
    slack_app_enabled: bool = False
    slack_bot_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None
    l9_enable_legacy_slack_router: bool = True
    l_slack_user_id: str = "l-cto"
```

---

## Feature Flags

| Flag                            | Default | Purpose                              | Location                 |
| ------------------------------- | ------- | ------------------------------------ | ------------------------ |
| `SLACK_APP_ENABLED`             | `false` | Master toggle for Slack integration  | `config/settings.py`     |
| `L9_ENABLE_LEGACY_SLACK_ROUTER` | `true`  | Use legacy AIOS /chat vs L-CTO agent | `memory/slack_ingest.py` |

### `L9_ENABLE_LEGACY_SLACK_ROUTER`

**When `false` (Recommended):**

- Routes through L-CTO agent via `AgentExecutorService`
- Full kernel stack, governance, memory integration
- Better conversation continuity

**When `true` (Legacy):**

- Routes through AIOS `/chat` endpoint
- Simpler, but less integrated
- No kernel stack, limited governance

---

## Dependencies

### External Dependencies

| Package     | Purpose             | Used By                                                                    |
| ----------- | ------------------- | -------------------------------------------------------------------------- |
| `httpx`     | HTTP client (async) | `api/slack_client.py`, `memory/slack_ingest.py`                            |
| `openai`    | LLM client          | `orchestration/slack_task_router.py`, `orchestration/email_task_router.py` |
| `slack_sdk` | Legacy sync client  | `services/slack_client.py` (optional)                                      |

### Internal Dependencies

| Module                          | Used By                           | Purpose                                         |
| ------------------------------- | --------------------------------- | ----------------------------------------------- |
| `memory.substrate_service`      | `slack_ingest.py`                 | Packet storage, thread context, semantic search |
| `core.agents.executor`          | `slack_ingest.py`                 | L-CTO agent execution                           |
| `mac_agent.executor`            | `agent_execution/orchestrator.py` | Browser automation                              |
| `email_agent.client`            | `slack_ingest.py`                 | Email operations                                |
| `orchestrators.agent_execution` | `slack_ingest.py`                 | Mac Agent task queue                            |

---

## Testing

### Unit Tests

```bash
# Test signature validation
pytest tests/api/test_slack_adapter.py

# Test file processing
pytest tests/services/test_slack_files.py

# Test task routing
pytest tests/orchestration/test_slack_task_router.py
```

### Integration Tests

```bash
# Test end-to-end Slack flow
pytest tests/integration/test_slack_dispatch_integration.py
```

### Manual Testing

1. **Test Events:**

   ```bash
   # Send test event via Slack Events API
   curl -X POST http://localhost:8000/slack/events \
     -H "X-Slack-Signature: v0=..." \
     -H "X-Slack-Request-Timestamp: $(date +%s)" \
     -d '{"type": "event_callback", "event": {...}}'
   ```

2. **Test Commands:**
   ```bash
   # Send slash command
   curl -X POST http://localhost:8000/slack/commands \
     -H "X-Slack-Signature: v0=..." \
     -d "command=/l9&text=do task&user_id=U123"
   ```

---

## Troubleshooting

### Common Issues

#### 1. Signature Verification Fails

**Symptom:** `401 Unauthorized` on all Slack requests

**Causes:**

- `SLACK_SIGNING_SECRET` not set or incorrect
- Request timestamp too old (> 300 seconds)
- Signature header format incorrect

**Fix:**

```bash
# Verify secret is set
echo $SLACK_SIGNING_SECRET

# Check Slack app Settings > Basic Information > Signing Secret
```

#### 2. Bot Not Responding

**Symptom:** Messages sent but no reply

**Causes:**

- `SLACK_BOT_TOKEN` not set
- Bot not added to channel
- `SLACK_APP_ENABLED=false`

**Fix:**

```bash
# Verify token is set
echo $SLACK_BOT_TOKEN

# Check Slack app Settings > Install App > Bot User OAuth Token
# Ensure bot is added to channel: /invite @L9
```

#### 3. Duplicate Processing

**Symptom:** Bot responds twice to same message

**Causes:**

- `_check_duplicate()` not working
- Event ID not being set correctly

**Fix:**

- Check `packet_store` for duplicate event_id entries
- Verify `_check_duplicate()` is being called
- Check logs for deduplication messages

#### 4. Mac Agent Tasks Not Executing

**Symptom:** Tasks enqueued but not executed

**Causes:**

- Orchestrator not running
- `MAC_AGENT_ENABLED=false`
- Queue directory permissions

**Fix:**

```bash
# Check orchestrator is running
ps aux | grep agent_execution

# Verify queue directory exists
ls -la ~/.l9/mac_tasks/

# Check orchestrator logs
tail -f logs/agent_execution.log
```

#### 5. Email Tasks Failing

**Symptom:** Email commands return error

**Causes:**

- Gmail API not configured
- `email_agent` not available
- OAuth tokens expired

**Fix:**

```bash
# Check Gmail client is available
python3 -c "from email_agent.gmail_client import GmailClient; print('OK')"

# Verify OAuth tokens
ls -la ~/.l9/gmail_credentials.json
```

---

## File Interaction Matrix

| File                                            | Imports From                                                                                                                                                                                 | Used By                                                                   |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `api/routes/slack.py`                           | `api.slack_adapter`, `memory.slack_ingest`                                                                                                                                                   | `api/server.py`                                                           |
| `api/slack_adapter.py`                          | None                                                                                                                                                                                         | `api/routes/slack.py`                                                     |
| `api/slack_client.py`                           | `httpx`                                                                                                                                                                                      | `memory/slack_ingest.py`                                                  |
| `memory/slack_ingest.py`                        | `api.slack_adapter`, `api.slack_client`, `orchestration.slack_task_router`, `orchestration.email_task_router`, `orchestrators.agent_execution`, `email_agent.client`, `core.agents.executor` | `api/routes/slack.py`                                                     |
| `orchestration/slack_task_router.py`            | `openai`                                                                                                                                                                                     | `memory/slack_ingest.py`                                                  |
| `orchestration/email_task_router.py`            | `openai`                                                                                                                                                                                     | `memory/slack_ingest.py`                                                  |
| `orchestrators/agent_execution/task_queue.py`   | `memory.ingestion`                                                                                                                                                                           | `orchestrators/agent_execution/orchestrator.py`, `memory/slack_ingest.py` |
| `orchestrators/agent_execution/orchestrator.py` | `mac_agent.executor`, `services.slack_client`                                                                                                                                                | Standalone (polling loop)                                                 |
| `services/slack_files.py`                       | `httpx`                                                                                                                                                                                      | `memory/slack_ingest.py`                                                  |
| `services/slack_client.py`                      | `slack_sdk` (optional)                                                                                                                                                                       | `orchestrators/agent_execution/orchestrator.py`                           |

---

## Complete Message Flow (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SLACK WORKSPACE                                    │
│                                                                              │
│  User sends: "@L9 process this file" + [file.pdf]                          │
└────────────────────────────────────┬──────────────────────────────────────────┘
                                     │
                                     │ POST /slack/events
                                     │ Headers: X-Slack-Signature, X-Slack-Request-Timestamp
                                     │ Body: JSON event payload
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  api/routes/slack.py::slack_events()                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Validate signature (SlackRequestValidator.verify())                │  │
│  │ 2. Parse JSON payload                                                │  │
│  │ 3. Rate limit check (100 events/min per team)                         │  │
│  │ 4. Ignore bot messages (prevent loops)                                │  │
│  │ 5. Call handle_slack_events()                                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬──────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  memory/slack_ingest.py::handle_slack_events()                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Normalize provenance (team_id, channel_id, user_id)               │  │
│  │ 2. Generate thread UUID (deterministic)                               │  │
│  │ 3. Check duplicate (_check_duplicate())                               │  │
│  │    → Query packet_store for event_id                                  │  │
│  │    → If found: return {"ok": True, "duplicate": True}                │  │
│  │                                                                       │  │
│  │ 4. Retrieve thread context (_retrieve_thread_context())              │  │
│  │    → Query packet_store for thread_uuid                               │  │
│  │    → Returns: [packet1, packet2, ...] (conversation history)         │  │
│  │                                                                       │  │
│  │ 5. Retrieve semantic hits (_retrieve_semantic_hits())                 │  │
│  │    → Semantic search on message text                                  │  │
│  │    → Returns: [hit1, hit2, ...] (related knowledge)                  │  │
│  │                                                                       │  │
│  │ 6. Process file attachments (if present)                              │  │
│  │    → services/slack_files.py::process_file_artifact()                 │  │
│  │    → Download, OCR, PDF extraction, transcription                      │  │
│  │                                                                       │  │
│  │ 7. Route based on content:                                            │  │
│  │    ├─ "@L" command → handle_slack_with_l_agent()                     │  │
│  │    ├─ "!mac" command → _handle_mac_command()                         │  │
│  │    ├─ Email command → _route_to_email_task()                           │  │
│  │    ├─ Files attached → _route_to_mac_task()                            │  │
│  │    └─ Default → L-CTO agent (if legacy=false) or AIOS /chat           │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬──────────────────────────────────────────┘
                                     │
                                     │ (Files detected)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  memory/slack_ingest.py::_route_to_mac_task()                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Call orchestration/slack_task_router.py::route_slack_message()     │  │
│  │    → LLM generates task structure                                    │  │
│  │    → Returns: {"type": "mac_task", "steps": [...], ...}               │  │
│  │                                                                       │  │
│  │ 2. Enqueue via orchestrators/agent_execution/task_queue.py           │  │
│  │    → enqueue_mac_task_dict(task_dict)                                │  │
│  │    → Writes to ~/.l9/mac_tasks/{task_id}.json                        │  │
│  │    → Ingests packet to memory                                         │  │
│  │                                                                       │  │
│  │ 3. Post acknowledgment to Slack                                      │  │
│  │    → api/slack_client.py::SlackAPIClient.post_message()              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬──────────────────────────────────────────┘
                                     │
                                     │ (Task enqueued)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  orchestrators/agent_execution/orchestrator.py::poll_and_execute()         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Poll queue every 3 seconds                                          │  │
│  │    → get_next_task() reads from ~/.l9/mac_tasks/*.json                │  │
│  │                                                                       │  │
│  │ 2. Execute task                                                       │  │
│  │    → mac_agent.executor.AutomationExecutor.run_steps()                 │  │
│  │    → Runs Playwright automation                                       │  │
│  │                                                                       │  │
│  │ 3. Post result to Slack                                               │  │
│  │    → services/slack_client.py::post_result()                          │  │
│  │    → Formats result with logs, screenshots                             │  │
│  │                                                                       │  │
│  │ 4. Mark task completed                                                │  │
│  │    → mark_task_completed(task_id)                                     │  │
│  │    → Moves file to completed/ directory                               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬──────────────────────────────────────────┘
                                     │
                                     │ (Result posted)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SLACK WORKSPACE                                    │
│                                                                              │
│  User sees: "Task completed. Screenshot: ..."                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Memory Integration

### Packet Types

| Packet Type            | Created By        | Purpose                     |
| ---------------------- | ----------------- | --------------------------- |
| `slack_event_received` | `slack_ingest.py` | Inbound event from Slack    |
| `slack_reply_sent`     | `slack_ingest.py` | Outbound reply to Slack     |
| `mac_task_enqueued`    | `task_queue.py`   | Mac Agent task queued       |
| `email_task_executed`  | `slack_ingest.py` | Email Agent task executed   |
| `agent.executor.trace` | `executor.py`     | L-CTO agent reasoning steps |

### Thread Model

- **Thread UUID:** Deterministic UUIDv5 from `team_id:channel_id:thread_ts`
- **Storage:** All packets include `thread_id` for conversation grouping
- **Retrieval:** `_retrieve_thread_context()` fetches all packets in thread
- **Continuity:** Thread context passed to L-CTO agent for conversation history

---

## Security

### Signature Verification

- **Algorithm:** HMAC-SHA256
- **Format:** `v0=<hex_hash>`
- **Tolerance:** 300 seconds (prevents replay attacks)
- **Fail-closed:** Invalid signature → 401, no processing

### Rate Limiting

- **Events:** 100 events/minute per team
- **Commands:** 50 commands/minute per user
- **Implementation:** Redis-based (if available) or in-memory

### Bot Message Filtering

- Filters out bot's own messages to prevent infinite loops
- Uses `L_SLACK_USER_ID` and `SLACK_BOT_USER_ID` for filtering

---

## Error Handling

### Fail-Safe Patterns

1. **Signature validation fails:** Return 401, log error, no processing
2. **Agent execution fails:** Log error, store error packet, return 200 to Slack
3. **Slack API fails:** Log error, store error packet, return 200 to Slack
4. **Memory persistence fails:** Log error, still return 200 to Slack

**Rationale:** Slack retries webhooks if non-200 response. We return 200 to prevent retry loops, but log all errors for investigation.

---

## Performance

### Optimization Strategies

1. **Async I/O:** All Slack API calls are async
2. **Fire-and-forget memory:** Packet ingestion doesn't block response
3. **Deduplication:** Prevents duplicate processing
4. **Rate limiting:** Protects against abuse

### Bottlenecks

- **LLM calls:** Task routing uses GPT-4o-mini (can be slow)
- **File processing:** OCR/PDF extraction (can be slow)
- **Memory queries:** Thread context retrieval (can be slow with large threads)

---

## Future Enhancements

### Planned Features

1. **Interactive Modals:** Slack modals for user input
2. **File Uploads:** Direct file upload to Slack (not just attachments)
3. **Rich Blocks:** Formatting, buttons, interactive elements
4. **Multi-workspace:** Support for multiple Slack workspaces
5. **WebSocket:** Real-time bidirectional communication

### Deprecation Path

- **Legacy AIOS /chat:** Will be removed when `L9_ENABLE_LEGACY_SLACK_ROUTER=false` is default
- **Legacy sync client:** `services/slack_client.py` will be deprecated in favor of async client

---

## Related Documentation

- `api/README-SLACK.md` — Original Slack integration README
- `api/adapters/slack_adapter/README.md` — Adapter status (archived)
- `reports/GMP_Report_GMP-32-Port-Slack-Legacy-Features.md` — Migration report
- `reports/GMP_Report_GMP-40-Refactor-Agent-Execution-to-Orchestrator.md` — Orchestrator refactoring

---

## Quick Reference

### Key Files

| File                                 | Lines | Purpose                |
| ------------------------------------ | ----- | ---------------------- |
| `api/routes/slack.py`                | 357   | HTTP routes            |
| `memory/slack_ingest.py`             | 1,380 | Orchestration          |
| `api/slack_adapter.py`               | 296   | Validation             |
| `api/slack_client.py`                | 146   | API client             |
| `orchestration/slack_task_router.py` | 248   | Mac task routing       |
| `orchestration/email_task_router.py` | 248   | Email task routing     |
| `services/slack_files.py`            | 432   | File processing        |
| `orchestrators/agent_execution/`     | 735   | Mac Agent orchestrator |

### Key Functions

| Function                      | File                                            | Purpose                  |
| ----------------------------- | ----------------------------------------------- | ------------------------ |
| `slack_events()`              | `api/routes/slack.py`                           | HTTP endpoint for events |
| `handle_slack_events()`       | `memory/slack_ingest.py`                        | Main orchestration       |
| `handle_slack_with_l_agent()` | `memory/slack_ingest.py`                        | L-CTO agent routing      |
| `_route_to_mac_task()`        | `memory/slack_ingest.py`                        | Mac Agent routing        |
| `_route_to_email_task()`      | `memory/slack_ingest.py`                        | Email Agent routing      |
| `route_slack_message()`       | `orchestration/slack_task_router.py`            | Mac task generation      |
| `route_email_task()`          | `orchestration/email_task_router.py`            | Email task generation    |
| `poll_and_execute()`          | `orchestrators/agent_execution/orchestrator.py` | Mac Agent execution loop |

---

**Last Updated:** 2026-01-08
**Maintainer:** L9 Core Team
**Status:** ✅ Production
