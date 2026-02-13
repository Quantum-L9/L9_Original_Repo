# L9 Module-Spec Generator Prompt v1.0

## Purpose

This prompt instructs Perplexity (or Claude) to generate **Module-Spec-v2.4 compliant YAML** that can be directly fed into the L9 CodeGen pipeline.

**Input**: Research synthesis, architecture recommendations, or module description  
**Output**: Complete 22-section YAML spec ready for `codegen/specs/`

---

## Usage

### For Perplexity Labs (Deep Research)

```
POST https://api.perplexity.ai/chat/completions

{
  "model": "sonar-deep-research",
  "messages": [
    {
      "role": "user",
      "content": "[PASTE FULL PROMPT BELOW WITH YOUR MODULE DESCRIPTION]"
    }
  ],
  "temperature": 0.2,
  "max_tokens": 8000
}
```

### For Cursor/Claude

Copy the full prompt below and replace `{{MODULE_DESCRIPTION}}` with your requirements.

---

# SPEC GENERATOR PROMPT

```
You are an L9 system architect generating production-ready module specifications.

## YOUR TASK

Generate a COMPLETE Module-Spec-v2.4 YAML file for the following module:

{{MODULE_DESCRIPTION}}

## L9 SYSTEM CONTEXT

L9 is a secure AI OS with these core patterns:

### Core Protocols
- **PacketEnvelope**: All inter-module communication uses PacketEnvelope protocol
- **Memory Substrate**: PostgreSQL + pgvector for packets, Redis for cache, Neo4j for graphs
- **Logging**: structlog ONLY (NEVER use print or logging module)
- **HTTP Client**: httpx ONLY (NEVER use requests or aiohttp)
- **Startup Tiers**: 0-7 ordering (lower = earlier boot)

### Module Tiers
| Tier | Description | Examples |
|------|-------------|----------|
| 0 | Core infrastructure | Config loader, environment |
| 1 | Database connections | PostgreSQL, Redis, Neo4j |
| 2 | Memory substrate | Packet storage, retrieval |
| 3 | Core services | Agent registry, tool registry |
| 4 | Application services | Adapters, integrations |
| 5 | API layer | HTTP routes, webhooks |
| 6 | Orchestration | Task routing, scheduling |
| 7 | Optional services | Analytics, monitoring |

### Service Types
| Service | Description |
|---------|-------------|
| api | FastAPI HTTP server (port 8000) |
| worker | Background task processor |
| scheduler | Cron/scheduled tasks |
| memory | Memory substrate service |

### Startup Phases
| Phase | When |
|-------|------|
| early | Before API routes registered |
| normal | After dependencies, before serving |
| late | After server starts accepting traffic |

### Standard Endpoints
- AIOS chat: `/chat`
- Memory ingest: `/memory/ingest`
- Memory search: `/memory/search`
- Health: `/health`

## OUTPUT REQUIREMENTS

Generate a COMPLETE YAML file with ALL 22 sections.
- NO placeholders ({{...}})
- NO "if applicable" - make a decision
- NO empty sections - fill everything
- VALID YAML syntax
- Production-ready values

## MODULE-SPEC-v2.4 SCHEMA

```yaml
# ============================================================================
# SECTION 1: METADATA (REQUIRED)
# ============================================================================
metadata:
  module_id: "<lowercase_snake_case>"
  name: "<Human Readable Name>"
  tier: <0-7>
  description: "<One-line description>"
  system: "L9"
  language: "python"
  runtime: "python>=3.11"

# ============================================================================
# SECTION 2: OWNERSHIP (REQUIRED)
# ============================================================================
ownership:
  team: "<core | infra | integrations | security | observability>"
  primary_contact: "<role_name>"

# ============================================================================
# SECTION 3: RUNTIME WIRING (REQUIRED)
# ============================================================================
runtime_wiring:
  service: "<api | worker | scheduler | memory>"
  startup_phase: "<early | normal | late>"
  depends_on:
    - "<postgres | redis | memory.service | ...>"
  blocks_startup_on_failure: <true | false>

# ============================================================================
# SECTION 4: RUNTIME CONTRACT (REQUIRED)
# ============================================================================
runtime_contract:
  runtime_class: "<fully.qualified.ClassName>"
  execution_model: "<sync | async>"
  initialization: "<eager | lazy>"
  singleton: <true | false>

# ============================================================================
# SECTION 5: EXTERNAL SURFACE (REQUIRED)
# ============================================================================
external_surface:
  exposes_http_endpoint: <true | false>
  exposes_webhook: <true | false>
  exposes_tool: <true | false>
  callable_from:
    - "<external | internal>"

# ============================================================================
# SECTION 6: DEPENDENCY CONTRACT (REQUIRED)
# ============================================================================
dependency_contract:
  inbound:
    - module: "<calling_module>"
      interface: "<http | tool | direct>"
  outbound:
    - module: "<called_module>"
      interface: "<http | tool>"
      endpoint: "<endpoint_path>"

# ============================================================================
# SECTION 7: DEPENDENCIES (REQUIRED)
# ============================================================================
dependencies:
  allowed_tiers:
    - <tier_numbers>
  outbound_calls:
    - module: "<module_id>"
      interface: "<http | tool>"
      endpoint: "<endpoint_path>"

# ============================================================================
# SECTION 8: PACKET CONTRACT (REQUIRED)
# ============================================================================
packet_contract:
  emits:
    - "<module>.in"
    - "<module>.out"
    - "<module>.error"
  requires_metadata:
    - "task_id"
    - "thread_uuid"
    - "source"
    - "tool_id"

# ============================================================================
# SECTION 9: PACKET EXPECTATIONS (REQUIRED)
# ============================================================================
packet_expectations:
  on_success:
    emit: "<module>.out"
    contains:
      - "response_text"
      - "metadata"
  on_error:
    emit: "<module>.error"
    contains:
      - "error_code"
      - "error_message"
  durability: "<in_memory | substrate | both>"

# ============================================================================
# SECTION 10: IDEMPOTENCY (REQUIRED)
# ============================================================================
idempotency:
  pattern: "<event_id | composite_key | substrate_lookup>"
  source: "<platform_event_id | webhook_header | computed_hash>"
  durability: "<in_memory | substrate>"

# ============================================================================
# SECTION 11: ERROR POLICY (REQUIRED)
# ============================================================================
error_policy:
  default: "<fail_fast | best_effort>"
  retries:
    enabled: <true | false>
    max_attempts: <0-5>
    backoff_ms: <100-5000>
  escalation:
    emit_error_packet: <true | false>
    mark_task_failed: <true | false>
    alert: "<none | log | metric | slack>"

# ============================================================================
# SECTION 12: OBSERVABILITY (REQUIRED)
# ============================================================================
observability:
  logs:
    enabled: true
    level: "<debug | info | warning | error>"
    include_request_id: true
  metrics:
    enabled: true
    counters:
      - "<module>_requests_total"
      - "<module>_errors_total"
    histograms:
      - "<module>_latency_seconds"
  traces:
    enabled: <true | false>
    sample_rate: <0.0-1.0>

# ============================================================================
# SECTION 13: RUNTIME TOUCHPOINTS (REQUIRED)
# ============================================================================
runtime_touchpoints:
  touches_db: <true | false>
  touches_tools: <true | false>
  touches_external_network: <true | false>
  affects_boot: <true | false>

# ============================================================================
# SECTION 14: TIER EXPECTATIONS (REQUIRED)
# ============================================================================
tier_expectations:
  tier_0_available: <true | false>
  tier_1_available: <true | false>
  tier_2_available: <true | false>
  tier_3_available: <true | false>

# ============================================================================
# SECTION 15: TEST SCOPE (REQUIRED)
# ============================================================================
test_scope:
  unit: true
  integration: <true | false>
  docker_smoke: <true | false>
  boot_failure: <true | false>

# ============================================================================
# SECTION 16: ACCEPTANCE (REQUIRED)
# ============================================================================
acceptance:
  positive:
    - id: "AP-1"
      description: "<Happy path test>"
      test: "test_<happy_path>"
    - id: "AP-2"
      description: "<Another positive case>"
      test: "test_<positive_case>"
  negative:
    - id: "AN-1"
      description: "<Error case test>"
      expected_behavior: "<What should happen>"
      test: "test_<error_case>"

# ============================================================================
# SECTION 17: GLOBAL INVARIANTS ACKNOWLEDGEMENT (REQUIRED)
# ============================================================================
global_invariants_ack:
  emits_packet_on_ingress: true
  tool_calls_traceable: true
  unknown_tool_id_hard_fail: true
  malformed_packet_blocked: true
  missing_env_fails_boot: true

# ============================================================================
# SECTION 18: SPEC CONFIDENCE (REQUIRED)
# ============================================================================
spec_confidence:
  level: "<high | medium | low>"
  basis:
    - "<Evidence for confidence level>"

# ============================================================================
# SECTION 19: FILE MANIFEST (REQUIRED)
# ============================================================================
repo:
  root_path: "/Users/ib-mac/Projects/L9"
  allowed_new_files:
    - "api/<module>_adapter.py"
    - "api/routes/<module>.py"
    - "tests/test_<module>_adapter.py"
    - "tests/test_<module>_smoke.py"
    - "docs/<module>.md"
  allowed_modified_files:
    - "api/server.py"

# ============================================================================
# SECTION 20: INTERFACES (REQUIRED)
# ============================================================================
interfaces:
  inbound:
    - name: "<route_name>"
      method: "<GET | POST | PUT | DELETE>"
      route: "/<module>/<action>"
      headers:
        - "<Required-Header>"
      payload_type: "JSON"
      auth: "<hmac-sha256 | bearer | api_key | none>"
  outbound:
    - name: "<external_call>"
      endpoint: "<endpoint_path>"
      method: "POST"
      timeout_seconds: <1-60>
      retry: <true | false>

# ============================================================================
# SECTION 21: ENVIRONMENT VARIABLES (REQUIRED)
# ============================================================================
environment:
  required:
    - name: "<MODULE>_API_KEY"
      description: "<What this is for>"
  optional:
    - name: "AIOS_BASE_URL"
      description: "AIOS endpoint"
      default: "http://localhost:8000"

# ============================================================================
# SECTION 22: ORCHESTRATION FLOW (REQUIRED)
# ============================================================================
orchestration:
  validation:
    - "<Validation step 1>"
    - "<Validation step 2>"
  context_reads:
    - method: "substrate_service.search_packets"
      filter: "thread_uuid match"
      purpose: "<Why reading context>"
  aios_calls:
    - endpoint: "/chat"
      input: "<What goes in>"
      output: "<What comes out>"
  side_effects:
    - action: "<Side effect description>"
      service: "<service.method>"
      packet_type: "<module>.out"

# ============================================================================
# SECTION 23: BOOT IMPACT (REQUIRED)
# ============================================================================
boot_impact:
  level: "<none | soft | hard>"
  reason: "<Why this boot impact level>"

# ============================================================================
# SECTION 24: MANDATORY STANDARDS (REQUIRED)
# ============================================================================
standards:
  identity:
    canonical_identifier: "tool_id"
  logging:
    library: "structlog"
    forbidden: ["logging", "print"]
  http_client:
    library: "httpx"
    forbidden: ["aiohttp", "requests"]

# ============================================================================
# SECTION 25: GOALS & NON-GOALS (REQUIRED)
# ============================================================================
goals:
  - "<Primary goal>"
  - "<Secondary goal>"

non_goals:
  - "<What this module does NOT do>"
  - "No new database tables"
  - "No new migrations"
  - "No parallel memory/logging/config systems"

# ============================================================================
# SECTION 26: NOTES FOR CODEGEN (REQUIRED)
# ============================================================================
notes_for_codegen:
  - "Use PacketEnvelopeIn for all packets"
  - "Use UUIDv5 for thread_id (not uuid4)"
  - "All handlers accept injected services (no singletons)"
  - "Validate emitted packets against packet_contract.emits"
  - "Generate docker smoke test if external_surface.exposes_http_endpoint"
  - "Generate boot-failure test if boot_impact.level == hard"
```

## EXAMPLE OUTPUT

Here is an example of a correctly generated spec for a Slack webhook adapter:

```yaml
metadata:
  module_id: "slack_webhook_adapter"
  name: "Slack Webhook Adapter"
  tier: 4
  description: "Receives Slack webhook events, validates signatures, routes to AIOS"
  system: "L9"
  language: "python"
  runtime: "python>=3.11"

ownership:
  team: "integrations"
  primary_contact: "integration_lead"

runtime_wiring:
  service: "api"
  startup_phase: "normal"
  depends_on:
    - "postgres"
    - "redis"
    - "memory.service"
  blocks_startup_on_failure: false

runtime_contract:
  runtime_class: "api.slack_webhook_adapter.SlackWebhookAdapter"
  execution_model: "async"
  initialization: "lazy"
  singleton: false

external_surface:
  exposes_http_endpoint: true
  exposes_webhook: true
  exposes_tool: true
  callable_from:
    - "external"

dependency_contract:
  inbound:
    - module: "slack_api"
      interface: "http"
  outbound:
    - module: "aios.runtime"
      interface: "http"
      endpoint: "/chat"
    - module: "memory.service"
      interface: "http"
      endpoint: "/memory/ingest"

dependencies:
  allowed_tiers:
    - 0
    - 1
    - 2
    - 3
  outbound_calls:
    - module: "memory.service"
      interface: "http"
      endpoint: "/memory/ingest"
    - module: "aios.runtime"
      interface: "http"
      endpoint: "/chat"

packet_contract:
  emits:
    - "slack.in"
    - "slack.out"
    - "slack.error"
  requires_metadata:
    - "task_id"
    - "thread_uuid"
    - "source"
    - "tool_id"
    - "slack_channel_id"
    - "slack_user_id"

packet_expectations:
  on_success:
    emit: "slack.out"
    contains:
      - "response_text"
      - "slack_ts"
      - "metadata"
  on_error:
    emit: "slack.error"
    contains:
      - "error_code"
      - "error_message"
      - "slack_event_id"
  durability: "substrate"

idempotency:
  pattern: "event_id"
  source: "platform_event_id"
  durability: "substrate"

error_policy:
  default: "best_effort"
  retries:
    enabled: true
    max_attempts: 3
    backoff_ms: 1000
  escalation:
    emit_error_packet: true
    mark_task_failed: true
    alert: "slack"

observability:
  logs:
    enabled: true
    level: "info"
    include_request_id: true
  metrics:
    enabled: true
    counters:
      - "slack_requests_total"
      - "slack_errors_total"
      - "slack_signature_failures_total"
    histograms:
      - "slack_latency_seconds"
  traces:
    enabled: true
    sample_rate: 1.0

runtime_touchpoints:
  touches_db: true
  touches_tools: true
  touches_external_network: true
  affects_boot: false

tier_expectations:
  tier_0_available: true
  tier_1_available: true
  tier_2_available: true
  tier_3_available: true

test_scope:
  unit: true
  integration: true
  docker_smoke: true
  boot_failure: false

acceptance:
  positive:
    - id: "AP-1"
      description: "Valid Slack event processed and routed to AIOS"
      test: "test_valid_slack_event_processed"
    - id: "AP-2"
      description: "HMAC signature verification passes for valid request"
      test: "test_signature_verification_passes"
    - id: "AP-3"
      description: "AIOS response posted back to Slack channel"
      test: "test_response_posted_to_slack"
    - id: "AP-4"
      description: "Duplicate event detected and skipped (idempotency)"
      test: "test_duplicate_event_skipped"
  negative:
    - id: "AN-1"
      description: "Invalid HMAC signature rejected with 401"
      expected_behavior: "Return 401 Unauthorized, log signature_invalid"
      test: "test_invalid_signature_rejected"
    - id: "AN-2"
      description: "Stale timestamp rejected (>5 minutes old)"
      expected_behavior: "Return 401 Unauthorized, log timestamp_stale"
      test: "test_stale_timestamp_rejected"
    - id: "AN-3"
      description: "Malformed JSON payload rejected with 400"
      expected_behavior: "Return 400 Bad Request, log malformed_payload"
      test: "test_malformed_payload_rejected"

global_invariants_ack:
  emits_packet_on_ingress: true
  tool_calls_traceable: true
  unknown_tool_id_hard_fail: true
  malformed_packet_blocked: true
  missing_env_fails_boot: true

spec_confidence:
  level: "high"
  basis:
    - "Slack API documentation reviewed"
    - "HMAC-SHA256 signature verification well-documented"
    - "Similar patterns exist in other adapters"

repo:
  root_path: "/Users/ib-mac/Projects/L9"
  allowed_new_files:
    - "api/slack_webhook_adapter.py"
    - "api/slack_client.py"
    - "api/routes/slack.py"
    - "tests/test_slack_webhook_adapter.py"
    - "tests/test_slack_smoke.py"
    - "docs/slack_webhook.md"
  allowed_modified_files:
    - "api/server.py"

interfaces:
  inbound:
    - name: "slack_events"
      method: "POST"
      route: "/slack/events"
      headers:
        - "X-Slack-Signature"
        - "X-Slack-Request-Timestamp"
      payload_type: "JSON"
      auth: "hmac-sha256"
  outbound:
    - name: "aios_chat"
      endpoint: "/chat"
      method: "POST"
      timeout_seconds: 30
      retry: false
    - name: "slack_post_message"
      endpoint: "https://slack.com/api/chat.postMessage"
      method: "POST"
      timeout_seconds: 10
      retry: true

environment:
  required:
    - name: "SLACK_SIGNING_SECRET"
      description: "Secret for HMAC signature verification"
    - name: "SLACK_BOT_TOKEN"
      description: "Bot token for posting messages"
  optional:
    - name: "AIOS_BASE_URL"
      description: "AIOS endpoint"
      default: "http://localhost:8000"

orchestration:
  validation:
    - "Verify HMAC-SHA256 signature using X-Slack-Signature header"
    - "Check timestamp freshness (< 5 minutes)"
    - "Parse and validate JSON payload structure"
    - "Extract event_id for idempotency check"
  context_reads:
    - method: "substrate_service.search_packets"
      filter: "thread_uuid match"
      purpose: "Get conversation history for context"
  aios_calls:
    - endpoint: "/chat"
      input: "message text + conversation context"
      output: "response_text"
  side_effects:
    - action: "Store inbound Slack event as packet"
      service: "substrate_service.write_packet"
      packet_type: "slack.in"
    - action: "Post AIOS response to Slack"
      service: "slack_client.post_message"
      packet_type: "slack.out"
    - action: "Store outbound response as packet"
      service: "substrate_service.write_packet"
      packet_type: "slack.out"

boot_impact:
  level: "none"
  reason: "Module is lazy-loaded, does not affect boot sequence"

standards:
  identity:
    canonical_identifier: "tool_id"
  logging:
    library: "structlog"
    forbidden: ["logging", "print"]
  http_client:
    library: "httpx"
    forbidden: ["aiohttp", "requests"]

goals:
  - "Receive and validate Slack webhook events"
  - "Route messages to AIOS for processing"
  - "Post responses back to Slack"
  - "Maintain conversation thread context"

non_goals:
  - "Slash command handling (separate module)"
  - "Interactive component handling (separate module)"
  - "No new database tables"
  - "No new migrations"
  - "No parallel memory/logging/config systems"

notes_for_codegen:
  - "Use PacketEnvelopeIn for all packets"
  - "Use UUIDv5 for thread_id based on Slack channel + thread_ts"
  - "All handlers accept injected services (no singletons)"
  - "Validate emitted packets against packet_contract.emits"
  - "Generate docker smoke test (exposes_http_endpoint = true)"
  - "Implement Slack URL verification challenge response"
  - "Cache HMAC validation results for 5 minutes"
```

## VALIDATION CHECKLIST

Before outputting, verify:

- [ ] All 26 sections present (not 22 - the schema evolved)
- [ ] No `{{placeholders}}` remain
- [ ] Valid YAML syntax (test with a YAML parser)
- [ ] module_id is lowercase_snake_case
- [ ] tier is 0-7 integer
- [ ] All boolean values are `true` or `false` (not quoted)
- [ ] All lists have at least one item
- [ ] packet_contract.emits includes .in, .out, .error variants
- [ ] test names start with `test_`
- [ ] File paths are valid Unix paths

## NOW GENERATE THE SPEC

Generate the complete Module-Spec-v2.4 YAML for:

{{MODULE_DESCRIPTION}}

Output ONLY the YAML, no explanations. Start with `metadata:` and end with the last section.
```

---

## Quick Reference

### Minimal Example Call

```
Generate Module-Spec-v2.4 YAML for:

Module: github_webhook_adapter
Description: Receives GitHub webhook events (push, PR, issues), validates signatures, 
extracts relevant data, and routes to AIOS for processing.
```

### Research-to-Spec Call

```
Based on this research synthesis:

CONSENSUS FINDINGS:
- Use adapter pattern for webhook handling
- HMAC-SHA256 for signature verification
- PacketEnvelope for all communication
- Async httpx for external calls

ARCHITECTURE RECOMMENDATIONS:
- Tier 4 (application service)
- Lazy initialization
- Event-ID based idempotency

Generate Module-Spec-v2.4 YAML for: github_webhook_adapter
```

---

## Integration with Super-Prompt Pack

The Super-Prompt Pack's synthesis output can feed directly into this prompt:

```python
# In autonomous-research-agent.py, after synthesis:

spec_prompt = f"""
Based on this research synthesis:

CONSENSUS FINDINGS:
{json.dumps(synthesis.consensus_patterns, indent=2)}

UNIQUE INSIGHTS:
{synthesis.unique_insights}

ARCHITECTURE RECOMMENDATIONS:
{json.dumps(synthesis.recommended_architecture, indent=2)}

Generate Module-Spec-v2.4 YAML for: {topic}
"""

# Call Perplexity with spec generator prompt + spec_prompt
spec_yaml = await perplexity_client.query(
    SPEC_GENERATOR_PROMPT.replace("{{MODULE_DESCRIPTION}}", spec_prompt)
)

# Save to codegen/specs/
with open(f"codegen/specs/{module_id}.yaml", "w") as f:
    f.write(spec_yaml)

# Feed to CodeGen pipeline
await codegen_agent.generate(f"codegen/specs/{module_id}.yaml")
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-05 | Initial release with 26-section schema |


