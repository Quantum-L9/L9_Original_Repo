# ADR 0058: C1 Kubernetes Deployment Workflow

- **Status**: Accepted
- **Date**: 2026-01-22
- **Deciders**: Igor Beylin
- **GMP**: c1-infrastructure

## Context and Problem Statement

C1 is a Hetzner CPX32 server (8GB RAM, 4 vCPU) designated as the Kubernetes deployment target for L9. The deployment requires Docker images for L9 API and MCP Memory services.

### Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | Build on Mac, push to GHCR, pull on C1 | Standard CI/CD pattern | Requires GHCR auth setup |
| B | Build on Mac, SCP tar to C1, import | Fast, no auth needed | Copies codebase via SCP |
| C | Commit to Git, pull on C1, build on C1 | Clean separation, reproducible | Requires Docker on C1 |

## Decision

**Option C: Git-based deployment workflow**

```
Mac (Dev) ─── git push ───> GitHub ─── git pull ───> C1 (Build & Run)
```

### Workflow

1. **Development (Mac)**
   - Make code changes
   - Test locally
   - Commit and push to GitHub

2. **Deployment (C1)**
   - Pull latest from GitHub
   - Build Docker image on C1
   - Import to containerd (k3s)
   - Update K8s deployment

### Rationale

- **No codebase transfer via SCP** - Code flows through Git only
- **Reproducible** - Same Git commit = same build anywhere
- **Audit trail** - All changes tracked in Git history
- **Clean separation** - Dev environment stays on Mac, production on C1
- **No external registry dependency** - Build locally on C1

## Implementation

### Prerequisites on C1

```bash
# Install Docker (for building)
apt-get update
apt-get install -y docker.io

# Configure Git (if private repo)
# SSH key or PAT for GitHub access
```

### Deployment Commands

```bash
# On C1
cd /opt/l9
git pull origin main

# Build
docker build -f Dockerfile.C1 -t l9-api:latest .

# Import to containerd (k3s uses containerd)
docker save l9-api:latest | ctr -n k8s.io images import -

# Restart deployment
kubectl rollout restart deployment/l9-api -n l9-c1
```

### K8s Manifest Update

Change image reference from:
```yaml
image: ghcr.io/igor-beylin/l9-api:latest
```

To:
```yaml
image: l9-api:latest
imagePullPolicy: Never  # Use local image
```

## Consequences

### Positive
- Clean Git-based workflow
- No secrets needed for container registry
- Full control over build process
- Easy rollback via Git

### Negative
- Requires Docker installed on C1 (uses disk/memory)
- Manual deployment steps (can automate later)
- Build time on C1 (not pre-built)

### Mitigations
- Docker only needed during build, can be stopped after
- Create deployment script for automation
- Consider CI/CD pipeline (GitHub Actions) for future

## Related

- ADR-057: K8s Migration from Docker Compose
- `Dockerfile.C1` - Production Dockerfile
- `c1-deploy.sh` - Deployment script

## Changelog

| Date | Change |
|------|--------|
| 2026-01-22 | Initial decision |
