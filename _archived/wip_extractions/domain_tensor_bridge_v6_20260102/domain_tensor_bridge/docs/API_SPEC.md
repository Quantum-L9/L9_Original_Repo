# API Specification

## REST Endpoints

### POST /bridge/process

Process a packet through the reasoning pipeline.

**Request:**
```json
{
  "source_id": "plastos_agent",
  "kind": "REASONING",
  "payload": {
    "entity_id": "customer_123",
    "action": "risk_assessment"
  }
}
```

**Response:**
```json
{
  "source_id": "domain_tensor_bridge",
  "kind": "DECISION",
  "payload": {
    "result": {...},
    "confidence": 0.85,
    "reasoning_trace": [...]
  }
}
```

### GET /bridge/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "6.0.0",
  "components": {
    "reasoning_engine": "ok",
    "memory_bridge": "ok",
    "governance_bridge": "ok"
  }
}
```

### GET /bridge/metrics

Prometheus-compatible metrics.

## gRPC

See `proto/domain_tensor_bridge.proto` for gRPC definitions.


