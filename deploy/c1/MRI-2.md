cd /opt/l9
docker compose logs l9-neo4j --tail=50
docker compose logs l9-api --tail=50
docker compose logs l9-api --tail=100 | grep -i "error\|exception\|traceback"
docker compose logs l9-neo4j --tail=100 | grep -i "error\|fatal"
ls -la docker-compose*.yml  # Show all compose files
# Shows what's actually running (and which file Docker used)
# Check what's currently running
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"  # Shows container→image mapping
cat docker-compose.yml | grep "l9-api" -A 5  # Check if l9-api is defined
cat docker-compose.prod.yml | grep "l9-api" -A 5  # Check prod file
docker compose ps  

# 1. Find which compose file defines l9-api
grep -r "l9-api" docker-compose*.yml  # Shows which file(s) have the service

# 2. Get crash logs (use whichever file from step 1)
docker compose logs l9-api --tail=200 > /tmp/api-crash.log  # Save full output
cat /tmp/api-crash.log  # Review for Python tracebacks, import errors, DB connection failures

# 3. Check if .env has all required vars
cat .env  # Look for missing: OPENAI_API_KEY, POSTGRES_HOST, REDIS_HOST, NEO4J_HOST, etc.


======
cd /opt/l9

# 1. Stop all services
docker compose down  # Stops and removes containers

# 2. Prune unused resources (safe - keeps volumes and named images)
docker system prune -f  # Removes stopped containers, unused networks, dangling images

# 3. Optional: Prune build cache (frees more space)
docker builder prune -f  # Removes build cache (safe - will rebuild on next up)

# 4. Verify volumes are intact (DATA SAFETY CHECK)
docker volume ls | grep l9  # Should still show l9-postgres-data, l9-redis-data, l9-neo4j-data

# 5. Rebuild and start with prod overlay
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build  # Fresh build + start all services

# 6. Watch bootstrap complete
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs l9-bootstrap --follow  # Wait for "Bootstrap completed"

# 7. Verify l9-api is running
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps  # Check all services healthy
curl http://127.0.0.1:8000/health  # Test l9-api endpoint

# 8. Shows build metadata
docker inspect l9-api | grep -A 3 "Labels"  

========


l9-bootstrap  | 2026-02-02 13:59:19 [info     ] Phase 5: Binding tools & capabilities...
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Tool registry not available, using default tools
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] Bound tool to agent            agent_id=l9-primary tool=memory_search
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] Bound tool to agent            agent_id=l9-primary tool=memory_write
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] Bound tool to agent            agent_id=l9-primary tool=gmp_run
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] Bound tool to agent            agent_id=l9-primary tool=git_commit
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] Tools bound to agent           agent_id=l9-primary tool_count=4
