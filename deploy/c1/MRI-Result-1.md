# 8. Verify .env has required vars (secrets redacted)
cat .env | sed 's/\(PASSWORD\|KEY\|SECRET\)=.*/\1=***REDACTED***/g' | head -50
-rw-r--r-- 1 root root 11647 Feb  2 20:12 docker-compose.prod.yml
-rw-r--r-- 1 root root  7986 Feb  1 04:28 docker-compose.yml
-rw-r--r-- 1 root root 4108 Feb  2 19:47 .env
NAME                 IMAGE                                    COMMAND                  SERVICE         CREATED              STATUS                             PORTS
l9-grafana           grafana/grafana:10.2.0                   "/run.sh"                grafana         27 minutes ago       Up 27 minutes (healthy)            127.0.0.1:3000->3000/tcp
l9-jaeger            jaegertracing/all-in-one:1.52            "/go/bin/all-in-one-…"   jaeger          27 minutes ago       Up 27 minutes (healthy)            4317-4318/tcp, 5775/udp, 5778/tcp, 9411/tcp, 127.0.0.1:14268->14268/tcp, 14250/tcp, 6832/udp, 127.0.0.1:6831->6831/udp, 127.0.0.1:16686->16686/tcp
l9-l9-api-1          ghcr.io/cryptoxdog/l9-api:4.1.0          "uvicorn api.server:…"   l9-api          About a minute ago   Up 57 seconds (health: starting)   127.0.0.1:8000->8000/tcp
l9-l9-mcp-memory-1   ghcr.io/cryptoxdog/l9-mcp-memory:4.1.0   "uvicorn mcp_memory.…"   l9-mcp-memory   11 minutes ago       Up 11 minutes (healthy)            127.0.0.1:9002->9002/tcp
l9-neo4j             neo4j:5-community                        "tini -g -- /startup…"   neo4j           27 minutes ago       Up 27 minutes (healthy)            127.0.0.1:7474->7474/tcp, 7473/tcp, 127.0.0.1:7687->7687/tcp
l9-nginx-1           nginx:alpine                             "/docker-entrypoint.…"   nginx           11 minutes ago       Up 11 minutes                      0.0.0.0:80->80/tcp, 0.0.0.0:30379->30379/tcp, 0.0.0.0:30432->30432/tcp, 0.0.0.0:30474->30474/tcp, 0.0.0.0:30687->30687/tcp
l9-postgres          pgvector/pgvector:pg16                   "docker-entrypoint.s…"   l9-postgres     27 minutes ago       Up 27 minutes (healthy)            127.0.0.1:5432->5432/tcp
l9-prometheus        prom/prometheus:v2.48.0                  "/bin/prometheus --c…"   prometheus      27 minutes ago       Up 27 minutes (healthy)            127.0.0.1:9090->9090/tcp
l9-redis             redis:7-alpine                           "docker-entrypoint.s…"   redis           27 minutes ago       Up 27 minutes (healthy)            127.0.0.1:6379->6379/tcp
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "new row for relation \"packet_store\" violates check constraint \"packet_store_scope_check\"\nDETAIL:  Failing row contains (56d6b905-41a4-566e-a89b-29035dd89639, seed.cross_task_graph, {\"ttl\": null, \"tags\": [], \"lineage\": null, \"payload\": {\"scope\": ..., 2026-02-02 21:58:09.067722+00, {\"agent\": \"seed_loader\"}, {\"tool\": null, \"source\": null, \"derive_type\": null, \"source_agen..., null, {}, {}, null, agent, null, 0, null, null, 0, 1, f, null, complete, null, null, null, ae99936f-867c-46b8-a14e-a0027689e8fc, null, null).", "event": "enrichment_tier_1_exception", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-02T21:58:09.393257Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "new row for relation \"packet_store\" violates check constraint \"packet_store_scope_check\"\nDETAIL:  Failing row contains (56d6b905-41a4-566e-a89b-29035dd89639, seed.cross_task_graph, {\"ttl\": null, \"tags\": [], \"lineage\": null, \"payload\": {\"scope\": ..., 2026-02-02 21:58:09.067722+00, {\"agent\": \"seed_loader\"}, {\"tool\": null, \"source\": null, \"derive_type\": null, \"source_agen..., null, {}, {}, null, agent, null, 0, null, null, 0, 1, f, null, complete, null, null, null, ae99936f-867c-46b8-a14e-a0027689e8fc, null, null).", "event": "enrichment_dag_tier_1_failed", "logger": "memory.enrichment_dag", "level": "warning", "timestamp": "2026-02-02T21:58:09.393479Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "current transaction is aborted, commands ignored until end of transaction block", "event": "enrichment_tier_2_failed", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-02T21:58:09.394489Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "current transaction is aborted, commands ignored until end of transaction block", "event": "enrichment_dag_tier_2_failed", "logger": "memory.enrichment_dag", "level": "warning", "timestamp": "2026-02-02T21:58:09.394806Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "relation \"packets\" does not exist", "event": "enrichment_tier_3_failed", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-02T21:58:09.396658Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "relation \"packets\" does not exist", "event": "enrichment_dag_tier_3_failed", "logger": "memory.enrichment_dag", "level": "warning", "timestamp": "2026-02-02T21:58:09.396832Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "cannot import name 'get_dlq' from 'memory.dead_letter_queue' (/app/memory/dead_letter_queue.py)", "event": "enrichment_dag_dlq_push_failed", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-02T21:58:09.396999Z"}
l9-api-1  | {"event": "Packet 56d6b905-41a4-566e-a89b-29035dd89639 processed: status=error, tables=[]", "logger": "memory.substrate_service", "level": "info", "timestamp": "2026-02-02T21:58:09.397961Z"}
l9-api-1  | {"event": "Failed to write packet: All enrichment tiers failed; pushed to DLQ", "logger": "world_model.seed_loader", "level": "error", "timestamp": "2026-02-02T21:58:09.398132Z"}
l9-api-1  | {"event": "Ingested packet 37730484-58d6-4a2b-a540-65e396c233e5: entities=1, relations=0", "logger": "world_model.seed_loader", "level": "info", "timestamp": "2026-02-02T21:58:09.398370Z"}
l9-api-1  | {"event": "Seed loading complete: 4 files, 3 entities, 0 relations, 10 reflections, 0 synced to DB", "logger": "world_model.seed_loader", "level": "info", "timestamp": "2026-02-02T21:58:09.398673Z"}
l9-api-1  | {"event": "Seed library loaded: 4 files, 0 patterns, 0 heuristics", "logger": "world_model.runtime", "level": "info", "timestamp": "2026-02-02T21:58:09.398934Z"}
l9-api-1  | {"event": "Starting runtime loop (poll_interval=60s, batch_size=50)", "logger": "world_model.runtime", "level": "info", "timestamp": "2026-02-02T21:58:09.399048Z"}
l9-api-1  | {"event": "Error querying packets: syntax error at or near \"#\"", "logger": "memory.substrate_service", "level": "error", "timestamp": "2026-02-02T21:58:09.401280Z"}
l9-api-1  | {"event": "Failed to fetch packets from substrate: syntax error at or near \"#\"", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-02-02T21:58:09.404692Z"}
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | HTTP Request: POST https://api.openai.com/v1/embeddings "HTTP/1.1 200 OK"
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "new row for relation \"packet_store\" violates check constraint \"packet_store_scope_check\"\nDETAIL:  Failing row contains (56d6b905-41a4-566e-a89b-29035dd89639, seed.cross_task_graph, {\"ttl\": null, \"tags\": [], \"lineage\": null, \"payload\": {\"scope\": ..., 2026-02-02 21:58:09.067722+00, {\"agent\": \"seed_loader\"}, {\"tool\": null, \"source\": null, \"derive_type\": null, \"source_agen..., null, {}, {}, null, agent, null, 0, null, null, 0, 1, f, null, complete, null, null, null, ae99936f-867c-46b8-a14e-a0027689e8fc, null, null).", "event": "enrichment_tier_1_exception", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-02T21:58:09.393257Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "new row for relation \"packet_store\" violates check constraint \"packet_store_scope_check\"\nDETAIL:  Failing row contains (56d6b905-41a4-566e-a89b-29035dd89639, seed.cross_task_graph, {\"ttl\": null, \"tags\": [], \"lineage\": null, \"payload\": {\"scope\": ..., 2026-02-02 21:58:09.067722+00, {\"agent\": \"seed_loader\"}, {\"tool\": null, \"source\": null, \"derive_type\": null, \"source_agen..., null, {}, {}, null, agent, null, 0, null, null, 0, 1, f, null, complete, null, null, null, ae99936f-867c-46b8-a14e-a0027689e8fc, null, null).", "event": "enrichment_dag_tier_1_failed", "logger": "memory.enrichment_dag", "level": "warning", "timestamp": "2026-02-02T21:58:09.393479Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "current transaction is aborted, commands ignored until end of transaction block", "event": "enrichment_tier_2_failed", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-02T21:58:09.394489Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "current transaction is aborted, commands ignored until end of transaction block", "event": "enrichment_dag_tier_2_failed", "logger": "memory.enrichment_dag", "level": "warning", "timestamp": "2026-02-02T21:58:09.394806Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "relation \"packets\" does not exist", "event": "enrichment_tier_3_failed", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-02T21:58:09.396658Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "relation \"packets\" does not exist", "event": "enrichment_dag_tier_3_failed", "logger": "memory.enrichment_dag", "level": "warning", "timestamp": "2026-02-02T21:58:09.396832Z"}
l9-api-1  | {"packet_id": "56d6b905-41a4-566e-a89b-29035dd89639", "error": "cannot import name 'get_dlq' from 'memory.dead_letter_queue' (/app/memory/dead_letter_queue.py)", "event": "enrichment_dag_dlq_push_failed", "logger": "memory.enrichment_dag", "level": "error", "timestamp": "2026-02-02T21:58:09.396999Z"}
l9-api-1  | {"event": "Packet 56d6b905-41a4-566e-a89b-29035dd89639 processed: status=error, tables=[]", "logger": "memory.substrate_service", "level": "info", "timestamp": "2026-02-02T21:58:09.397961Z"}
l9-api-1  | {"event": "Failed to write packet: All enrichment tiers failed; pushed to DLQ", "logger": "world_model.seed_loader", "level": "error", "timestamp": "2026-02-02T21:58:09.398132Z"}
l9-api-1  | {"event": "Error querying packets: syntax error at or near \"#\"", "logger": "memory.substrate_service", "level": "error", "timestamp": "2026-02-02T21:58:09.401280Z"}
l9-api-1  | {"event": "Failed to fetch packets from substrate: syntax error at or near \"#\"", "logger": "world_model.runtime", "level": "error", "timestamp": "2026-02-02T21:58:09.404692Z"}
*   Trying 127.0.0.1:8000...
* Connected to 127.0.0.1 (127.0.0.1) port 8000
> GET /health HTTP/1.1
> Host: 127.0.0.1:8000
> User-Agent: curl/8.5.0
> Accept: */*
> 
* Recv failure: Connection reset by peer
* Closing connection
curl: (56) Recv failure: Connection reset by peer
l9-bootstrap         ghcr.io/cryptoxdog/l9-api:4.1.0          "python -m bootstrap"    l9-bootstrap    About a minute ago   Exited (0) 58 seconds ago          
# =============================================================================
# L9 DOCKER/VPS Environment (.env.vps)
# For Docker Compose on VPS - uses service DNS names (NOT localhost!)
#
# ⚠️  CRITICAL: NO INLINE COMMENTS ALLOWED
#     Pydantic-settings parses entire line as value

# -----------------------------------------------------------------------------
# Database (use container service names, NOT localhost/127.0.0.1)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=***REDACTED***
POSTGRES_DB=l9_memory
MEMORY_DSN=postgresql://postgres:8e4fXWM6Q3M87*b3@l9-postgres:5432/l9_memory
DATABASE_URL=postgresql://postgres:8e4fXWM6Q3M87*b3@l9-postgres:5432/l9_memory
# API Keys
L9_EXECUTOR_API_KEY=***REDACTED***
L9_API_KEY=***REDACTED***
OPENAI_API_KEY=***REDACTED***
PERPLEXITY_API_KEY=***REDACTED***
GOOGLE_CALENDAR_API_KEY=***REDACTED***
GMAIL_API_KEY=***REDACTED***
GPG_KEY=***REDACTED***
L9_API_URL=http://mcp.quantumaipartners.com:30080
# Neo4j Graph Database (use container name)
NEO4J_URL=bolt://neo4j:7687
NEO4J_URI=${NEO4J_URL}
NEO4J_USER=neo4j
NEO4J_PASSWORD=***REDACTED***
# Redis (use container name)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=***REDACTED***
# Qdrant Vector Store (use container name)
QDRANT_HOST=qdrant
QDRANT_PORT=6333
# Slack Integration
SLACK_APP_ENABLED=true
SLACK_APP_ID=A0A3MLBJ55Y
SLACK_SIGNING_SECRET=***REDACTED***
SLACK_CLIENT_SECRET=***REDACTED***
SLACK_CLIENT_ID=5756690555681.10123691617202
SLACK_BOT_TOKEN=xoxb-5756690555681-10120570028437-0GsjsVSUP0rsKfxOoHFPrpxc
SLACK_VERIFICATION_TOKEN=nFrKJ0NVekjgzIpOtpyYqUCK
SLACK_BOT_USER_ID=U0A3JGS0UCV
L_SLACK_USER_ID=U0A3JGS0UCV
# Twilio
TWILIO_ENABLED=false
TWILIO_ACCOUNT_SID=AC4daa74c868f142472f9717e3ac6c8c0f
TWILIO_AUTH_TOKEN=d3d1d33dd9afb72f36c210dc845a4ea3
TWILIO_SMS_NUMBER=17047416314