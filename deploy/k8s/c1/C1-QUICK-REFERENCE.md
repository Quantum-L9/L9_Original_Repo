# C1 Quick Reference Card

## Server Info

| Property  | Value                   |
| --------- | ----------------------- |
| **Name**  | C1                      |
| **IP**    | 46.62.243.82            |
| **IPv6**  | 2a01:4f9:c012:54f2::/64 |
| **Specs** | 4 vCPU, 8GB RAM, 160GB  |

## ⚠️ OFF LIMITS

```
L9 Server: 157.180.73.53 - DO NOT TOUCH
```

---

## Access Endpoints (After Deployment)

| Service           | URL                                               | Purpose                    |
| ----------------- | ------------------------------------------------- | -------------------------- |
| **L9 API**        | http://46.62.243.82:30080                         | Core FastAPI application   |
| **MCP Memory**    | http://46.62.243.82:30902                         | Cursor IDE memory protocol |
| **PostgreSQL**    | postgresql://l9_user@46.62.243.82:30432/l9_memory | Memory substrate           |
| **Neo4j Browser** | http://46.62.243.82:30474                         | Knowledge graph UI         |
| **Neo4j Bolt**    | bolt://46.62.243.82:30687                         | Graph database connection  |
| **Grafana**       | http://46.62.243.82:30300                         | Metrics dashboards         |
| **Prometheus**    | http://46.62.243.82:30909                         | Metrics collection         |

---

## SSH Access

```bash
ssh root@46.62.243.82
```

---

## Deployment Commands

### Full Deployment

```bash
# Copy files to server
scp -r ./* root@46.62.243.82:/opt/l9-k8s/

# SSH and deploy
ssh root@46.62.243.82
cd /opt/l9-k8s
./c1-deploy.sh
```

### Check Status

```bash
kubectl get pods -n l9-c1 -w
kubectl get svc -n l9-c1
kubectl logs -n l9-c1 -l app=l9-orchestrator -f
```

### Rollback

```bash
./c1-rollback.sh                    # Interactive
./c1-rollback.sh --namespace        # Delete all
./c1-rollback.sh --full             # Uninstall k3s
```

---

## Default Credentials (CHANGE IN PRODUCTION!)

| Service    | Username | Password          |
| ---------- | -------- | ----------------- |
| PostgreSQL | l9_user  | C1_Postgres-2026! |
| Neo4j      | C1_neo4j | C1_Neo4j-2026!    |
| Grafana    | admin | C1_Grafana-2026!  |

## **All credentials stored in:** `.env.c1.hetzner`

## Resource Allocation

| Component  | Memory  | CPU   |
| ---------- | ------- | ----- |
| k3s        | 0.5GB   | 0.5   |
| PostgreSQL | 1.0GB   | 0.5   |
| Neo4j      | 2.0GB   | 1.0   |
| Redis      | 0.5GB   | 0.5   |
| L9 API     | 2.0GB   | 1.5   |
| MCP Memory | 0.5GB   | 0.5   |
| Prometheus | 0.5GB   | 0.25  |
| Grafana    | 0.25GB  | 0.2   |
| OS/Buffer  | 0.75GB  | -     |
| **Total**  | **8GB** | **5** |

**Note:** CPU is overprovisioned (5 > 4 vCPU) - OK for burst workloads

---

## Files Created

```
c1-namespace.yaml       # Kubernetes namespace
c1-secrets.yaml         # Secrets & ConfigMap
c1-postgres.yaml        # PostgreSQL + pgvector (memory substrate)
c1-neo4j.yaml          # Neo4j StatefulSet
c1-redis.yaml          # Redis Deployment
c1-l9-api.yaml         # L9 FastAPI application
c1-mcp-memory.yaml     # MCP Memory Server
c1-monitoring.yaml     # Prometheus + Grafana
c1-ingress.yaml        # NodePort services
c1-full-deploy.sh      # Full automated deployment
c1-rollback.sh         # Rollback script
.env.c1.hetzner        # All credentials + Hetzner API
C1-DEPLOYMENT-PLAN.md  # Full deployment plan
C1-QUICK-REFERENCE.md  # This file
```

---

## Troubleshooting

### Pod not starting?

```bash
kubectl describe pod -n l9-c1 <pod-name>
kubectl logs -n l9-c1 <pod-name>
```

### Out of memory?

```bash
kubectl top pods -n l9-c1
free -h  # On the server
```

### Can't access endpoints?

```bash
# Check services
kubectl get svc -n l9-c1

# Check firewall
nc -zv 46.62.243.82 30800

# Check from server locally
curl http://localhost:30800/health
```

### Full reset?

```bash
./c1-rollback.sh --full
# Then re-run ./c1-deploy.sh
```
