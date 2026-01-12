# L9 Five-Tier Observability

Version: 1.0.0  
Module: `core/observability/`

## Overview

The L9 Five-Tier Observability module provides comprehensive observability for the L9 Secure AI OS:

1. **Distributed Tracing** - W3C Trace Context standard, hierarchical spans
2. **Failure Detection** - 12 failure classes with automated recovery
3. **Context Strategies** - 6 algorithms for context window optimization
4. **Metrics Aggregation** - SRE metrics and Agent KPIs
5. **Multi-Backend Export** - Console, file, L9 Memory Substrate, Datadog, Honeycomb

## Quick Start

The observability module is automatically initialized at server startup when enabled:

```python
# Controlled by environment variable (default: true)
L9_OBSERVABILITY=true
```

## Environment Variables

All observability configuration uses the `OBS_` prefix:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OBS_ENABLED` | bool | `true` | Enable/disable observability system |
| `OBS_SAMPLING_RATE` | float | `0.10` | Fraction of requests to sample (0.0-1.0) |
| `OBS_ERROR_SAMPLING_RATE` | float | `1.0` | Fraction of errors to sample (typically 1.0) |
| `OBS_EXPORTERS` | list | `console` | Comma-separated list: console, file, substrate, jaeger, datadog, honeycomb |
| `OBS_BATCH_SIZE` | int | `100` | Number of spans to batch before export |
| `OBS_BATCH_TIMEOUT_SEC` | int | `10` | Seconds before flushing batch |
| `OBS_LOG_LEVEL` | str | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `OBS_FILE_EXPORT_PATH` | str | `/tmp/l9_spans.jsonl` | Path for file exporter output |
| `OBS_SUBSTRATE_ENABLED` | bool | `true` | Export to L9 Memory Substrate |
| `OBS_JAEGER_ENABLED` | bool | `false` | Export to Jaeger for distributed tracing |
| `OBS_JAEGER_ENDPOINT` | str | None | Jaeger OTLP endpoint (default: http://jaeger:4318/v1/traces) |
| `OBS_DATADOG_ENABLED` | bool | `false` | Export to Datadog APM |
| `OBS_DATADOG_API_KEY` | str | None | Datadog API key (required if datadog enabled) |
| `OBS_CONTEXT_STRATEGY_DEFAULT` | str | `recency_biased_window` | Default context strategy |
| `OBS_CONTEXT_MAX_TOKENS` | int | `8000` | Maximum tokens in assembled context |
| `OBS_ENABLE_CIRCUIT_BREAKER` | bool | `true` | Enable circuit breaker for failure recovery |
| `OBS_ENABLE_BACKOFF_RETRY` | bool | `true` | Enable exponential backoff retry |
| `OBS_CIRCUIT_BREAKER_THRESHOLD` | int | `5` | Failures before circuit opens |
| `OBS_CIRCUIT_BREAKER_WINDOW_SEC` | int | `60` | Time window for failure counting |

## Example Configuration

### Development (verbose, all local)

```bash
L9_OBSERVABILITY=true
OBS_ENABLED=true
OBS_SAMPLING_RATE=1.0
OBS_EXPORTERS=console,file
OBS_LOG_LEVEL=DEBUG
```

### Production (sampled, substrate + external APM)

```bash
L9_OBSERVABILITY=true
OBS_ENABLED=true
OBS_SAMPLING_RATE=0.10
OBS_ERROR_SAMPLING_RATE=1.0
OBS_EXPORTERS=substrate,datadog
OBS_DATADOG_ENABLED=true
OBS_DATADOG_API_KEY=your-datadog-api-key
OBS_LOG_LEVEL=INFO
```

### Minimal (console only, low overhead)

```bash
L9_OBSERVABILITY=true
OBS_ENABLED=true
OBS_SAMPLING_RATE=0.01
OBS_EXPORTERS=console
```

## Span Types

The module provides 7 specialized span types:

| Span Type | Description | Use Case |
|-----------|-------------|----------|
| `TraceContext` | W3C Trace Context with trace_id, span_id | Request correlation |
| `LLMGenerationSpan` | LLM API calls with model, tokens, latency | AI cost tracking |
| `ToolCallSpan` | Tool executions with args, result, duration | Tool audit |
| `ContextAssemblySpan` | Context window construction | Memory optimization |
| `RAGRetrievalSpan` | Vector search with hits, scores | Retrieval tuning |
| `GovernanceCheckSpan` | Policy evaluations | Security audit |
| `AgentTrajectorySpan` | Full agent task trajectory | Debugging |

## Failure Classes

The module detects 12 failure classes:

| Class | Description | Recovery Action |
|-------|-------------|-----------------|
| `TOOL_TIMEOUT` | Tool call exceeded timeout | Retry with backoff |
| `TOOL_ERROR` | Tool returned error | Fallback tool |
| `LLM_RATE_LIMIT` | Rate limited by LLM provider | Exponential backoff |
| `LLM_CONTEXT_LENGTH` | Context exceeded max tokens | Summarize context |
| `LLM_CONTENT_FILTER` | Content blocked by filter | Rephrase request |
| `GOVERNANCE_DENIED` | Policy denied action | Escalate to Igor |
| `MEMORY_UNAVAILABLE` | Memory substrate down | Degrade gracefully |
| `CONTEXT_WINDOW_EXCEEDED` | Context too large | Apply context strategy |
| `AGENT_LOOP_DETECTED` | Agent stuck in loop | Force exit |
| `DEPENDENCY_FAILURE` | External dependency down | Circuit break |
| `AUTHENTICATION_FAILURE` | Auth failed | Re-authenticate |
| `UNKNOWN` | Unclassified error | Log and escalate |

## Context Strategies

6 strategies for context window optimization:

| Strategy | Description | Best For |
|----------|-------------|----------|
| `naive_truncation` | Simple head/tail truncation | Simple tasks |
| `recency_biased_window` | Prioritize recent context | Conversations |
| `hierarchical_summarization` | Summarize older context | Long sessions |
| `rag` | RAG-based retrieval | Knowledge tasks |
| `hybrid` | Combine recency + RAG | General use |
| `adaptive` | Auto-select based on task | Production |

## Programmatic Usage

```python
from core.observability import (
    trace_span,
    trace_llm_call,
    trace_tool_call,
    trace_governance_check,
    SpanKind,
)

# Decorate any async function
@trace_span("my.operation", kind=SpanKind.INTERNAL)
async def my_function():
    pass

# LLM call tracing
@trace_llm_call(model="gpt-4o")
async def call_llm(prompt: str):
    pass

# Tool call tracing
@trace_tool_call("memory_search")
async def search_memory(query: str):
    pass
```

## Integration with L9 Services

The module automatically instruments:

- `AgentExecutorService.start_agent_task()` - Agent task execution
- `ExecutorToolRegistry.dispatch_tool_call()` - Tool dispatch
- `GovernanceEngineService.evaluate()` - Policy evaluation
- `MemorySubstrateService.write_packet()` - Memory writes
- `MemorySubstrateService.semantic_search()` - Semantic search
- `MemorySubstrateService.get_packet()` - Packet retrieval

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    L9 Application Layer                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ Agent Exec  │ │ Tool Reg    │ │ Memory Substrate        ││
│  └──────┬──────┘ └──────┬──────┘ └───────────┬─────────────┘│
└─────────┼───────────────┼────────────────────┼──────────────┘
          │               │                    │
          ▼               ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Observability Layer                         │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌───────────┐│
│  │ Tracing    │ │ Failure    │ │ Context    │ │ Metrics   ││
│  │ Decorators │ │ Detection  │ │ Strategies │ │ Aggregator││
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬─────┘│
│        │              │              │              │       │
│        └──────────────┴──────────────┴──────────────┘       │
│                            │                                 │
│                    ┌───────┴───────┐                        │
│                    │ Span Exporter │                        │
│                    └───────┬───────┘                        │
└────────────────────────────┼────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
    ┌──────────┐      ┌──────────┐       ┌──────────┐
    │ Console  │      │ Substrate│       │ Datadog  │
    └──────────┘      └──────────┘       └──────────┘
```

## Related

- `l9/upgrades/packet_envelope/phase_2_observability.py` - OpenTelemetry/Jaeger integration (complementary)
- `telemetry/memory_metrics.py` - Prometheus metrics for memory operations
- `memory/tool_audit.py` - Tool invocation audit logging

