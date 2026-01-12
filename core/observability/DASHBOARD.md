# Five-Tier Observability Dashboard

## Overview

The Five-Tier Observability system now exports metrics to Prometheus, enabling visualization in Grafana.

## Access

### Grafana Dashboard

**URL:** `http://localhost:3000`

**Credentials:**
- Username: `admin` (default)
- Password: `admin` (default, set via `GRAFANA_PASSWORD` env var)

**Dashboard Name:** "L9 Five-Tier Observability"

The dashboard is auto-provisioned from `grafana/provisioning/dashboards/l9-five-tier-observability.json`.

### Prometheus UI (Optional)

**URL:** `http://localhost:9090`

View raw metrics and query Prometheus directly.

## Dashboard Panels

The dashboard includes 12 panels tracking:

### 1. Span Rate by Name
- **Metric:** `rate(l9_observability_spans_total[5m])`
- **Tracks:** Rate of spans by name and status
- **Labels:** `span_name`, `status`, `kind`

### 2. Span Latency (p50, p95, p99)
- **Metric:** `histogram_quantile()` on `l9_observability_span_duration_ms_bucket`
- **Tracks:** Latency percentiles by span name
- **Thresholds:** Green < 100ms, Yellow < 1000ms, Red >= 1000ms

### 3. Error Rate
- **Metric:** `l9_observability_error_rate`
- **Tracks:** Current error rate (0.0-1.0)
- **Thresholds:** Green < 1%, Yellow < 5%, Red >= 5%

### 4. P95 Latency
- **Metric:** `l9_observability_p95_latency_ms`
- **Tracks:** 95th percentile latency
- **Thresholds:** Green < 100ms, Yellow < 500ms, Red >= 500ms

### 5. P99 Latency
- **Metric:** `l9_observability_p99_latency_ms`
- **Tracks:** 99th percentile latency
- **Thresholds:** Green < 500ms, Yellow < 2000ms, Red >= 2000ms

### 6. Failure Signals by Class
- **Metric:** `rate(l9_observability_failure_signals_total[5m])`
- **Tracks:** Failure detection rate by failure class
- **Failure Classes:** TOOL_TIMEOUT, TOOL_ERROR, CONTEXT_WINDOW_EXCEEDED, GOVERNANCE_DENIED, etc.

### 7. LLM Calls by Model
- **Metric:** `rate(l9_observability_llm_calls_total[5m])`
- **Tracks:** LLM API call rate by model and status
- **Labels:** `model`, `status`

### 8. Agent Success Rate
- **Metric:** `l9_observability_agent_success_rate`
- **Tracks:** Success rate per agent (0.0-1.0)
- **Labels:** `agent_name`

### 9. LLM Cost (USD)
- **Metric:** `rate(l9_observability_llm_cost_usd[5m])`
- **Tracks:** LLM cost rate by model
- **Labels:** `model`

### 10. Span Count (Window)
- **Metric:** `l9_observability_span_count`
- **Tracks:** Current number of spans in the observation window

### 11. Error Count (Window)
- **Metric:** `l9_observability_error_count`
- **Tracks:** Current number of errors in the observation window

### 12. Context Assembly by Strategy
- **Metric:** `rate(l9_observability_context_assemblies_total[5m])`
- **Tracks:** Context window assembly rate by strategy
- **Strategies:** recency_biased_window, hierarchical_summarization, rag, hybrid, adaptive

## Metrics Exported

### Counters
- `l9_observability_spans_total` - Total spans (by name, status, kind)
- `l9_observability_errors_total` - Total errors (by span_name, failure_class)
- `l9_observability_failure_signals_total` - Failure signals (by failure_class)
- `l9_observability_llm_calls_total` - LLM calls (by model, status)
- `l9_observability_llm_tokens_total` - LLM tokens (by model, type)
- `l9_observability_llm_cost_usd` - LLM cost (by model)
- `l9_observability_tool_calls_total` - Tool calls (by tool_name, status)
- `l9_observability_context_assemblies_total` - Context assemblies (by strategy)

### Histograms
- `l9_observability_span_duration_ms` - Span duration (by span_name, kind)
- `l9_observability_context_tokens` - Context window size (by strategy)

### Gauges
- `l9_observability_span_count` - Current span count
- `l9_observability_error_count` - Current error count
- `l9_observability_error_rate` - Current error rate
- `l9_observability_p50_latency_ms` - 50th percentile latency
- `l9_observability_p95_latency_ms` - 95th percentile latency
- `l9_observability_p99_latency_ms` - 99th percentile latency
- `l9_observability_agent_success_rate` - Agent success rate (by agent_name)
- `l9_observability_agent_tool_efficiency` - Tool efficiency (by agent_name)
- `l9_observability_agent_cost_usd` - Agent cost (by agent_name)

## How It Works

1. **Span Collection:** Observability decorators (`@trace_span`, `@trace_llm_call`, etc.) create spans
2. **Prometheus Export:** Each span is recorded to Prometheus metrics via `ObservabilityPrometheusExporter`
3. **Metric Updates:** Every 30 seconds, SRE metrics and agent KPIs are computed and updated
4. **Prometheus Scraping:** Prometheus scrapes `/metrics` endpoint every 10s
5. **Grafana Visualization:** Grafana queries Prometheus and displays dashboards

## Configuration

The Prometheus exporter is automatically initialized when:
- `L9_OBSERVABILITY=true` (default)
- `prometheus_client` package is installed

No additional configuration needed - metrics are automatically exported to the existing `/metrics` endpoint.

## Comparison: Two Dashboards

| Dashboard | Purpose | Metrics Source |
|-----------|---------|----------------|
| **L9 Tool Observability** | Tool execution metrics | `telemetry/memory_metrics.py` |
| **L9 Five-Tier Observability** | Distributed tracing & observability | `core/observability/prometheus_exporter.py` |

Both dashboards are available in Grafana and complement each other:
- **Tool Observability:** Focuses on tool invocations, memory operations
- **Five-Tier Observability:** Focuses on spans, traces, failure detection, LLM calls, agent KPIs

