root@C1:/opt/l9# cd /opt/l9

# Stop current infrastructure-only stack
docker compose down  # Stops base services only

# Start with BOTH files (base + prod overlay)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d  # Starts all services including l9-api

# Verify all services running
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps  # Should show l9-api, l9-mcp-memory, l9-bootstrap
ç^C
root@C1:/opt/l9# cd /opt/l9

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
[+] down 7/7
 ✔ Container l9-redis      Removed                                                                                                                          0.5ss
 ✔ Container l9-grafana    Removed                                                                                                                          0.3ss
 ✔ Container l9-neo4j      Removed                                                                                                                          10.5s
 ✔ Container l9-postgres   Removed                                                                                                                          0.5ss
 ✔ Container l9-jaeger     Removed                                                                                                                          0.4ss
 ✔ Container l9-prometheus Removed                                                                                                                          0.2ss
 ! Network l9-network      Resource is still in use                                                                                                         0.0s
Deleted Containers:
639cd658bffdd1b56a4720725db3f5c0db3cce1de82df21fe5ae0edbe1531a1f
9f7917dbdbdcdd0a755e780acf6beb8f12e3e50306fbd1751e56b4796a7232cb
aa8691c3b095ed03bdfb6a49e1d05513c3f6d02fd4ca1293a47e08fa956c02e3

Deleted Networks:
l9_l9-network

Deleted Images:
deleted: sha256:6eaf0806d254185301752c02ffa678e889324726fbe55cd3c1663b62e1b8d735
deleted: sha256:78d81d5891ce808eb521f07c9ef9ae0d1deb55912b47a2a4792ab7517de28e9e
deleted: sha256:77e8406b8af2bbfc852db2f44466f506b7d563d50ee86347d784023091bd2d23
deleted: sha256:3d7c3606a6e06e11e1946fc0518da03da79be71c27068b5ebfa4a2ad3c86bf5e
deleted: sha256:c3b12ad4fb0279a176846b635063a41ff53bab56031cc0f243849d9170634b66

Deleted build cache objects:
hzj6oorqv5lx1blga6ipmk1qg
kovumhnlvkc9gvlj030bp7tiq
4o9drib4h8peucbcvlqjuqmzg
lcl87j8xzaldn7e8j225o1n23
sdprzeets95iplm8qifcpvnwo
dhkmt0wrpvek0cjo9z585mn5u
kgk04ewkzq8scqwslqx8xs6py
qv1zwmws0iliuj2vdv07fumsj
xbl37jnkq1ods9glozxdvam51
l86v01ydmiedt6j0aj92c8n0x
vnm3ygm8kk8kahnqb5y424nf4
w016z7ebwq8h6gle2ljhxtk1l
uykfhchaawpd8yg7sleyk8ab7
1b8rtr7iaa5zpuuedg4zkrcc6
f34270nzfv8dt39vro87kzkdr
cxi64mi0tq5dt1bmqcpqfkeff
010d08mlkhaqoxbut4bdtepvc
mrg41jpj305kfoju5g5ms0jsl
lz1kgyb4af2gm2e0n6wlk90br
ols0aussq1xt3j5ro00ccqoog
m911iqeew8ex7cici6xs4bhas
vkhsized5v0zwumy5706an7ph
nzmapbd3uodmypp0z34faodpl
hy84ovzbydgdavnopsipcw3qk
ssajvdawtkk6dz3nhzr6k647b
dnyydv6zippsiluun1ii2us8y
ebh1m9gjn06aw92r4z2s1s7wj
h923fxyvp5sq47pnftf9nrquc
lxcis2p3ox46b3ar0w6avrkl9
pvlkubp9fs5t8fcm7pthjh9tl
itcwg413k41wwpueid5ih2ovw
wvv3u5qhzvodd7ohv1y2pvqz9
u30mpzihfrriiams1jql3tkhz
w4m7ck8cx3l5mosrkakul6qio
ge76eavtljl9feyq98wluq6y1
mx7rvl7l756cjrkw5s228ujsl
ifnwsmyu0lp03rawoziu22ngu
9b6pa487cvoecq3zo7biofwv5
ylrzk9j1m2037z398um68aclu
rgr8cu8vzxrxjiq85a7bsivbh
mwok5aditpt6m3h5qgxexaibx
fd4lbe8ji46ifatbpbxhgz4ti
iyk2u2o0zpt8dgx7m4vlit9hm
xcmgvokcsxythqstaq4099899
bit1i2apb5pv1ekzvwkqjhocy
sqg73h9d27a630k54ym7s5esn
ey0zb4vkfwhdn0bb7tbqe1c13
jgbmhppebil9cs5gyp9unctrg
czmeu4pkuorsmsk4484igvb7w
jtgrrwht1tvk4tze238n10yx1
fwdzrrbjs303mn8xj8u99akpl
s1rxjayhkchkurp9zqil3ff3h
z2tow5htwg4jic51t56pqos35

Total reclaimed space: 48.76GB
Total:	0B
local     l9-grafana-data
local     l9-grafana-data-prod
local     l9-jaeger-data-prod
local     l9-neo4j-data
local     l9-neo4j-data-prod
local     l9-neo4j-logs
local     l9-neo4j-logs-prod
local     l9-postgres-data
local     l9-postgres-data-prod
local     l9-prometheus-data
local     l9-prometheus-data-prod
local     l9-redis-data
local     l9-redis-data-prod
local     l9_grafana_data
local     l9_neo4j_data
local     l9_neo4j_logs
local     l9_postgres_data
local     l9_prometheus_data
local     l9_redis_data
WARN[0000] The "BUILD_DATE" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VCS_REF" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VERSION" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VCS_REF" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VERSION" variable is not set. Defaulting to a blank string. 
WARN[0000] The "BUILD_DATE" variable is not set. Defaulting to a blank string. 
WARN[0000] The "BUILD_DATE" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VCS_REF" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VERSION" variable is not set. Defaulting to a blank string. 
[+] Building 3.2s (33/33) FINISHED                                                                                                                               
 => [internal] load local bake definitions                                                                                                                  0.0s
 => => reading from stdin 1.70kB                                                                                                                            0.0s
 => [l9-bootstrap internal] load build definition from Dockerfile                                                                                           0.0s
 => => transferring dockerfile: 4.40kB                                                                                                                      0.0s
 => [l9-mcp-memory internal] load build definition from Dockerfile.mcp-memory                                                                               0.0s
 => => transferring dockerfile: 5.06kB                                                                                                                      0.0s
 => [l9-mcp-memory internal] load metadata for docker.io/library/python:3.12-slim                                                                           1.0s
 => [l9-mcp-memory internal] load .dockerignore                                                                                                             0.0s
 => => transferring context: 480B                                                                                                                           0.0s
 => [l9-mcp-memory base 1/4] FROM docker.io/library/python:3.12-slim@sha256:5e2dbd4bbdd9c0e67412aea9463906f74a22c60f89eb7b5bbb7d45b66a2b68a6                0.0s
 => [l9-api internal] load build context                                                                                                                    0.7s
 => => transferring context: 31.56MB                                                                                                                        0.7s
 => [l9-mcp-memory internal] load build context                                                                                                             0.3s
 => => transferring context: 7.32MB                                                                                                                         0.3s
 => CACHED [l9-bootstrap base 2/4] WORKDIR /app                                                                                                             0.0s
 => CACHED [l9-mcp-memory base 3/4] RUN apt-get update && apt-get install -y --no-install-recommends     curl     postgresql-client     ca-certificates     0.0s
 => CACHED [l9-mcp-memory base 4/4] RUN useradd -m -u 1000 l9user &&     chown -R l9user:l9user /app                                                        0.0s
 => CACHED [l9-mcp-memory production  1/10] COPY requirements-mcp-memory.txt /app/                                                                          0.0s
 => CACHED [l9-mcp-memory production  2/10] RUN pip install --no-cache-dir -r requirements-mcp-memory.txt &&     pip cache purge                            0.0s
 => [l9-mcp-memory production  3/10] COPY --chown=l9user:l9user mcp_memory/ /app/mcp_memory/                                                                0.1s
 => [l9-mcp-memory production  4/10] COPY --chown=l9user:l9user core/ /app/core/                                                                            0.1s
 => [l9-mcp-memory production  5/10] COPY --chown=l9user:l9user memory/ /app/memory/                                                                        0.1s
 => [l9-mcp-memory production  6/10] COPY --chown=l9user:l9user config/ /app/config/                                                                        0.0s
 => CACHED [l9-bootstrap base 3/4] RUN apt-get update && apt-get install -y --no-install-recommends     curl     ca-certificates     && rm -rf /var/lib/ap  0.0s
 => CACHED [l9-bootstrap base 4/4] RUN useradd -m -u 1000 l9user &&     mkdir -p /app/data/.l9/gmail/attachments &&     chown -R l9user:l9user /app         0.0s
 => CACHED [l9-bootstrap production 1/4] COPY requirements-docker.txt /app/                                                                                 0.0s
 => CACHED [l9-bootstrap production 2/4] RUN python -m pip install -U pip setuptools wheel &&     pip install --no-cache-dir -r requirements-docker.txt &&  0.0s
 => [l9-bootstrap production 3/4] COPY --chown=l9user:l9user . /app/                                                                                        0.4s
 => [l9-mcp-memory production  7/10] COPY --chown=l9user:l9user telemetry/ /app/telemetry/                                                                  0.0s
 => [l9-mcp-memory production  8/10] COPY --chown=l9user:l9user private/ /app/private/                                                                      0.1s
 => [l9-mcp-memory production  9/10] COPY --chown=l9user:l9user migrations/ /app/migrations/                                                                0.0s
 => [l9-mcp-memory production 10/10] RUN test -f /app/mcp_memory/src/main.py || (echo "ERROR: mcp_memory/src/main.py not found" && exit 1) &&     test -f   0.3s
 => [l9-api production 4/4] RUN test -f /app/api/server.py || (echo "ERROR: api/server.py not found" && exit 1) &&     test -f /app/requirements-docker.tx  0.3s
 => [l9-mcp-memory] exporting to image                                                                                                                      0.2s
 => => exporting layers                                                                                                                                     0.1s
 => => writing image sha256:b835559fe8947334d0525e5432f3d09c3f6641859b45f03a2918481034123f5c                                                                0.0s
 => => naming to ghcr.io/cryptoxdog/l9-mcp-memory:latest                                                                                                    0.0s
 => [l9-mcp-memory] resolving provenance for metadata file                                                                                                  0.0s
 => [l9-api] exporting to image                                                                                                                             0.5s
 => => exporting layers                                                                                                                                     0.5s
 => => writing image sha256:e3ca02e5d2c0a7e501f73918598e5a656ecf6306cfa5db45b3cfca40c3bb45d7                                                                0.0s
 => => naming to ghcr.io/cryptoxdog/l9-api:latest                                                                                                           0.0s
 => [l9-bootstrap] exporting to image                                                                                                                       0.5s
 => => exporting layers                                                                                                                                     0.5s
 => => writing image sha256:006ce525b61e5d76343ca1bb537e93db86a916aad9883fa1841f6c1fb16f94d6                                                                0.0s
 => => naming to ghcr.io/cryptoxdog/l9-api:latest                                                                                                           0.0s
 => [l9-api] resolving provenance for metadata file                                                                                                         0.0s
 => [l9-bootstrap] resolving provenance for metadata file                                                                                                   0.0s
[+] up 12/12
 ✔ Image ghcr.io/cryptoxdog/l9-api:latest        Built                                                                                                                         3.4ss
 ✔ Image ghcr.io/cryptoxdog/l9-mcp-memory:latest Built                                                                                                                         3.4ss
 ✔ Container l9-redis                            Healthy                                                                                                                       13.1s
 ✔ Container l9-prometheus                       Healthy                                                                                                                       11.6s
 ✔ Container l9-neo4j                            Healthy                                                                                                                       13.1s
 ✔ Container l9-jaeger                           Created                                                                                                                       0.1ss
 ✔ Container l9-postgres                         Healthy                                                                                                                       13.2s
 ✔ Container l9-grafana                          Created                                                                                                                       0.1ss
 ✔ Container l9-bootstrap                        Exited                                                                                                                        34.5s
 ✔ Container l9-l9-mcp-memory-1                  Recreated                                                                                                                     0.6ss
 ✔ Container l9-l9-api-1                         Created                                                                                                                       0.0ss
 ✔ Container l9-nginx-1                          Created                                                                                                                       0.0ss
WARN[0000] The "BUILD_DATE" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VCS_REF" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VERSION" variable is not set. Defaulting to a blank string. 
WARN[0000] The "BUILD_DATE" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VCS_REF" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VERSION" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VCS_REF" variable is not set. Defaulting to a blank string. 
WARN[0000] The "VERSION" variable is not set. Defaulting to a blank string. 
WARN[0000] The "BUILD_DATE" variable is not set. Defaulting to a blank string. 
l9-bootstrap  | [BOOTSTRAP] First run - system_state table will be created
l9-bootstrap  | [BOOTSTRAP] Running migrations
l9-bootstrap  | 2026-02-02 13:59:04 [info     ] registry.initialized           allow_duplicates=False registry_name=singleton_services
l9-bootstrap  | 2026-02-02 13:59:04 [info     ] registry.instance_registered   component=neo4j_client priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:04 [info     ] singleton_service_registry.registered category=general name=neo4j_client
l9-bootstrap  | 2026-02-02 13:59:04 [debug    ] singleton_service_registry.closer_registered singleton=neo4j_client
l9-bootstrap  | 2026-02-02 13:59:05 [info     ] registry.instance_registered   component=memory_substrate_repository priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:05 [info     ] singleton_service_registry.registered category=general name=memory_substrate_repository
l9-bootstrap  | 2026-02-02 13:59:05 [debug    ] singleton_service_registry.closer_registered singleton=memory_substrate_repository
l9-bootstrap  | 2026-02-02 13:59:05 [info     ] registry.instance_registered   component=housekeeping_engine priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:05 [info     ] singleton_service_registry.registered category=general name=housekeeping_engine
l9-bootstrap  | 2026-02-02 13:59:05 [debug    ] tool_risk_policy.loaded        high_risk_count=13 igor_required_count=8 path=/app/config/policies/high_risk_tools.yaml safe_count=9
l9-bootstrap  | 2026-02-02 13:59:05 [info     ] registry.instance_registered   component=memory_substrate_service priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:05 [info     ] singleton_service_registry.registered category=general name=memory_substrate_service
l9-bootstrap  | 2026-02-02 13:59:05 [debug    ] singleton_service_registry.closer_registered singleton=memory_substrate_service
l9-bootstrap  | 2026-02-02 13:59:05 [info     ] registry.instance_registered   component=ingestion_pipeline priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:05 [info     ] singleton_service_registry.registered category=general name=ingestion_pipeline
l9-bootstrap  | 2026-02-02 13:59:05 [info     ] registry.instance_registered   component=insight_extraction_pipeline priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:05 [info     ] singleton_service_registry.registered category=general name=insight_extraction_pipeline
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] CrossEncoder available from sentence-transformers
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] registry.instance_registered   component=retrieval_pipeline priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] singleton_service_registry.registered category=general name=retrieval_pipeline
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] Migration runner connected to database with JSON codecs
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Migrations table ensured
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0001_init_memory_substrate.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0002_enhance_packet_store.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0003_init_tasks.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0004_init_world_model_entities.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0005_init_knowledge_facts.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0006_init_world_model_updates.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0007_init_world_model_snapshots.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0008_memory_substrate_10x.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0009_feedback_and_effectiveness.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0010_add_fact_deprecation.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0011_tool_audit_log.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0012_fix_graph_checkpoints_unique.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0013_mcp_audit_columns.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0014_multi_checkpoint_support.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0015_knowledge_facts_upsert_key.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0016_governance_scope_semantics.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0017_governance_project_id.sql
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] Running migration: 0018_semantic_facts.sql
l9-bootstrap  | 2026-02-02 13:59:16 [error    ] Migration failed: 0018_semantic_facts.sql: column cannot have more than 2000 dimensions for ivfflat index
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] Running migration: 0019_episodic_events.sql
l9-bootstrap  | 2026-02-02 13:59:16 [error    ] Migration failed: 0019_episodic_events.sql: policy "episodic_events_platform_admin" for table "episodic_events" already exists
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0020_optimize_vector_search.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0021_gmp_learning.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0022_temporal_fact_validity.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0024_cmts_schema.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0025_tool_embeddings.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0026_tool_bm25_index.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0027_eval_results.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 0028_optimize_vector_indexing.sql
l9-bootstrap  | 2026-02-02 13:59:16 [debug    ] Skipping already-applied migration: 20260125_tool_feedback_learning.sql
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] Migration runner disconnected
l9-bootstrap  | [BOOTSTRAP] Initializing memory substrate
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] substrate_service.factory_create config_keys=['database_url', 'embedding_provider_type'] database_url_set=True embedding_provider_type=openai
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] MemorySubstrateContainer.initialized database_url_set=True embedding_provider=openai
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] Database connection pool initialized max_size=15 min_size=0
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] MemorySubstrateContainer.repository_initialized pool_size=5
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] Using OpenAI embedding provider: text-embedding-3-large
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] MemorySubstrateContainer.embedding_provider_initialized model=text-embedding-3-large provider_type=openai
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] EnrichmentDAG initialized      config_summary={'enable_semantic': True, 'enable_entity_extraction': True, 'enable_graph': True, 'enable_fallback': True}
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] MemorySubstrateService initialized
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] MemorySubstrateContainer.service_initialized
l9-bootstrap  | 2026-02-02 13:59:16 [info     ] substrate_service.factory_SUCCESS
l9-bootstrap  | [BOOTSTRAP] Initializing Neo4j
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] Neo4j connected: bolt://neo4j:7687/neo4j
l9-bootstrap  | [BOOTSTRAP] Bootstrapping agent
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] agent.bootstrap.orchestrator.init l9_new_agent_init=True
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] ╔════════════════════════════════════════╗ extra={'markup': True}
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] ║  BOOTSTRAP: Agent l9-primary
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] ╚════════════════════════════════════════╝
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] Phase 0: Validating blueprint...
l9-bootstrap  | 2026-02-02 13:59:17 [debug    ] Blueprint check passed         check=config_valid
l9-bootstrap  | 2026-02-02 13:59:17 [debug    ] Blueprint check passed         check=kernels_discoverable count=0
l9-bootstrap  | 2026-02-02 13:59:17 [debug    ] Blueprint check passed         check=postgres_online
l9-bootstrap  | 2026-02-02 13:59:17 [debug    ] Blueprint check passed         check=neo4j_online
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.initialized           allow_duplicates=False registry_name=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_get priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_set priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_keys priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_delete priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_enqueue_task priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_dequeue_task priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_queue_size priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_get_task_context priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_set_task_context priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_get_rate_limit priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_set_rate_limit priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_increment_rate_limit priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_decrement_rate_limit priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] kernel_config_loader.load_kernel_config action=loading_config environment=production
l9-bootstrap  | 2026-02-02 13:59:17 [debug    ] kernel_config_loader.load_kernel_config action=applied_env_overrides environment=production
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] kernel_config_loader.load_kernel_config action=config_loaded environment=production kernel_count=10
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] kernel_loader.config_loaded    action=loaded_externalized_config kernel_count=10 source=config/kernel_discovery.yaml
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] registry.instance_registered   component=redis_client priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:17 [info     ] singleton_service_registry.registered category=general name=redis_client
l9-bootstrap  | 2026-02-02 13:59:17 [debug    ] singleton_service_registry.closer_registered singleton=redis_client
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] WebSocketOrchestrator initialized
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] registry.instance_registered   component=tool_registry priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] singleton_service_registry.registered category=general name=tool_registry
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] registry.instance_registered   component=tool_router_find priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] registry.instance_registered   component=saga_fetch_and_enrich priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] registry.instance_registered   component=saga_enrich_entities priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] registry.instance_registered   component=saga_timeline_correlation priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] registry.instance_registered   component=saga_execute_custom priority=10 registry=tool_executors
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] registry.instance_registered   component=research_memory_adapter priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] singleton_service_registry.registered category=general name=research_memory_adapter
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] registry.instance_registered   component=tool_resolver priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] singleton_service_registry.registered category=general name=tool_resolver
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] registry.instance_registered   component=research_graph_runtime priority=0 registry=singleton_services
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] singleton_service_registry.registered category=general name=research_graph_runtime
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] RouterRegistry initialized
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Router registered: Research Factory API module_id=research_factory prefix= tags=['research']
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Registered tool: Perplexity Search (perplexity_search)
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Registered tool: HTTP Request (http_request)
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Registered tool: Mock Search (mock_search)
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Registered tool: Calculator (calculate)
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Initialized 4 default tools
l9-bootstrap  | 2026-02-02 13:59:18 [debug    ] Blueprint check passed         check=tool_registry_available
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Blueprint validation complete  agent_id=l9-primary checks_passed=5
l9-bootstrap  | 2026-02-02 13:59:18 [debug    ] bootstrap.phase.metrics        agent_id=l9-primary duration_ms=1123.7609169911593 phase=0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] ✓ Phase 0 complete
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Phase 1: Loading & parsing kernels...
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Loaded kernel                  hash_prefix=204fe1a6 name=01_master_kernel version=1.0.0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Loaded kernel                  hash_prefix=6f79ecea name=02_identity_kernel version=1.0.0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Loaded kernel                  hash_prefix=4e37729c name=03_cognitive_kernel version=1.0.0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Loaded kernel                  hash_prefix=820d5311 name=04_behavioral_kernel version=1.0.0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Loaded kernel                  hash_prefix=fed71ac6 name=05_memory_kernel version=1.0.0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Loaded kernel                  hash_prefix=6dc335a6 name=06_worldmodel_kernel version=1.0.0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Loaded kernel                  hash_prefix=7dbefcc1 name=07_execution_kernel version=1.0.0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Loaded kernel                  hash_prefix=97fa6e06 name=08_safety_kernel version=1.0.0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Loaded kernel                  hash_prefix=be89fa0a name=09_developer_kernel version=1.0.0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Loaded kernel                  hash_prefix=0cd5d4b3 name=10_packet_protocol_kernel version=1.0.0
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] All kernels loaded and parsed  kernel_count=10
l9-bootstrap  | 2026-02-02 13:59:18 [debug    ] bootstrap.phase.metrics        agent_id=l9-primary duration_ms=73.73380800709128 phase=1
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] ✓ Phase 1 complete (10 kernels loaded)
l9-bootstrap  | 2026-02-02 13:59:18 [info     ] Phase 2: Instantiating agent...
l9-bootstrap  | 2026-02-02 13:59:19 [info     ] Agent registered in Neo4j      agent_id=l9-primary instance_id=fd33c142-cb75-40e4-808d-24c58e1793a9
l9-bootstrap  | 2026-02-02 13:59:19 [info     ] Redis connected: redis:6379/0
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Redis working memory initialized agent_id=l9-primary key=l9:agent:l9-primary:working_memory ttl_hours=24
l9-bootstrap  | 2026-02-02 13:59:19 [info     ] Instantiated agent             agent_id=l9-primary instance_id=fd33c142-cb75-40e4-808d-24c58e1793a9 redis_working_memory=True
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] bootstrap.phase.metrics        agent_id=l9-primary duration_ms=512.9478330491111 phase=2
l9-bootstrap  | 2026-02-02 13:59:19 [info     ] ✓ Phase 2 complete (instance: fd33c142...)
l9-bootstrap  | 2026-02-02 13:59:19 [info     ] Phase 3: Binding kernels...
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Bound kernel to agent          agent_id=l9-primary kernel=01_master_kernel
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Bound kernel to agent          agent_id=l9-primary kernel=02_identity_kernel
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Bound kernel to agent          agent_id=l9-primary kernel=03_cognitive_kernel
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Bound kernel to agent          agent_id=l9-primary kernel=04_behavioral_kernel
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Bound kernel to agent          agent_id=l9-primary kernel=05_memory_kernel
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Bound kernel to agent          agent_id=l9-primary kernel=06_worldmodel_kernel
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Bound kernel to agent          agent_id=l9-primary kernel=07_execution_kernel
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Bound kernel to agent          agent_id=l9-primary kernel=08_safety_kernel
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Bound kernel to agent          agent_id=l9-primary kernel=09_developer_kernel
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Bound kernel to agent          agent_id=l9-primary kernel=10_packet_protocol_kernel
l9-bootstrap  | 2026-02-02 13:59:19 [info     ] Verified kernels bound to agent agent_id=l9-primary kernel_count=10
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] bootstrap.phase.metrics        agent_id=l9-primary duration_ms=726.469817920588 phase=3
l9-bootstrap  | 2026-02-02 13:59:19 [info     ] ✓ Phase 3 complete
l9-bootstrap  | 2026-02-02 13:59:19 [info     ] Phase 4: Loading identity persona...
l9-bootstrap  | 2026-02-02 13:59:19 [warning  ] Identity YAML not found, using defaults agent_id=l9-primary tried_path=private/agents/identity/l9-primary_identity.yaml
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] bootstrap.phase.metrics        agent_id=l9-primary duration_ms=0.2642190083861351 phase=4
l9-bootstrap  | 2026-02-02 13:59:19 [info     ] ✓ Phase 4 complete
l9-bootstrap  | 2026-02-02 13:59:19 [info     ] Phase 5: Binding tools & capabilities...
l9-bootstrap  | 2026-02-02 13:59:19 [debug    ] Tool registry not available, using default tools
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] Bound tool to agent            agent_id=l9-primary tool=memory_search
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] Bound tool to agent            agent_id=l9-primary tool=memory_write
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] Bound tool to agent            agent_id=l9-primary tool=gmp_run
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] Bound tool to agent            agent_id=l9-primary tool=git_commit
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] Tools bound to agent           agent_id=l9-primary tool_count=4
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] bootstrap.phase.metrics        agent_id=l9-primary duration_ms=263.01622902974486 phase=5
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] ✓ Phase 5 complete
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] Phase 6: Wiring governance gates...
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] Linked tool to Safety kernel   enforcement=STRICT tool=git_commit
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] Governance gates wired         agent_id=l9-primary tools_wired=4
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] bootstrap.phase.metrics        agent_id=l9-primary duration_ms=313.86536499485373 phase=6
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] ✓ Phase 6 complete
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] Phase 7: Verifying & locking...
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] ✓ Kernels verified             count=10
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] ✓ Identity verified            designation=l9-primary
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] ✓ Tools verified               count=4
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] RLS config loaded              org_id=quantumai org_uuid=14910cef-fea1-51d7-9a28-05579e6c0c18 tenant_id=l9 tenant_uuid=73350468-3158-5d0f-9b8c-9b193d96fc4b user_id=l9-shared user_uuid=2f00c090-3816-51a0-806c-34d32522a070
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] memory_scope_policies.loaded   callers=['L', 'C', 'default'] path=/app/config/policies/memory_scope.yaml
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] Processing packet: type=memory_write
l9-bootstrap  | 2026-02-02 13:59:20 [warning  ] injection_markers_detected     marker_count=1 markers=[] packet_id=82571a7b-3ef0-47b9-bbd1-644eafeed043 packet_type=memory_write
l9-bootstrap  | 2026-02-02 13:59:20 [info     ] enrichment_dag_start           packet_id=ac4beeb5-63f9-5edd-b3f9-7ee750f15ff2 packet_type=memory_write
l9-bootstrap  | 2026-02-02 13:59:20 [debug    ] Generating embedding for text: {'chunk_type': 'audit', 'event': 'agent_initialized', 'initialization_signature': '125f9c08edb991525...
l9-bootstrap  | 2026-02-02 13:59:22 [debug    ] Inserted semantic embedding fe9b9a11-4e86-43d0-8184-d39c8ac7e7db with scope=shared
l9-bootstrap  | 2026-02-02 13:59:22 [debug    ] Stored embedding fe9b9a11-4e86-43d0-8184-d39c8ac7e7db with scope=shared
l9-bootstrap  | 2026-02-02 13:59:22 [debug    ] enrichment_semantic_embedded   embedding_id=fe9b9a11-4e86-43d0-8184-d39c8ac7e7db packet_id=ac4beeb5-63f9-5edd-b3f9-7ee750f15ff2
l9-bootstrap  | 2026-02-02 13:59:22 [debug    ] enrichment_entities_extracted  count=0 packet_id=ac4beeb5-63f9-5edd-b3f9-7ee750f15ff2
l9-bootstrap  | 2026-02-02 13:59:22 [debug    ] Inserted packet ac4beeb5-63f9-5edd-b3f9-7ee750f15ff2 with thread_id=None, parent_ids=[], importance=None
l9-bootstrap  | 2026-02-02 13:59:22 [info     ] enrichment_dag_tier_1_success  duration_ms=2025.2042200881988 facts=0 packet_id=ac4beeb5-63f9-5edd-b3f9-7ee750f15ff2 relationships=0
l9-bootstrap  | 2026-02-02 13:59:22 [info     ] Packet ac4beeb5-63f9-5edd-b3f9-7ee750f15ff2 processed: status=ok, tables=['packets', 'knowledge_facts', 'relationships']
l9-bootstrap  | 2026-02-02 13:59:22 [info     ] ✓ Audit trail written
l9-bootstrap  | 2026-02-02 13:59:22 [info     ] ✓ Agent initialized and READY  agent_id=l9-primary signature=125f9c08edb99152...
l9-bootstrap  | 2026-02-02 13:59:22 [debug    ] bootstrap.phase.metrics        agent_id=l9-primary duration_ms=2174.116928013973 phase=7
l9-bootstrap  | 2026-02-02 13:59:22 [info     ] ✓ Phase 7 complete (signature: 125f9c08edb99152...)
l9-bootstrap  | 2026-02-02 13:59:22 [info     ] ╔════════════════════════════════════════╗
l9-bootstrap  | 2026-02-02 13:59:22 [info     ] ║  SUCCESS: l9-primary initialized
l9-bootstrap  | 2026-02-02 13:59:22 [info     ] ║  Instance: fd33c142-cb7...
l9-bootstrap  | 2026-02-02 13:59:22 [info     ] ║  Status: READY
l9-bootstrap  | 2026-02-02 13:59:22 [info     ] ╚════════════════════════════════════════╝
l9-bootstrap  | [BOOTSTRAP] Writing bootstrap artifact
l9-bootstrap  | [BOOTSTRAP] SUCCESS
