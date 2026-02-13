Below are **5 deliverables**, each clearly bounded and ready to drop in.

---

# 1️⃣ WRITE — `l9/bootstrap/__main__.py`

```python
# l9/bootstrap/__main__.py
"""
Canonical L9 Bootstrap Entrypoint
Runs exactly once. Fails hard. Writes bootstrap artifact.
"""

import os
import sys
import json
import asyncio
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# ---- CONFIG ----

REQUIRED_ENV = [
    "DATABASE_URL",
    "REDIS_URL",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
]

BOOTSTRAP_KEY = "l9.bootstrap"
BOOTSTRAP_VERSION = "2026-01-28"

# ---- UTIL ----

def fatal(msg: str):
    print(f"[BOOTSTRAP:FATAL] {msg}", file=sys.stderr)
    sys.exit(1)

def check_env():
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        fatal(f"Missing required env vars: {missing}")

# ---- BOOTSTRAP STEPS ----

async def run_migrations(engine):
    from api.migrations.runner import run_migrations  # existing code
    await run_migrations()

async def init_memory_substrate():
    from memory.substrate_service import init_service
    await init_service()

async def init_neo4j():
    from memory.graph_client import get_neo4j_client
    client = await get_neo4j_client()
    await client.verify_connectivity()

async def bootstrap_agent():
    from runtime.bootstrap import bootstrap_agent
    await bootstrap_agent()

async def write_bootstrap_artifact(engine):
    payload = {
        "version": BOOTSTRAP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }

    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_state (
                key TEXT PRIMARY KEY,
                value JSONB,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        await conn.execute(
            text("""
                INSERT INTO system_state (key, value)
                VALUES (:key, :value)
                ON CONFLICT (key) DO NOTHING
            """),
            {"key": BOOTSTRAP_KEY, "value": json.dumps(payload)},
        )

# ---- MAIN ----

async def main():
    check_env()

    db_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM system_state WHERE key = :key"),
            {"key": BOOTSTRAP_KEY},
        )
        if result.first():
            fatal("Bootstrap already completed. Refusing to run twice.")

    print("[BOOTSTRAP] Running migrations")
    await run_migrations(engine)

    print("[BOOTSTRAP] Initializing memory substrate")
    await init_memory_substrate()

    print("[BOOTSTRAP] Initializing Neo4j")
    await init_neo4j()

    print("[BOOTSTRAP] Bootstrapping agent")
    await bootstrap_agent()

    print("[BOOTSTRAP] Writing bootstrap artifact")
    await write_bootstrap_artifact(engine)

    print("[BOOTSTRAP] SUCCESS")

if __name__ == "__main__":
    asyncio.run(main())
```

---

# 2️⃣ WRITE — `docker-compose.production.yml` (Corrected)

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    restart: unless-stopped

  neo4j:
    image: neo4j:5
    restart: unless-stopped
    environment:
      NEO4J_AUTH: ${NEO4J_USER}/${NEO4J_PASSWORD}
    ports:
      - "7687:7687"

  l9-bootstrap:
    image: l9-api:latest
    command: python -m l9.bootstrap
    restart: "no"
    depends_on:
      - postgres
      - redis
      - neo4j

  l9-api:
    image: l9-api:latest
    command: python -m l9.api
    restart: unless-stopped
    depends_on:
      l9-bootstrap:
        condition: service_completed_successfully
    ports:
      - "8000:8000"
```

---

# 3️⃣ WRITE — API Startup Guard + Readiness

## `api/startup_guard.py`

```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import os

BOOTSTRAP_KEY = "l9.bootstrap"

async def ensure_bootstrap():
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT 1 FROM system_state WHERE key = :key"),
            {"key": BOOTSTRAP_KEY},
        )
        if not result.first():
            raise RuntimeError("Bootstrap not completed")
```

## Wire into `api/server.py` (lifespan)

```python
from api.startup_guard import ensure_bootstrap

@asynccontextmanager
async def lifespan(app):
    await ensure_bootstrap()
    yield
```

## Readiness endpoint

```python
@router.get("/os/readiness")
async def readiness():
    try:
        await ensure_bootstrap()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

---

# 4️⃣ WRITE — K8s Job + Deployment (Future-Proof)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: l9-bootstrap
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: bootstrap
          image: l9-api:latest
          command: ["python", "-m", "l9.bootstrap"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: l9-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: l9-api
  template:
    metadata:
      labels:
        app: l9-api
    spec:
      containers:
        - name: api
          image: l9-api:latest
          command: ["python", "-m", "l9.api"]
          ports:
            - containerPort: 8000
          readinessProbe:
            httpGet:
              path: /os/readiness
              port: 8000
```

---
