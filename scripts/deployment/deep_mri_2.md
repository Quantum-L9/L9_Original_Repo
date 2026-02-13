# L9 API unhealthy triage pack (read-only)
# Run on C1 in /opt/l9

set -euo pipefail

echo "===== 0) Context ====="
date -u
hostname
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'

echo
echo "===== 1) Healthcheck definition + status ====="
CID="$(docker ps --filter 'name=l9-l9-api-1' --format '{{.ID}}' | head -n1)"
if [ -z "${CID}" ]; then
  echo "l9-l9-api-1 not found"; exit 1
fi
docker inspect "${CID}" --format 'Healthcheck: {{json .Config.Healthcheck}}'
docker inspect "${CID}" --format 'State: {{json .State.Health}}'

echo
echo "===== 2) Last 400 API logs (errors/warnings + startup markers) ====="
docker logs --tail 400 l9-l9-api-1 2>&1 | tee /tmp/l9-api-last400.log >/dev/null
echo "--- grep: fatal/error/traceback/import/runtimeerror/startup failed ---"
grep -iE 'fatal|error|traceback|importerror|runtimeerror|application startup failed|waiting for application startup|failed to import|unhealthy' /tmp/l9-api-last400.log || true

echo
echo "===== 3) Probe from host to mapped port ====="
curl -sv --max-time 5 http://127.0.0.1:8000/_echo || true
curl -sv --max-time 5 http://127.0.0.1:8000/health || true
curl -sv --max-time 5 http://127.0.0.1:8000/health/services || true

echo
echo "===== 4) Probe from inside container namespace ====="
docker exec l9-l9-api-1 sh -lc '
  echo "inside container:" ;
  (curl -sv --max-time 5 http://127.0.0.1:8000/_echo || true) ;
  (curl -sv --max-time 5 http://127.0.0.1:8000/health || true) ;
  (curl -sv --max-time 5 http://127.0.0.1:8000/health/services || true)
'

echo
echo "===== 5) Import-chain smoke tests in running image ====="
docker exec l9-l9-api-1 sh -lc '
python - <<PY
import importlib, traceback
mods = [
  "core.tools.dynamic_discovery",
  "core.agents.dynamic_tool_binding",
  "core.agents.agent_instance",
  "core.agents.executor",
  "api.server",
]
for m in mods:
    try:
        importlib.import_module(m)
        print(f"OK  {m}")
    except Exception as e:
        print(f"FAIL {m}: {e}")
        traceback.print_exc()
PY
' || true

echo
echo "===== 6) Check symbol alignment (hotfix validation) ====="
docker exec l9-l9-api-1 sh -lc '
python - <<PY
import core.tools.dynamic_discovery as d
print("has discover_tools_for_task:", hasattr(d, "discover_tools_for_task"))
print("has discover_tools_for_agent:", hasattr(d, "discover_tools_for_agent"))
print("has get_tool_binding_mode:", hasattr(d, "get_tool_binding_mode"))
PY
' || true

echo
echo "===== 7) Config flags that can force startup failure ====="
docker exec l9-l9-api-1 sh -lc '
env | grep -E "^(L9_|SLACK_|DATABASE_URL|MEMORY_DSN|NEO4J_|REDIS_)" | sort
' || true

echo
echo "===== 8) Dependency quick checks ====="
docker exec l9-l9-api-1 sh -lc '
python - <<PY
import os, asyncio
print("MEMORY_DSN set:", bool(os.getenv("MEMORY_DSN") or os.getenv("DATABASE_URL")))
print("SLACK_BOT_TOKEN set:", bool(os.getenv("SLACK_BOT_TOKEN")))
print("SLACK_SIGNING_SECRET set:", bool(os.getenv("SLACK_SIGNING_SECRET")))
print("L9_MINIMAL_MODE:", os.getenv("L9_MINIMAL_MODE"))
PY
' || true

echo
echo "===== 9) Image/version drift ====="
docker inspect "${CID}" --format 'ImageRef={{.Config.Image}}'
docker inspect "${CID}" --format 'ImageDigest={{.Image}}'
docker exec l9-l9-api-1 sh -lc 'python -V; uname -a' || true

echo
echo "===== 10) One-line diagnosis hint ====="
if grep -qi "cannot import name 'discover_tools_for_agent'" /tmp/l9-api-last400.log; then
  echo "LIKELY ROOT CAUSE: stale import in dynamic tool binding path (discover_tools_for_agent)."
elif grep -qi "cannot import name 'get_tool_binding_mode'" /tmp/l9-api-last400.log; then
  echo "LIKELY ROOT CAUSE: stale import in dynamic tool binding path (get_tool_binding_mode)."
elif grep -qi "Agent Executor required for Slack routing" /tmp/l9-api-last400.log; then
  echo "LIKELY ROOT CAUSE: executor init failed, then startup guard aborts due to Slack routing requirement."
else
  echo "No single obvious root cause from last 400 lines; inspect /tmp/l9-api-last400.log manually."
fi

echo
echo "Done. Primary log file: /tmp/l9-api-last400.log"