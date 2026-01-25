# C1 Kubernetes Deployment Plan

**Target Server:** C1 (Hetzner CPX32)
**Status:** PLAN LOCKED - Ready for execution

---

## Server Specifications

| Property | Value |
|----------|-------|
| **Name** | C1 |
| **Type** | CPX32 |
| **ID** | #114194366 |
| **vCPU** | 4 |
| **RAM** | 8 GB |
| **Disk** | 160 GB |
| **IPv4** | 46.62.243.82 |
| **IPv6** | 2a01:4f9:c012:54f2::/64 |
| **Location** | Helsinki, Finland (hel1-dc2) |
| **Price** | $11.99/mo |

---

## CONSTRAINTS (IMMUTABLE)

### ❌ OFF LIMITS - DO NOT TOUCH
```
Server: L9
Type: cx23
ID: #113739124
IPv4: 157.180.73.53
IPv6: 2a01:4f9:c012:d06c::/64
```

### ✅ Deployment Rules
- All actions on C1 must be **justified, repeatable, and rollback-able**
- No changes to L9 server
- K8s deployment (not Docker Compose - that's the logical upgrade path)

---

## Resource Budget (8GB Total)

| Component | Memory | CPU | Justification |
|-----------|--------|-----|---------------|
| **OS/System** | 1.0 GB | - | Ubuntu base |
| **k3s** | 0.5 GB | 0.5 | Lightweight K8s |
| **Neo4j** | 2.0 GB | 1.0 | 1GB heap + 0.5GB pagecache + overhead |
| **Redis** | 0.5 GB | 0.5 | Single instance, LRU eviction |
| **Orchestrator** | 2.5 GB | 1.5 | L9 AIOS core |
| **Prometheus** | 0.5 GB | 0.25 | Metrics collection |
| **Grafana** | 0.5 GB | 0.25 | Dashboards |
| **Buffer** | 0.5 GB | - | Safety margin |
| **TOTAL** | **8.0 GB** | **4.0** | ✅ Fits exactly |

---

## Deployment Phases

### Phase 1: Server Preparation
```bash
# SSH to C1
ssh root@46.62.243.82

# Update system
apt update && apt upgrade -y

# Install prerequisites
apt install -y curl wget git htop

# Set hostname
hostnamectl set-hostname c1-k8s
```

### Phase 2: k3s Installation
```bash
# Install k3s (single-node, no traefik - we'll use nginx-ingress)
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -

# Verify
kubectl get nodes
kubectl get pods -A
```

### Phase 3: Deploy L9 Stack
```bash
# Clone configs
mkdir -p /opt/l9-k8s
cd /opt/l9-k8s

# Apply manifests in order
kubectl apply -f c1-namespace.yaml
kubectl apply -f c1-secrets.yaml
kubectl apply -f c1-neo4j.yaml
kubectl apply -f c1-redis.yaml
kubectl apply -f c1-orchestrator.yaml
kubectl apply -f c1-monitoring.yaml
kubectl apply -f c1-ingress.yaml
```

### Phase 4: Verification
```bash
# Check all pods running
kubectl get pods -n l9-c1 -w

# Check services
kubectl get svc -n l9-c1

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:7474  # Neo4j browser
```

---

## Rollback Procedure

### Option 1: Full Namespace Delete (Clean Slate)
```bash
kubectl delete namespace l9-c1
# All resources deleted, PVCs retained
```

### Option 2: Individual Component Rollback
```bash
# Delete specific deployment
kubectl delete -f c1-orchestrator.yaml

# Re-apply previous version
kubectl apply -f c1-orchestrator.yaml.bak
```

### Option 3: k3s Full Reset
```bash
# Complete k3s uninstall
/usr/local/bin/k3s-uninstall.sh

# Server returns to clean state
```

---

## Differences from Original Manifests

| Aspect | Original | C1 Adapted | Reason |
|--------|----------|------------|--------|
| Neo4j replicas | 3 | 1 | Single node |
| Neo4j memory | 6Gi | 2Gi | Resource constraint |
| Redis replicas | 6 | 1 | Single node |
| Redis cluster | Yes | No | Single instance |
| Orchestrator replicas | 3 | 1 | Single node |
| GPU | nvidia.com/gpu: 1 | REMOVED | No GPU on CPX32 |
| Storage class | fast-nvme | local-path | k3s default |
| Anti-affinity | Yes | REMOVED | Single node |

---

## Files Created

```
c1-namespace.yaml      # Namespace: l9-c1
c1-secrets.yaml        # Secrets and ConfigMap
c1-neo4j.yaml          # Neo4j StatefulSet (1 replica)
c1-redis.yaml          # Redis Deployment (1 replica)  
c1-orchestrator.yaml   # L9 Orchestrator Deployment
c1-monitoring.yaml     # Prometheus + Grafana
c1-ingress.yaml        # Nginx Ingress
c1-deploy.sh           # One-click deployment script
c1-rollback.sh         # Rollback script
```

---

## Network Ports

| Port | Service | Access |
|------|---------|--------|
| 22 | SSH | Admin only |
| 80 | HTTP (Ingress) | Public |
| 443 | HTTPS (Ingress) | Public |
| 6379 | Redis | Internal only |
| 7474 | Neo4j Browser | Internal/VPN |
| 7687 | Neo4j Bolt | Internal only |
| 8000 | L9 Orchestrator | Via Ingress |
| 9090 | Prometheus | Internal/VPN |
| 3000 | Grafana | Via Ingress |

---

## Alignment with L9 Codebase

The deployment will run the **actual L9 codebase** (not the generic AIOS v5):

- `core/agents/executor.py` - Agent execution
- `memory/substrate_service.py` - Memory substrate
- `orchestration/unified_controller.py` - Orchestration
- `runtime/redis_client.py` - Redis integration
- `api/` - FastAPI routes

Docker image will be built from L9 repo, not the generic orchestrator.

---

**Plan Status:** ✅ LOCKED
**Ready for:** Phase 1 execution
