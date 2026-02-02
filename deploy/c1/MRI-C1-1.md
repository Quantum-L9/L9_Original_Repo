# Navigate to L9 repo
cd /opt/l9

# 1. Check docker-compose files exist
ls -la docker-compose*.yml

# 2. Check .env exists
ls -la .env

# 3. Check running containers
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 4. Get l9-api crash logs (CRITICAL)
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs l9-api --tail=200

# 5. Check for Python errors
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs l9-api --tail=200 | grep -i "error\|exception\|traceback\|fatal"

# 6. Test health endpoint
curl -v http://127.0.0.1:8000/health

# 7. Check if bootstrap completed successfully
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps -a | grep bootstrap

# 8. Verify .env has required vars (secrets redacted)
cat .env | sed 's/\(PASSWORD\|KEY\|SECRET\)=.*/\1=***REDACTED***/g' | head -50
