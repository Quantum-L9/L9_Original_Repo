# L9 Platform Deployment Guide

**Version:** 3.0.0
**Last Updated:** January 21, 2026
**Status:** Production-Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [CI/CD Setup](#cicd-setup)
7. [Monitoring & Observability](#monitoring--observability)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## 🎯 Overview

This guide covers deploying the L9 Agentic Intelligence Platform using:

- **Docker Compose** (local development, single-server)
- **Kubernetes + Helm** (production, multi-server)
- **GitHub Actions** (CI/CD automation)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     L9 Platform                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐          │
│  │ L9 API   │  │ MCP Memory   │  │ Monitoring  │          │
│  │ (FastAPI)│  │ (FastAPI)    │  │ (Prom/Graf) │          │
│  └────┬─────┘  └──────┬───────┘  └──────┬──────┘          │
│       │                │                  │                  │
│  ┌────┴────────────────┴──────────────────┴──────┐          │
│  │         Data Layer                             │          │
│  │  ┌──────────┐ ┌───────┐ ┌────────┐           │          │
│  │  │PostgreSQL│ │ Redis │ │ Neo4j  │           │          │
│  │  │+pgvector │ │       │ │        │           │          │
│  │  └──────────┘ └───────┘ └────────┘           │          │
│  └────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ Prerequisites

### Required Tools

| Tool           | Version | Purpose                              |
| -------------- | ------- | ------------------------------------ |
| Docker         | 24.0+   | Container runtime                    |
| Docker Compose | 2.20+   | Multi-container orchestration        |
| Kubernetes     | 1.28+   | Container orchestration (production) |
| Helm           | 3.13+   | Kubernetes package manager           |
| kubectl        | 1.28+   | Kubernetes CLI                       |
| Git            | 2.40+   | Version control                      |

### System Requirements

**Development:**

- CPU: 4 cores
- RAM: 8 GB
- Disk: 20 GB

**Production:**

- CPU: 16+ cores
- RAM: 32+ GB
- Disk: 200+ GB SSD

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/cryptoxdog/L9.git
cd L9
```

### 2. Configure Environment

```bash
# Copy environment template
cp deploy/docker-production/.env.production.template .env.production

# Edit with your values
nano .env.production
```

**Required variables:**

- `POSTGRES_PASSWORD` - Strong password for PostgreSQL
- `NEO4J_PASSWORD` - Strong password for Neo4j
- `OPENAI_API_KEY` - Your OpenAI API key
- `L9_API_KEY` - Random string for API authentication
- `GRAFANA_PASSWORD` - Strong password for Grafana

### 3. Start Services

```bash
# Development (docker-compose.yml)
docker-compose up -d

# Production (optimized)
docker-compose --env-file .env.production \
  -f deploy/docker-production/docker-compose.production.yml up -d
```

### 4. Verify Deployment

```bash
# Check all services are running
docker-compose ps

# Check API health
curl http://localhost:8000/health

# Check MCP Memory health
curl http://localhost:9002/health
```

### 5. Access Services

| Service       | URL                    | Credentials         |
| ------------- | ---------------------- | ------------------- |
| L9 API        | http://localhost:8000  | API Key             |
| MCP Memory    | http://localhost:9002  | API Key             |
| Grafana       | http://localhost:3000  | admin / (from .env) |
| Prometheus    | http://localhost:9090  | None                |
| Jaeger UI     | http://localhost:16686 | None                |
| Neo4j Browser | http://localhost:7474  | neo4j / (from .env) |

---

## 🐳 Docker Deployment

### Development Setup

**File:** `docker-compose.yml` (root directory)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f l9-api

# Stop services
docker-compose down

# Clean up (including volumes)
docker-compose down -v
```

### Production Setup

**File:** `deploy/docker-production/docker-compose.production.yml`

**Features:**

- Multi-stage Dockerfiles (70% smaller images)
- Resource limits
- Health checks
- Optimized caching
- Security hardening

```bash
# Build production images
docker-compose -f deploy/docker-production/docker-compose.production.yml build

# Start with environment file
docker-compose --env-file .env.production \
  -f deploy/docker-production/docker-compose.production.yml up -d

# View resource usage
docker stats

# Update to new version
docker-compose -f deploy/docker-production/docker-compose.production.yml pull
docker-compose -f deploy/docker-production/docker-compose.production.yml up -d
```

### Docker Image Management

```bash
# Build specific image
docker build -f deploy/docker-production/Dockerfile.l9-api -t l9-api:3.0.0 .

# Tag for registry
docker tag l9-api:3.0.0 ghcr.io/cryptoxdog/l9-api:3.0.0

# Push to registry
docker push ghcr.io/cryptoxdog/l9-api:3.0.0

# Pull from registry
docker pull ghcr.io/cryptoxdog/l9-api:3.0.0
```

---

## ☸️ Kubernetes Deployment

### Prerequisites

1. **Kubernetes cluster** (EKS, GKE, AKS, or self-hosted)
2. **kubectl** configured with cluster access
3. **Helm 3.13+** installed
4. **Storage class** available (for persistent volumes)
5. **Ingress controller** (nginx recommended)
6. **Cert-manager** (for TLS certificates)

### Setup Cluster

```bash
# Verify cluster access
kubectl cluster-info
kubectl get nodes

# Create namespace
kubectl create namespace l9-prod

# Set default namespace
kubectl config set-context --current --namespace=l9-prod
```

### Install Cert-Manager (for TLS)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@l9.ai
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### Create Secrets

```bash
# Create secrets from .env file
kubectl create secret generic l9-secrets \
  --from-literal=postgres-user=l9_user \
  --from-literal=postgres-password=YOUR_PASSWORD \
  --from-literal=neo4j-user=neo4j \
  --from-literal=neo4j-password=YOUR_PASSWORD \
  --from-literal=openai-api-key=YOUR_KEY \
  --from-literal=l9-api-key=YOUR_KEY \
  --from-literal=grafana-password=YOUR_PASSWORD \
  -n l9-prod

# Verify secrets
kubectl get secrets -n l9-prod
```

### Deploy with Helm

**Development:**

```bash
cd deploy/helm

# Install
helm install l9-dev ./l9-platform \
  -f ./l9-platform/values-dev.yaml \
  --namespace l9-dev \
  --create-namespace

# Verify
helm list -n l9-dev
kubectl get pods -n l9-dev
```

**Production:**

```bash
cd deploy/helm

# Install
helm install l9-prod ./l9-platform \
  -f ./l9-platform/values-production.yaml \
  --namespace l9-prod \
  --create-namespace \
  --wait \
  --timeout 15m

# Verify
helm list -n l9-prod
kubectl get pods -n l9-prod
kubectl get ingress -n l9-prod
```

### Upgrade Deployment

```bash
# Upgrade to new version
helm upgrade l9-prod ./l9-platform \
  -f ./l9-platform/values-production.yaml \
  --namespace l9-prod \
  --set api.image.tag=3.1.0 \
  --set mcpMemory.image.tag=3.1.0

# Rollback if needed
helm rollback l9-prod -n l9-prod

# View history
helm history l9-prod -n l9-prod
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment l9-prod-api --replicas=5 -n l9-prod

# HPA (Horizontal Pod Autoscaler) - already configured in values-production.yaml
kubectl get hpa -n l9-prod

# View autoscaling events
kubectl describe hpa l9-prod-api -n l9-prod
```

---

## 🔄 CI/CD Setup

### GitHub Actions Workflows

**Location:** `.github/workflows/`

**Workflows:**

1. `docker-build.yml` - Build and push Docker images
2. `k8s-deploy.yml` - Deploy to Kubernetes

### Setup GitHub Secrets

**Repository Settings → Secrets → Actions:**

| Secret               | Description                           |
| -------------------- | ------------------------------------- |
| `KUBECONFIG_DEV`     | Kubernetes config for dev cluster     |
| `KUBECONFIG_STAGING` | Kubernetes config for staging cluster |
| `KUBECONFIG_PROD`    | Kubernetes config for prod cluster    |
| `SLACK_WEBHOOK`      | Slack webhook for notifications       |

### Deployment Flow

```
┌──────────────┐
│ Push to main │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Docker Build     │ ← Build images
│ - L9 API         │
│ - MCP Memory     │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Security Scan    │ ← Trivy scan
│ - Vulnerabilities│
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Deploy Staging   │ ← Auto deploy
│ - Smoke tests    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Manual Approval  │ ← Required
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Deploy Production│ ← Blue-green
│ - Traffic switch │
└──────────────────┘
```

### Manual Deployment

```bash
# Trigger deployment via GitHub UI
# Actions → Kubernetes Deployment → Run workflow

# Or via GitHub CLI
gh workflow run k8s-deploy.yml \
  -f environment=production \
  -f version=3.0.0
```

---

## 📊 Monitoring & Observability

### Prometheus Metrics

**Access:** http://localhost:9090 (Docker) or https://prometheus.l9.ai (K8s)

**Key Metrics:**

- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `process_cpu_seconds_total` - CPU usage
- `process_resident_memory_bytes` - Memory usage
- `postgres_connections` - Database connections

### Grafana Dashboards

**Access:** http://localhost:3000 (Docker) or https://grafana.l9.ai (K8s)

**Default Dashboards:**

1. L9 API Overview
2. Database Performance
3. Redis Metrics
4. Neo4j Metrics
5. Kubernetes Cluster

### Jaeger Tracing

**Access:** http://localhost:16686 (Docker) or https://jaeger.l9.ai (K8s)

**Features:**

- Distributed tracing
- Service dependencies
- Latency analysis
- Error tracking

### Log Aggregation

**Docker:**

```bash
# View logs
docker-compose logs -f l9-api

# Search logs
docker-compose logs l9-api | grep ERROR
```

**Kubernetes:**

```bash
# View logs
kubectl logs -f deployment/l9-prod-api -n l9-prod

# Tail logs from all pods
kubectl logs -f -l app=l9-api -n l9-prod --all-containers=true

# Search logs
kubectl logs deployment/l9-prod-api -n l9-prod | grep ERROR
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. API Not Starting

**Symptoms:**

- Container restarts repeatedly
- Health check fails

**Solutions:**

```bash
# Check logs
docker-compose logs l9-api

# Check environment variables
docker-compose exec l9-api env | grep DATABASE_URL

# Verify database connection
docker-compose exec l9-api python -c "import asyncpg; print('OK')"
```

#### 2. Database Connection Failed

**Symptoms:**

- `could not connect to server`
- `password authentication failed`

**Solutions:**

```bash
# Check PostgreSQL is running
docker-compose ps l9-postgres

# Check PostgreSQL logs
docker-compose logs l9-postgres

# Test connection
docker-compose exec l9-postgres psql -U l9_user -d l9_memory -c "SELECT 1"

# Reset password
docker-compose exec l9-postgres psql -U postgres -c "ALTER USER l9_user PASSWORD 'newpassword'"
```

#### 3. Out of Memory

**Symptoms:**

- OOMKilled pods
- Slow performance

**Solutions:**

```bash
# Check resource usage
docker stats

# Kubernetes
kubectl top pods -n l9-prod

# Increase memory limits
# Edit values-production.yaml and upgrade
helm upgrade l9-prod ./l9-platform -f values-production.yaml
```

#### 4. Image Pull Failed

**Symptoms:**

- `ImagePullBackOff`
- `ErrImagePull`

**Solutions:**

```bash
# Check image exists
docker pull ghcr.io/cryptoxdog/l9-api:3.0.0

# Check image pull secrets
kubectl get secrets -n l9-prod

# Create image pull secret
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_USERNAME \
  --docker-password=YOUR_TOKEN \
  -n l9-prod
```

---

## ✅ Best Practices

### Security

1. **Never commit secrets** - Use `.env` files (gitignored)
2. **Use strong passwords** - 32+ characters, random
3. **Enable TLS** - Use cert-manager for automatic certificates
4. **Scan images** - Trivy scan in CI/CD
5. **Run as non-root** - Already configured in Dockerfiles
6. **Network policies** - Restrict pod-to-pod communication

### Performance

1. **Resource limits** - Set appropriate CPU/memory limits
2. **HPA** - Enable horizontal pod autoscaling
3. **Connection pooling** - Already configured (asyncpg)
4. **Caching** - Use Redis for frequently accessed data
5. **Database indexes** - Ensure proper indexes on queries
6. **Monitoring** - Set up alerts for high resource usage

### Reliability

1. **Health checks** - Liveness and readiness probes
2. **PDB** - Pod Disruption Budget for safe updates
3. **Backups** - Daily automated backups
4. **Blue-green deployments** - Zero-downtime updates
5. **Rollback plan** - Test rollback procedures
6. **Disaster recovery** - Document and test DR procedures

### Operations

1. **Version tagging** - Use semantic versioning (v3.0.0)
2. **Change logs** - Document all changes
3. **Runbooks** - Document common operations
4. **On-call rotation** - 24/7 coverage for production
5. **Incident response** - Document incident procedures
6. **Post-mortems** - Learn from incidents

---

## 📞 Support

**Documentation:** https://github.com/cryptoxdog/L9/tree/main/docs
**Issues:** https://github.com/cryptoxdog/L9/issues
**Discussions:** https://github.com/cryptoxdog/L9/discussions

---

**Last Updated:** January 21, 2026
**Version:** 3.0.0
**Status:** Production-Ready
