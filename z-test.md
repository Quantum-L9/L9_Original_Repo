# 1) Check if migrations/\*.sql files exist

ls -lh migrations/\*.sql | head -10

# 2) Apply all migrations to l9_memory database

for f in migrations/\*.sql; do
echo "Running $f..."
  PGPASSWORD=$POSTGRES_PASSWORD psql -h 127.0.0.1 -U $POSTGRES_USER -d $POSTGRES_DB -f "$f"
done

# 3) Verify memory.packets table now exists

PGPASSWORD=$POSTGRES_PASSWORD psql -h 127.0.0.1 -U $POSTGRES_USER -d $POSTGRES_DB -c \
 "SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'memory' ORDER BY tablename;"

# 4) Restart l9-api to pick up the new schema

docker compose restart l9-api
sleep 10

# 5) Check logs for RLS error (should be gone)

docker compose logs l9-api --tail=50 | grep -E 'RLS|packet|Failed to fetch'# 1. List all services in docker-compose.yml
docker compose config --services | grep -i api

# 2. Check current running containers
docker compose ps

# 3. Look at the compose file directly
grep -A 5 "ghcr.io/cryptoxdog/l9-api" docker-compose.yml | head -10

# 6. Get build/startup errors
docker compose logs --tail=200 | grep -iE "error|fail|exit|fatal"

# 2. Build l9-api image with the fix baked in
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache l9-api

# 3. Start ALL services (infra + l9-bootstrap + l9-api + l9-mcp-memory + nginx)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. Watch bootstrap logs (runs once, then exits successfully)
docker logs -f l9-bootstrap 2>&1 | head -100

# Press Ctrl+C after bootstrap completes, then check API startup: