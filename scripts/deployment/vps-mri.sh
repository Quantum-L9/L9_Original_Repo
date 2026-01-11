#!/bin/bash
# =============================================================================
# L9 VPS MRI - Comprehensive System Diagnostic
# Version: 1.0.0
#
# USAGE (run on VPS):
#   cd /opt/l9 && bash deploy/vps-mri.sh
#
# Or paste entire script into terminal
# =============================================================================

set -uo pipefail  # Removed -e to continue on errors (diagnostic script should be resilient)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
}

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           L9 VPS MRI - COMPLETE SYSTEM DIAGNOSTIC              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo "Timestamp: $(date -Iseconds)"
echo "Hostname:  $(hostname)"
echo "User:      $(whoami)"
echo ""

# =============================================================================
# SECTION A: SYSTEM IDENTITY & RESOURCES
# =============================================================================

header "A1. SYSTEM IDENTITY"
uname -a
ip addr show | grep "inet " | head -3
echo ""

header "A2. DISK SPACE"
df -h / /opt/l9 /var 2>/dev/null | grep -v "^Filesystem" || df -h /
echo ""

header "A3. MEMORY"
free -h
echo ""

header "A4. LOAD"
uptime
echo ""

# =============================================================================
# SECTION B: NETWORK & PORTS
# =============================================================================

header "B1. ALL LISTENING PORTS"
sudo ss -tlnp 2>/dev/null | grep LISTEN || sudo netstat -tlnp 2>/dev/null | grep LISTEN
echo ""

header "B2. CRITICAL PORTS CHECK"
echo "Port 80 (HTTP):"
sudo ss -tlnp 2>/dev/null | grep ":80 " || echo "  Not listening"
echo "Port 443 (HTTPS):"
sudo ss -tlnp 2>/dev/null | grep ":443 " || echo "  Not listening"
echo "Port 5432 (PostgreSQL):"
sudo ss -tlnp 2>/dev/null | grep ":5432 " || echo "  Not listening"
echo "Port 6379 (Redis):"
sudo ss -tlnp 2>/dev/null | grep ":6379 " || echo "  Not listening"
echo "Port 7687 (Neo4j Bolt):"
sudo ss -tlnp 2>/dev/null | grep ":7687 " || echo "  Not listening"
echo "Port 8000 (L9 API):"
sudo ss -tlnp 2>/dev/null | grep ":8000 " || echo "  Not listening"
echo ""

header "B3. FIREWALL (UFW)"
sudo ufw status numbered 2>/dev/null || echo "UFW not installed/active"
echo ""

# =============================================================================
# SECTION C: REVERSE PROXY (CADDY vs NGINX)
# =============================================================================

header "C1. CADDY STATUS"
if systemctl is-active caddy &>/dev/null; then
    check "Caddy is RUNNING"
    sudo systemctl status caddy --no-pager 2>/dev/null | head -5
else
    warn "Caddy not running or not installed"
fi
echo ""

header "C2. CADDYFILE"
if [ -f /etc/caddy/Caddyfile ]; then
    check "Caddyfile exists"
    cat /etc/caddy/Caddyfile 2>/dev/null
else
    warn "No Caddyfile found"
fi
echo ""

header "C3. NGINX STATUS"
if systemctl is-active nginx &>/dev/null; then
    check "Nginx is RUNNING"
    sudo systemctl status nginx --no-pager 2>/dev/null | head -5
    echo ""
    echo "Nginx config:"
    sudo nginx -T 2>/dev/null | head -50
else
    echo "Nginx not running or not installed"
fi
echo ""

# =============================================================================
# SECTION D: DOCKER
# =============================================================================

header "D1. DOCKER VERSION"
docker --version 2>&1 || fail "Docker not installed"
docker compose version 2>&1 || fail "Docker Compose not installed"
echo ""

header "D2. DOCKER SERVICE"
if systemctl is-active docker &>/dev/null; then
    check "Docker daemon is RUNNING"
else
    fail "Docker daemon is NOT running"
fi
echo ""

header "D3. RUNNING CONTAINERS"
sudo docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Cannot list containers"
echo ""

header "D4. DOCKER IMAGES"
sudo docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>/dev/null | head -10
echo ""

header "D5. DOCKER NETWORKS"
sudo docker network ls 2>/dev/null
echo ""

# =============================================================================
# SECTION E: L9 APPLICATION
# =============================================================================

header "E1. L9 INSTALLATION"
if [ -d /opt/l9 ]; then
    check "/opt/l9 exists"
    ls -la /opt/l9 | head -15
else
    fail "/opt/l9 does not exist"
fi
echo ""

header "E2. L9 SYSTEMD SERVICE"
if [ -f /etc/systemd/system/l9.service ]; then
    check "l9.service exists"
    sudo systemctl status l9 --no-pager 2>/dev/null | head -8
    echo ""
    echo "Service file:"
    cat /etc/systemd/system/l9.service 2>/dev/null
else
    echo "No l9.service (using Docker instead?)"
fi
echo ""

header "E3. DOCKER-COMPOSE.YML"
for path in /opt/l9/docker-compose.yml /opt/l9/docker/docker-compose.yml; do
    if [ -f "$path" ]; then
        check "Found: $path"
        cat "$path"
        break
    fi
done
echo ""

header "E4. DOCKERFILE"
for path in /opt/l9/runtime/Dockerfile /opt/l9/docker/Dockerfile /opt/l9/Dockerfile; do
    if [ -f "$path" ]; then
        check "Found: $path"
        cat "$path"
        break
    fi
done
echo ""

header "E5. .ENV (SANITIZED)"
if [ -f /opt/l9/.env ]; then
    cat /opt/l9/.env 2>/dev/null | sed 's/=.*/=<REDACTED>/' | head -30
else
    warn "No .env file found"
fi
echo ""

header "E6. L9-API CONTAINER LOGS (last 30)"
sudo docker logs l9-api 2>&1 | tail -30 || echo "No l9-api container"
echo ""

# =============================================================================
# SECTION F: DATABASES
# =============================================================================

header "F1. POSTGRESQL"
if systemctl is-active postgresql &>/dev/null; then
    check "PostgreSQL systemd service is RUNNING"
elif sudo docker ps 2>/dev/null | grep -q postgres; then
    check "PostgreSQL running in Docker"
else
    warn "PostgreSQL status unknown"
fi
sudo ss -tlnp 2>/dev/null | grep 5432 || echo "Port 5432 not listening"
echo ""

header "F2. POSTGRESQL DATABASES"
sudo -u postgres psql -l 2>/dev/null | head -15 || echo "Cannot list databases (may be in Docker)"
echo ""

header "F3. L9_MEMORY TABLES"
sudo -u postgres psql l9_memory -c "SELECT table_name FROM information_schema.tables WHERE table_schema='memory';" 2>/dev/null || echo "Cannot query (may be in Docker)"
echo ""

header "F4. REDIS STATUS"
if sudo docker ps 2>/dev/null | grep -q redis; then
    check "Redis running in Docker"
    sudo docker exec l9-redis redis-cli ping 2>/dev/null || echo "Cannot ping Redis"
elif systemctl is-active redis &>/dev/null; then
    check "Redis systemd service is RUNNING"
else
    warn "Redis not detected"
fi
echo ""

header "F5. NEO4J STATUS"
if sudo docker ps 2>/dev/null | grep -q neo4j; then
    check "Neo4j running in Docker"
else
    warn "Neo4j not detected"
fi
echo ""

# =============================================================================
# SECTION G: PYTHON/UVICORN PROCESSES
# =============================================================================

header "G1. PYTHON/UVICORN PROCESSES"
ps aux | grep -E "python|uvicorn" | grep -v grep || echo "No Python/Uvicorn processes outside Docker"
echo ""

header "G2. PYTHON VERSION"
python3 --version 2>&1
echo ""

# =============================================================================
# SECTION H: CONNECTIVITY TESTS
# =============================================================================

header "H1. PUBLIC IP & DNS"
echo "Public IP:"
curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "Cannot reach ifconfig.me"
echo ""
echo "DNS resolution for l9.quantumaipartners.com:"
getent hosts l9.quantumaipartners.com 2>/dev/null || echo "DNS not resolving"
echo ""

header "H2. LOCAL HEALTH CHECK (bypass proxy)"
echo "http://127.0.0.1:8000/health:"
curl -fsS --max-time 5 http://127.0.0.1:8000/health 2>&1 || fail "Backend not responding"
echo ""

header "H3. PUBLIC HEALTH CHECK (through Caddy)"
echo "https://l9.quantumaipartners.com/health:"
curl -kfsS --max-time 10 https://l9.quantumaipartners.com/health 2>&1 || fail "Public endpoint not responding"
echo ""

header "H4. API ROUTES AVAILABLE"
curl -s --max-time 5 http://127.0.0.1:8000/openapi.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(sorted(d.get('paths',{}).keys())))" 2>/dev/null | head -20 || echo "Cannot fetch OpenAPI spec"
echo ""

# =============================================================================
# SECTION I: LOGS & ERRORS
# =============================================================================

header "I1. JOURNALCTL - L9 SERVICE (last 20)"
sudo journalctl -u l9 -n 20 --no-pager 2>/dev/null || echo "No l9 journal logs"
echo ""

header "I2. JOURNALCTL - CADDY ERRORS"
sudo journalctl -u caddy -n 20 --no-pager 2>/dev/null | grep -iE "error|warn|fail" || echo "No Caddy errors"
echo ""

header "I3. DOCKER CONTAINER ERRORS"
for container in l9-api l9-postgres l9-redis l9-neo4j; do
    if sudo docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${container}$"; then
        echo "--- $container ---"
        sudo docker logs "$container" 2>&1 | grep -iE "error|exception|fail|critical" | tail -5 || echo "No errors"
    fi
done
echo ""

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                     MRI DIAGNOSTIC COMPLETE                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Quick Status:"
echo "─────────────"

# Caddy/Nginx
if systemctl is-active caddy &>/dev/null; then
    check "Reverse Proxy: Caddy"
elif systemctl is-active nginx &>/dev/null; then
    check "Reverse Proxy: Nginx"
else
    fail "Reverse Proxy: NONE RUNNING"
fi

# Docker
if systemctl is-active docker &>/dev/null; then
    check "Docker: Running"
else
    fail "Docker: NOT Running"
fi

# L9 API
if curl -fs --max-time 3 http://127.0.0.1:8000/health &>/dev/null; then
    check "L9 API: Healthy"
else
    fail "L9 API: NOT Responding"
fi

# PostgreSQL
if sudo ss -tlnp 2>/dev/null | grep -q ":5432 "; then
    check "PostgreSQL: Listening"
else
    warn "PostgreSQL: Not detected on 5432"
fi

# Redis
if sudo ss -tlnp 2>/dev/null | grep -q ":6379 "; then
    check "Redis: Listening"
else
    warn "Redis: Not detected on 6379"
fi

# Neo4j
if sudo ss -tlnp 2>/dev/null | grep -q ":7687 "; then
    check "Neo4j: Listening"
else
    warn "Neo4j: Not detected on 7687"
fi

# Public endpoint
if curl -kfs --max-time 5 https://l9.quantumaipartners.com/health &>/dev/null; then
    check "Public HTTPS: Accessible"
else
    fail "Public HTTPS: NOT Accessible"
fi

echo ""
echo "Diagnostic completed at: $(date -Iseconds)"

