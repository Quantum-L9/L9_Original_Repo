# Audit Scripts Difference

## Two Audit Scripts Explained

### 1. `scripts/audit_graphs.py` (Direct Database Access)

**Purpose:** Direct database connection audit

**Method:**
- Connects directly to PostgreSQL via `DATABASE_URL`
- Connects directly to Neo4j via `NEO4J_URI`
- Uses `asyncpg` and `neo4j` drivers
- Requires database credentials and network access

**When to Use:**
- ✅ Running on VPS (direct database access)
- ✅ Running locally with Docker (localhost databases)
- ✅ Development/testing with local databases

**Limitations:**
- ❌ Requires direct database access
- ❌ Won't work from remote locations without VPN/tunnel
- ❌ Needs database credentials in environment

**Status:** ⚠️ **BROKEN** - Tries to connect to `neo4j:7687` (Docker service name) which doesn't exist locally

---

### 2. `scripts/audit_graphs_vps.py` (VPS API Access)

**Purpose:** HTTP API-based audit

**Method:**
- Uses VPS HTTP API (`https://157.180.73.53:9001`)
- Authenticates with `L9_EXECUTOR_API_KEY`
- Makes REST API calls to `/api/v1/memory/*` endpoints
- No direct database access needed

**When to Use:**
- ✅ Running from anywhere (Mac, remote, etc.)
- ✅ No database credentials needed
- ✅ Works through firewall/network restrictions
- ✅ Production-safe (read-only API access)

**Limitations:**
- ⚠️ Limited to what API exposes
- ⚠️ Some queries may not be available via API
- ⚠️ Requires VPS to be accessible

**Status:** ✅ **WORKING** - Successfully audits all graphs via API

---

## Recommendation

**Use `audit_graphs_vps.py`** for all audits:
- Works from anywhere
- No database credentials needed
- Production-safe
- Already working and tested

**Keep `audit_graphs.py`** for:
- Future VPS-local execution
- Development with local Docker
- Direct database debugging

---

## Quick Reference

| Script | Access Method | Credentials | Location |
|--------|---------------|-------------|----------|
| `audit_graphs.py` | Direct DB | DATABASE_URL, NEO4J_URI | VPS or local Docker |
| `audit_graphs_vps.py` | HTTP API | L9_EXECUTOR_API_KEY | Anywhere |

