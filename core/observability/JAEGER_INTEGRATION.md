# Jaeger Integration for Five-Tier Observability

## ✅ Complete Integration

The Five-Tier Observability system now exports to **all three** open source tools:

1. **Prometheus** - Metrics (counters, histograms, gauges)
2. **Grafana** - Visualization dashboards
3. **Jaeger** - Distributed tracing (spans and traces)

## How It Works

### Data Flow

```
Five-Tier Observability Spans
  ↓
┌─────────────────────────────────────┐
│  ObservabilityService.export_span() │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ↓                ↓
┌──────────────┐  ┌──────────────┐
│  Prometheus  │  │    Jaeger    │
│  (Metrics)   │  │  (Tracing)   │
└──────┬───────┘  └──────┬───────┘
       │                 │
       └────────┬────────┘
                ↓
         ┌──────────┐
         │ Grafana  │
         │(Visualize)│
         └──────────┘
```

### What Gets Exported Where

| Data Type | Prometheus | Jaeger | Grafana |
|-----------|------------|--------|---------|
| **Span counts** | ✅ Counter | ✅ Spans | ✅ Dashboard |
| **Span latency** | ✅ Histogram | ✅ Duration | ✅ Dashboard |
| **Errors** | ✅ Counter | ✅ Status | ✅ Dashboard |
| **LLM calls** | ✅ Metrics | ✅ Spans | ✅ Dashboard |
| **Tool calls** | ✅ Metrics | ✅ Spans | ✅ Dashboard |
| **Trace context** | ❌ | ✅ Full traces | ✅ (via Jaeger) |
| **Span relationships** | ❌ | ✅ Parent/child | ✅ (via Jaeger) |

## Configuration

### Enable Jaeger Export

Set environment variables:

```bash
# Enable Jaeger exporter
OBS_JAEGER_ENABLED=true

# Or add to exporters list
OBS_EXPORTERS=console,substrate,jaeger

# Optional: Custom Jaeger endpoint (default: http://jaeger:4318/v1/traces)
OBS_JAEGER_ENDPOINT=http://jaeger:4318/v1/traces
```

### Docker Compose

Jaeger is already configured in `docker-compose.yml`:

```yaml
jaeger:
  image: jaegertracing/all-in-one:1.52
  environment:
    COLLECTOR_OTLP_ENABLED: "true"  # ← OTLP enabled!
  ports:
    - "127.0.0.1:16686:16686"      # Jaeger UI
    - "127.0.0.1:14268:14268"      # Collector HTTP
    - "127.0.0.1:6831:6831/udp"     # Agent UDP
```

## Accessing Jaeger UI

### Via SSH Port Forwarding

```bash
# Forward Jaeger UI port
ssh -L 16686:localhost:16686 root@157.180.73.53
```

Then access: `http://localhost:16686`

### What You'll See in Jaeger

1. **Service List** - All services sending traces
2. **Trace Search** - Search by service, operation, tags, duration
3. **Trace Timeline** - Visual timeline of spans
4. **Span Details** - Full span attributes, logs, tags
5. **Service Map** - Dependency graph between services

## Span Details in Jaeger

Each span exported includes:

- **Basic Info:** name, trace_id, span_id, parent_span_id
- **Timing:** start_time, end_time, duration_ms
- **Status:** OK or ERROR (with error message)
- **Attributes:** All custom attributes from the span
- **Specialized Data:**
  - LLM spans: model, tokens, cost
  - Tool spans: tool_name, input parameters
  - Context spans: strategy, tokens_used

## Example: Viewing a Trace

1. **Open Jaeger UI:** `http://localhost:16686`
2. **Select Service:** `l9-observability`
3. **Search Traces:** Filter by operation (e.g., `tool.search`)
4. **View Timeline:** See span hierarchy and timing
5. **Inspect Span:** Click span to see all attributes

## Complete Observability Stack

You now have a **complete open source observability stack**:

| Tool | Purpose | Access |
|------|---------|--------|
| **Prometheus** | Metrics collection | `http://localhost:9090` |
| **Grafana** | Metrics visualization | `http://localhost:3000` |
| **Jaeger** | Distributed tracing | `http://localhost:16686` |

All three work together:
- **Prometheus** collects metrics from spans
- **Grafana** visualizes metrics in dashboards
- **Jaeger** shows full trace context and relationships

## Dependencies

Jaeger exporter requires:
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
```

These are optional - if not installed, Jaeger export is gracefully disabled.

## Benefits of Three-Tool Integration

1. **Prometheus** - Fast metrics queries, alerting, aggregation
2. **Grafana** - Beautiful dashboards, historical trends, KPIs
3. **Jaeger** - Full trace context, debugging, service dependencies

Together, they provide:
- ✅ Metrics (Prometheus)
- ✅ Visualization (Grafana)
- ✅ Tracing (Jaeger)
- ✅ All open source
- ✅ All self-hosted
- ✅ All integrated with Five-Tier Observability

