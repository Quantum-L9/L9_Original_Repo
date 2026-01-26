# C1 Kubernetes Deployment

Target: **C1 Hetzner Server** (46.62.243.82)
Type: CPX32 (8GB RAM, 4 vCPU, 160GB SSD)
OS: Ubuntu 24.04 LTS
K8s: k3s

## Quick Start

```bash
# On C1 after git pull
cd deploy/k8s/c1

# Build L9 API image
docker build -t l9-api:latest -f Dockerfile .

# Import to k3s containerd
docker save l9-api:latest | ctr -n k8s.io images import -

# Deploy manifests
kubectl apply -f manifests/
```

## Structure

```
deploy/k8s/c1/
├── Dockerfile          # L9 API Docker image
├── README.md           # This file
├── C1-QUICK-REFERENCE.md
├── c1-firewall-rules.md
├── manifests/          # K8s YAML files
│   ├── c1-namespace.yaml
│   ├── c1-secrets.yaml
│   ├── c1-rbac.yaml
│   ├── c1-postgres.yaml
│   ├── c1-neo4j.yaml
│   ├── c1-redis.yaml
│   ├── c1-l9-api.yaml
│   ├── c1-mcp-memory.yaml
│   ├── c1-monitoring.yaml
│   ├── c1-ingress.yaml
│   └── c1-network-policy.yaml
└── scripts/
    ├── c1-deploy.sh      # Standard deployment
    ├── c1-full-deploy.sh # Full automation (includes server rebuild)
    └── c1-rollback.sh    # Rollback procedures
```

## Access Endpoints

| Service       | URL                       | Credentials                 |
| ------------- | ------------------------- | --------------------------- |
| Grafana       | http://46.62.243.82:30300 | C1_admin / C1_Grafana-2026! |
| Prometheus    | http://46.62.243.82:30909 | -                           |
| Neo4j Browser | http://46.62.243.82:30474 | neo4j / C1_Neo4j-2026!      |
| L9 API        | http://46.62.243.82:30080 | -                           |
| MCP Memory    | http://46.62.243.82:30902 | -                           |
| PostgreSQL    | 46.62.243.82:30432        | l9_user / C1_Postgres-2026! |

## Deployment Order

1. `c1-namespace.yaml` - Namespace
2. `c1-secrets.yaml` - Credentials + ConfigMap
3. `c1-rbac.yaml` - Service accounts
4. `c1-postgres.yaml` - Memory substrate
5. `c1-neo4j.yaml` - Knowledge graph
6. `c1-redis.yaml` - Cache/queue
7. `c1-l9-api.yaml` - Main API
8. `c1-mcp-memory.yaml` - MCP server
9. `c1-monitoring.yaml` - Prometheus + Grafana
10. `c1-ingress.yaml` - External access
11. `c1-network-policy.yaml` - Security policies

## Related

- ADR-058: C1 Deployment Workflow
- `/readme/DEPLOYMENT-PHILOSOPHY.md`
