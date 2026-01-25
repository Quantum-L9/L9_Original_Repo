# L9 Docker Quick Start Guide

**Version:** 1.0.0  
**Last Updated:** 2026-01-25  
**Purpose:** Get L9 containers running in 5 minutes  

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Setup Environment (2 minutes)
```bash
# Run automated setup script
./scripts/setup-docker-env.sh

# This will:
# - Create .env file from template
# - Generate secure passwords
# - Prompt for OpenAI API key
```

### Step 2: Start Containers (2 minutes)
```bash
# Start all services
docker compose up -d

# Wait for healthchecks (30-60 seconds)
watch docker compose ps
```

### Step 3: Verify (1 minute)
```bash
# Check all services are healthy
docker compose ps

# Test L9 API
curl http://localhost:8000/health

# Test MCP Memory
curl http://localhost:9002/health
```

**Done!** 🎉

---

## 📊 Service Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **L9 API** | http://localhost:8000 | API key in .env |
| **MCP Memory** | http://localhost:9002 | API key in .env |
| **Prometheus** | http://localhost:9090 | None |
| **Grafana** | http://localhost:3000 | admin / (see .env) |
| **Jaeger UI** | http://localhost:16686 | None |
| **Neo4j Browser** | http://localhost:7474 | neo4j / (see .env) |

---

## 🐛 Troubleshooting

### Problem: Containers Won't Start

**Symptom:**
```bash
$ docker compose ps
NAME           STATUS
l9-api         Exited (1)
l9-mcp-memory  Exited (1)
```

**Cause #1: Missing .env file**
```bash
# Check if .env exists
ls -la .env

# If missing, run setup script
./scripts/setup-docker-env.sh
```

**Cause #2: Invalid credentials in .env**
```bash
# Check for placeholder values
grep "YOUR_.*_HERE" .env
grep "CHANGE_ME" .env

# If found, edit .env and replace with real values
nano .env
```

**Cause #3: Port conflicts**
```bash
# Check if ports are already in use
lsof -i :8000  # L9 API
lsof -i :9002  # MCP Memory
lsof -i :5432  # PostgreSQL
lsof -i :7687  # Neo4j

# If in use, stop conflicting services or change ports in .env
```

---

### Problem: Containers Start But Fail Healthcheck

**Symptom:**
```bash
$ docker compose ps
NAME           STATUS
l9-api         Up (unhealthy)
```

**Solution:**
```bash
# Check logs for errors
docker compose logs l9-api

# Common errors and fixes:
# - "Connection refused" → Database not ready, wait 30s
# - "Authentication failed" → Wrong password in .env
# - "Module not found" → Rebuild image: docker compose build
```

---

### Problem: Database Connection Errors

**Symptom:**
```
asyncpg.exceptions.InvalidPasswordError: password authentication failed
```

**Solution:**
```bash
# 1. Check .env has correct password
grep POSTGRES_PASSWORD .env

# 2. Restart postgres container
docker compose restart l9-postgres

# 3. Restart dependent services
docker compose restart l9-api l9-mcp-memory
```

---

### Problem: Slow Build Times

**Symptom:**
```
Building l9-api... (10 minutes)
```

**Solution:**
```bash
# Use Docker BuildKit for faster builds
export DOCKER_BUILDKIT=1
docker compose build

# Or use requirements-docker.txt (excludes playwright)
# Already configured in runtime/Dockerfile
```

---

## 📝 Manual Setup (Without Script)

If you prefer manual setup:

### 1. Create .env File
```bash
cp .env.docker .env
```

### 2. Edit .env
```bash
nano .env
```

Replace these values:
- `CHANGE_ME_SECURE_PASSWORD_HERE` → Strong PostgreSQL password
- `CHANGE_ME_NEO4J_PASSWORD_HERE` → Strong Neo4j password
- `YOUR_OPENAI_API_KEY_HERE` → Your OpenAI API key
- `YOUR_L9_API_KEY_HERE` → Generate with `openssl rand -hex 32`
- `YOUR_EXECUTOR_API_KEY_HERE` → Generate with `openssl rand -hex 32`

### 3. Start Containers
```bash
docker compose up -d
```

---

## 🔧 Advanced Configuration

### Use Host PostgreSQL (macOS)

Create `docker-compose.override.yml`:
```yaml
services:
  l9-api:
    environment:
      DATABASE_URL: postgresql://postgres:YOUR_PASSWORD@host.docker.internal:5432/l9_memory
      MEMORY_DSN: postgresql://postgres:YOUR_PASSWORD@host.docker.internal:5432/l9_memory
```

### Enable Slack Integration

In `.env`:
```bash
SLACK_APP_ENABLED=true
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret
# ... other Slack vars
```

### Enable Email Integration

In `.env`:
```bash
EMAIL_ENABLED=true
GMAIL_API_KEY=your-gmail-key
EMAIL_ADAPTER_SIGNING_SECRET=your-secret
```

---

## 📊 Monitoring

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f l9-api

# Last 100 lines
docker compose logs --tail=100 l9-api
```

### Check Resource Usage
```bash
docker stats
```

### Check Disk Usage
```bash
docker system df
```

---

## 🧹 Cleanup

### Stop Containers
```bash
docker compose down
```

### Stop and Remove Volumes (⚠️ Deletes all data)
```bash
docker compose down -v
```

### Remove Images
```bash
docker compose down --rmi all
```

### Full Cleanup
```bash
# Stop everything
docker compose down -v --rmi all

# Remove orphaned volumes
docker volume prune -f

# Remove orphaned networks
docker network prune -f
```

---

## 🎯 Production Deployment

For production deployment, see:
- `deploy/docker-production/` - Production-optimized Dockerfiles
- `deploy/helm/` - Kubernetes Helm charts
- `DEPLOYMENT_GUIDE.md` - Complete deployment documentation

---

## 📚 Related Documentation

- **docker-compose.yml** - Service definitions
- **.env.docker** - Environment template
- **runtime/Dockerfile** - L9 API Dockerfile
- **mcp_memory/Dockerfile** - MCP Memory Dockerfile
- **CONTAINER_LOADING_DIAGNOSIS.md** - Detailed troubleshooting

---

## 🆘 Getting Help

If containers still won't load:

1. **Check logs:** `docker compose logs`
2. **Check .env:** `cat .env | grep -v "^#" | grep -v "^$"`
3. **Check ports:** `docker compose ps`
4. **Check disk:** `docker system df`
5. **Ask for help:** Include logs and `docker compose ps` output

---

**Happy containerizing! 🐳**
