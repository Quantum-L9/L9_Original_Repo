# Deployment Guide

## Prerequisites

- Python 3.12+
- Redis 7+
- PostgreSQL 15+
- Neo4j 5+
- Access to TensorAIOS layer

## Installation

```bash
pip install -e .
```

## Docker

```yaml
services:
  domain-tensor-bridge:
    image: l9/domain-tensor-bridge:6.0.0
    environment:
      - L9_REDIS_URL=redis://redis:6379
      - L9_POSTGRES_URL=postgresql://user:pass@postgres/l9
      - L9_NEO4J_URL=bolt://neo4j:7687
      - L9_TENSOR_URL=http://tensoraios:8080
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - postgres
      - neo4j
```

## Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: domain-tensor-bridge
spec:
  replicas: 3
  selector:
    matchLabels:
      app: domain-tensor-bridge
  template:
    spec:
      containers:
        - name: bridge
          image: l9/domain-tensor-bridge:6.0.0
          envFrom:
            - secretRef:
                name: l9-secrets
```

## Health Checks

```bash
curl http://localhost:8000/bridge/health
```

## Monitoring

Metrics exposed at `/bridge/metrics` in Prometheus format.
