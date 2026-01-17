# L9 Runbook

## Local development run

```bash
# 1. Clone and setup
cd /path/to/L9
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Start PostgreSQL with pgvector
docker run -d --name l9-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=YOUR_PASSWORD \
  -e POSTGRES_DB=l9_memory \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# 3. Set environment variables
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/l9_memory"
export OPENAI_API_KEY="sk-..."  # Optional

# 4. Apply migrations
for f in migrations/000*.sql; do psql $DATABASE_URL -f $f; done

# 5. Start API server
uvicorn api.server:app --reload --port 8000
```

## Test run

```bash
# Docker stack smoke tests (auto-detects host vs container)
pytest tests/docker/test_stack_smoke.py -v
```

## Docker run

```bash
docker compose up -d
docker compose logs -f l9-api
```

## Required environment variables (names only)

- `DATABASE_URL`
- `L9_EXECUTOR_API_KEY`

## Common failure modes + fixes

- **API requests return `Executor key not configured` or `Unauthorized`.**
  - Fix: set `L9_EXECUTOR_API_KEY` and pass `Authorization: Bearer $L9_EXECUTOR_API_KEY` to authenticated endpoints.
- **Memory endpoints return `Memory system not available` / `Memory system not initialized`.**
  - Fix: ensure the database is running, `DATABASE_URL` is set, and migrations have been applied before starting the API server.
- **Docker tests fail with host DNS errors (e.g., `nodename nor servname provided`).**
  - Fix: run the stack with `docker compose up -d` and re-run the tests, or run tests from inside the `l9-api` container as documented.
