# Prometheus + Grafana Complete Setup

## ✅ What's Already Configured

### 1. Prometheus (Metrics Collection)

- **Container:** `l9-prometheus`
- **Port:** `9090` (localhost only)
- **Config:** `docker/prometheus.yml`
- **Scraping:** L9 API `/metrics` endpoint every 10s

### 2. Grafana (Visualization)

- **Container:** `l9-grafana`
- **Port:** `3000` (localhost only)
- **Credentials:** `admin` / `admin` (or `GRAFANA_PASSWORD` env var)
- **Datasource:** Auto-provisioned Prometheus connection
- **Dashboards:** Auto-provisioned from `grafana/provisioning/dashboards/`

### 3. Metrics Being Collected

#### From Five-Tier Observability (`core/observability/prometheus_exporter.py`)

- `l9_observability_spans_total` - Span counts by name/status/kind
- `l9_observability_span_duration_ms` - Span latency histograms
- `l9_observability_errors_total` - Error counts
- `l9_observability_failure_signals_total` - Failure detection
- `l9_observability_llm_calls_total` - LLM API calls
- `l9_observability_llm_tokens_total` - Token usage
- `l9_observability_llm_cost_usd` - LLM costs
- `l9_observability_tool_calls_total` - Tool invocations
- `l9_observability_context_assemblies_total` - Context strategies
- `l9_observability_agent_success_rate` - Agent KPIs
- `l9_observability_agent_cost_usd` - Agent costs
- SRE metrics: error_rate, p50/p95/p99 latency, span_count, error_count

#### From Memory Substrate (`telemetry/memory_metrics.py`)

- `l9_memory_write_total` - Memory write operations
- `l9_memory_write_duration_seconds` - Write latency
- `l9_memory_search_total` - Search operations
- `l9_memory_search_hits` - Search result counts
- `l9_memory_substrate_healthy` - Health gauge
- `l9_packet_store_size` - Packet count

#### From Tool Registry

- `l9_tool_invocation_total` - Tool invocations by tool_id/status
- `l9_tool_invocation_duration_ms` - Tool latency histograms

### 4. Dashboards Available

1. **L9 Five-Tier Observability** (`l9-five-tier-observability`)

   - 12 panels covering spans, latency, errors, failures, LLM calls, agent KPIs, context strategies

2. **L9 Tool Observability** (`l9-tool-observability`)
   - 8 panels covering tool invocations, latency, errors, memory operations

## 📊 Accessing Dashboards

### From Your Mac (SSH Port Forwarding)

```bash
# Forward all observability ports
ssh -L 3000:localhost:3000 -L 9090:localhost:9090 -L 16686:localhost:16686 root@157.180.73.53
```

Then access:

- **Grafana:** `http://localhost:3000` (admin/admin)
- **Prometheus:** `http://localhost:9090`
- **Jaeger:** `http://localhost:16686` (for distributed tracing)

### Directly on VPS

If ports are exposed (change `127.0.0.1` to `0.0.0.0` in docker-compose.yml):

- **Grafana:** `http://157.180.73.53:3000`
- **Prometheus:** `http://157.180.73.53:9090`

## 🔧 Configuration Files

### Prometheus Config

**File:** `docker/prometheus.yml`

- Scrapes `l9-api:8000/metrics` every 10s
- Self-monitoring enabled
- Jaeger metrics (optional)

### Grafana Datasource

**File:** `grafana/provisioning/datasources/prometheus.yml`

- Auto-provisioned on startup
- Connects to `http://prometheus:9090`
- Set as default datasource

### Grafana Dashboards

**Directory:** `grafana/provisioning/dashboards/`

- `l9-five-tier-observability.json` - Five-Tier Observability dashboard
- `l9-tool-observability.json` - Tool observability dashboard
- Auto-loaded on startup

## 🚀 Verification

### Check Prometheus is Scraping

```bash
# On VPS
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

Should show:

- `l9-api` - health: "up"
- `prometheus` - health: "up"

### Check Metrics are Available

```bash
# Query Prometheus directly
curl 'http://localhost:9090/api/v1/query?query=l9_observability_spans_total' | jq
```

### Check Grafana Dashboards

1. Login to Grafana: `http://localhost:3000`
2. Go to **Dashboards** → **Browse**
3. Should see:
   - "L9 Five-Tier Observability"
   - "L9 Tool Observability"

## 📈 What You Can Monitor

### Application Metrics

- ✅ Request rates and latency
- ✅ Error rates and types
- ✅ Tool invocation patterns
- ✅ Memory operations
- ✅ LLM API usage and costs

### Infrastructure Metrics

- ✅ Container health
- ✅ Resource usage (if node_exporter added)
- ✅ Database connections (if postgres_exporter added)
- ✅ Redis operations (if redis_exporter added)

### Business Metrics

- ✅ Agent success rates
- ✅ Cost per agent/task
- ✅ Tool efficiency
- ✅ Context window optimization

## 🔄 Data Flow

```
L9 Application
  ↓ (creates spans/metrics)
ObservabilityService
  ↓ (exports to Prometheus)
Prometheus Exporter
  ↓ (updates Prometheus metrics)
/metrics endpoint
  ↓ (scraped every 10s)
Prometheus
  ↓ (queried by Grafana)
Grafana Dashboards
```

## 🎯 Everything Goes Through Prometheus + Grafana

**All observability data flows through this stack:**

- ✅ Five-Tier Observability spans → Prometheus metrics → Grafana
- ✅ Memory substrate operations → Prometheus metrics → Grafana
- ✅ Tool invocations → Prometheus metrics → Grafana
- ✅ LLM calls → Prometheus metrics → Grafana
- ✅ Agent KPIs → Prometheus metrics → Grafana

**No external services needed!** Everything is self-hosted and open source.

## 🔐 Security Notes

- Grafana password: Set via `GRAFANA_PASSWORD` env var
- Ports bound to `127.0.0.1` by default (localhost only)
- Use SSH port forwarding for secure remote access
- Or expose with strong password + firewall rules

## 📚 Next Steps

1. **Access VPS Grafana** via SSH port forwarding
2. **View dashboards** - both are auto-loaded
3. **Customize dashboards** - edit JSON files and restart Grafana
4. **Add alerts** - configure alerting rules in Prometheus
5. **Add more exporters** - Redis, PostgreSQL, Node metrics if needed
