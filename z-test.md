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

docker compose logs l9-api --tail=50 | grep -E 'RLS|packet|Failed to fetch'
-rw-r--r-- 1 root root 11K Jan 26 22:25 migrations/0001_init_memory_substrate.sql
-rw-r--r-- 1 root root 2.2K Jan 26 22:25 migrations/0002_enhance_packet_store.sql
-rw-r--r-- 1 root root 1.2K Jan 26 22:25 migrations/0003_init_tasks.sql
-rw-r--r-- 1 root root 1.8K Jan 26 22:25 migrations/0004_init_world_model_entities.sql
-rw-r--r-- 1 root root 2.8K Jan 26 22:25 migrations/0005_init_knowledge_facts.sql
-rw-r--r-- 1 root root 2.2K Jan 26 22:25 migrations/0006_init_world_model_updates.sql
-rw-r--r-- 1 root root 1.8K Jan 26 22:25 migrations/0007_init_world_model_snapshots.sql
-rw-r--r-- 1 root root 49K Jan 26 22:25 migrations/0008_memory_substrate_10x.sql
-rw-r--r-- 1 root root 18K Jan 26 22:25 migrations/0009_feedback_and_effectiveness.sql
-rw-r--r-- 1 root root 2.1K Jan 22 20:56 migrations/0010_add_fact_deprecation.sql
Running migrations/0001_init_memory_substrate.sql...
psql:migrations/0001_init_memory_substrate.sql:8: NOTICE: extension "uuid-ossp" already exists, skipping
CREATE EXTENSION
psql:migrations/0001_init_memory_substrate.sql:9: NOTICE: extension "vector" already exists, skipping
CREATE EXTENSION
psql:migrations/0001_init_memory_substrate.sql:24: NOTICE: relation "agent_memory_events" already exists, skipping
CREATE TABLE
psql:migrations/0001_init_memory_substrate.sql:26: NOTICE: relation "idx_agent_memory_events_agent_id" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:27: NOTICE: relation "idx_agent_memory_events_timestamp" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:28: NOTICE: relation "idx_agent_memory_events_event_type" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:29: NOTICE: relation "idx_agent_memory_events_packet_id" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:42: NOTICE: relation "semantic_memory" already exists, skipping
CREATE TABLE
psql:migrations/0001_init_memory_substrate.sql:44: NOTICE: relation "idx_semantic_memory_agent_id" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:45: NOTICE: relation "idx_semantic_memory_created_at" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:54: NOTICE: relation "idx_semantic_memory_vector_hnsw" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:68: NOTICE: relation "agent_log" already exists, skipping
CREATE TABLE
psql:migrations/0001_init_memory_substrate.sql:70: NOTICE: relation "idx_agent_log_agent_id" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:71: NOTICE: relation "idx_agent_log_timestamp" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:72: NOTICE: relation "idx_agent_log_level" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:90: NOTICE: relation "reasoning_traces" already exists, skipping
CREATE TABLE
psql:migrations/0001_init_memory_substrate.sql:92: NOTICE: relation "idx_reasoning_traces_agent_id" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:93: NOTICE: relation "idx_reasoning_traces_packet_id" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:94: NOTICE: relation "idx_reasoning_traces_created_at" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:108: NOTICE: relation "packet_store" already exists, skipping
CREATE TABLE
psql:migrations/0001_init_memory_substrate.sql:110: NOTICE: relation "idx_packet_store_packet_type" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:111: NOTICE: relation "idx_packet_store_timestamp" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:112: NOTICE: relation "idx_packet_store_type_timestamp" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:124: NOTICE: relation "graph_checkpoints" already exists, skipping
CREATE TABLE
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:127: NOTICE: relation "idx_graph_checkpoints_updated_at" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:139: NOTICE: relation "buyer_profiles" already exists, skipping
CREATE TABLE
psql:migrations/0001_init_memory_substrate.sql:141: NOTICE: relation "idx_buyer_profiles_name" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:142: NOTICE: relation "idx_buyer_profiles_updated_at" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:154: NOTICE: relation "supplier_profiles" already exists, skipping
CREATE TABLE
psql:migrations/0001_init_memory_substrate.sql:156: NOTICE: relation "idx_supplier_profiles_name" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:157: NOTICE: relation "idx_supplier_profiles_updated_at" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:172: NOTICE: relation "transactions" already exists, skipping
CREATE TABLE
psql:migrations/0001_init_memory_substrate.sql:174: NOTICE: relation "idx_transactions_supplier_id" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:175: NOTICE: relation "idx_transactions_buyer_id" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:176: NOTICE: relation "idx_transactions_timestamp" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:189: NOTICE: relation "material_edges" already exists, skipping
CREATE TABLE
psql:migrations/0001_init_memory_substrate.sql:191: NOTICE: relation "idx_material_edges_updated_at" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:203: NOTICE: relation "entity_metadata" already exists, skipping
CREATE TABLE
psql:migrations/0001_init_memory_substrate.sql:205: NOTICE: relation "idx_entity_metadata_entity_type" already exists, skipping
CREATE INDEX
psql:migrations/0001_init_memory_substrate.sql:206: NOTICE: relation "idx_entity_metadata_updated_at" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
Running migrations/0002_enhance_packet_store.sql...
psql:migrations/0002_enhance_packet_store.sql:13: NOTICE: column "thread_id" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0002_enhance_packet_store.sql:17: NOTICE: column "parent_ids" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0002_enhance_packet_store.sql:21: NOTICE: column "tags" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0002_enhance_packet_store.sql:25: NOTICE: column "ttl" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0002_enhance_packet_store.sql:29: NOTICE: relation "idx_packet_thread" already exists, skipping
CREATE INDEX
psql:migrations/0002_enhance_packet_store.sql:32: NOTICE: relation "idx_packet_lineage" already exists, skipping
CREATE INDEX
psql:migrations/0002_enhance_packet_store.sql:35: NOTICE: relation "idx_packet_tags" already exists, skipping
CREATE INDEX
psql:migrations/0002_enhance_packet_store.sql:39: NOTICE: relation "idx_packet_ttl" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
Running migrations/0003_init_tasks.sql...
psql:migrations/0003_init_tasks.sql:17: NOTICE: relation "tasks" already exists, skipping
CREATE TABLE
psql:migrations/0003_init_tasks.sql:19: NOTICE: relation "idx_tasks_status" already exists, skipping
CREATE INDEX
psql:migrations/0003_init_tasks.sql:20: NOTICE: relation "idx_tasks_type" already exists, skipping
CREATE INDEX
psql:migrations/0003_init_tasks.sql:21: NOTICE: relation "idx_tasks_created_at" already exists, skipping
CREATE INDEX
COMMENT
Running migrations/0004_init_world_model_entities.sql...
psql:migrations/0004_init_world_model_entities.sql:16: NOTICE: relation "world_model_entities" already exists, skipping
CREATE TABLE
psql:migrations/0004_init_world_model_entities.sql:20: NOTICE: relation "idx_wm_entities_confidence" already exists, skipping
CREATE INDEX
psql:migrations/0004_init_world_model_entities.sql:24: NOTICE: relation "idx_wm_entities_type" already exists, skipping
CREATE INDEX
psql:migrations/0004_init_world_model_entities.sql:28: NOTICE: relation "idx_wm_entities_updated" already exists, skipping
CREATE INDEX
psql:migrations/0004_init_world_model_entities.sql:32: NOTICE: relation "idx_wm_entities_attributes" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
Running migrations/0005_init_knowledge_facts.sql...
psql:migrations/0005_init_knowledge_facts.sql:24: NOTICE: relation "knowledge_facts" already exists, skipping
CREATE TABLE
psql:migrations/0005_init_knowledge_facts.sql:28: NOTICE: relation "idx_knowledge_facts_subject" already exists, skipping
CREATE INDEX
psql:migrations/0005_init_knowledge_facts.sql:31: NOTICE: relation "idx_knowledge_facts_predicate" already exists, skipping
CREATE INDEX
psql:migrations/0005_init_knowledge_facts.sql:35: NOTICE: relation "idx_knowledge_facts_source_packet" already exists, skipping
CREATE INDEX
psql:migrations/0005_init_knowledge_facts.sql:38: NOTICE: relation "idx_knowledge_facts_created_at" already exists, skipping
CREATE INDEX
psql:migrations/0005_init_knowledge_facts.sql:42: NOTICE: relation "idx_knowledge_facts_object" already exists, skipping
CREATE INDEX
psql:migrations/0005_init_knowledge_facts.sql:46: NOTICE: relation "idx_knowledge_facts_subject_predicate" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
Running migrations/0006_init_world_model_updates.sql...
psql:migrations/0006_init_world_model_updates.sql:19: NOTICE: relation "world_model_updates" already exists, skipping
CREATE TABLE
psql:migrations/0006_init_world_model_updates.sql:23: NOTICE: relation "idx_wm_updates_confidence" already exists, skipping
CREATE INDEX
psql:migrations/0006_init_world_model_updates.sql:27: NOTICE: relation "idx_wm_updates_insight_type" already exists, skipping
CREATE INDEX
psql:migrations/0006_init_world_model_updates.sql:31: NOTICE: relation "idx_wm_updates_applied" already exists, skipping
CREATE INDEX
psql:migrations/0006_init_world_model_updates.sql:35: NOTICE: relation "idx_wm_updates_insight" already exists, skipping
CREATE INDEX
psql:migrations/0006_init_world_model_updates.sql:39: NOTICE: relation "idx_wm_updates_entities" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
Running migrations/0007_init_world_model_snapshots.sql...
psql:migrations/0007_init_world_model_snapshots.sql:17: NOTICE: relation "world_model_snapshots" already exists, skipping
CREATE TABLE
psql:migrations/0007_init_world_model_snapshots.sql:21: NOTICE: relation "idx_wm_snapshots_created" already exists, skipping
CREATE INDEX
psql:migrations/0007_init_world_model_snapshots.sql:25: NOTICE: relation "idx_wm_snapshots_version" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
Running migrations/0008_memory_substrate_10x.sql...
BEGIN
psql:migrations/0008_memory_substrate_10x.sql:37: NOTICE: extension "uuid-ossp" already exists, skipping
CREATE EXTENSION
psql:migrations/0008_memory_substrate_10x.sql:38: NOTICE: extension "vector" already exists, skipping
CREATE EXTENSION
psql:migrations/0008_memory_substrate_10x.sql:39: NOTICE: extension "pgcrypto" already exists, skipping
CREATE EXTENSION
CREATE FUNCTION
COMMENT
CREATE FUNCTION
CREATE FUNCTION
CREATE FUNCTION
CREATE FUNCTION
CREATE FUNCTION
CREATE FUNCTION
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:144: NOTICE: relation "memory_embeddings" already exists, skipping
CREATE TABLE
COMMENT
COMMENT
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:151: NOTICE: relation "idx_embeddings_packet" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:152: NOTICE: relation "idx_embeddings_type" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:153: NOTICE: relation "idx_embeddings_created" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:158: NOTICE: relation "idx_embeddings_vector_content" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:162: NOTICE: relation "idx_embeddings_vector_entity" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:166: NOTICE: relation "idx_embeddings_vector_summary" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:169: NOTICE: relation "idx_embeddings_tenant" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:170: NOTICE: relation "idx_embeddings_org" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:171: NOTICE: relation "idx_embeddings_user" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:172: NOTICE: relation "idx_embeddings_corr" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:198: NOTICE: relation "memory_access_log" already exists, skipping
CREATE TABLE
COMMENT
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:203: NOTICE: relation "idx_access_target" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:204: NOTICE: relation "idx_access_agent" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:205: NOTICE: relation "idx_access_time" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:206: NOTICE: relation "idx_access_useful" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:209: NOTICE: relation "idx_access_tenant" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:210: NOTICE: relation "idx_access_org" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:211: NOTICE: relation "idx_access_user" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:212: NOTICE: relation "idx_access_corr" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:235: NOTICE: relation "entity_relationships" already exists, skipping
CREATE TABLE
COMMENT
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:240: NOTICE: relation "idx_rel_source" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:241: NOTICE: relation "idx_rel_target" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:242: NOTICE: relation "idx_rel_type" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:243: NOTICE: relation "idx_rel_confidence" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:246: NOTICE: relation "idx_rel_tenant" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:247: NOTICE: relation "idx_rel_org" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:248: NOTICE: relation "idx_rel_user" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:249: NOTICE: relation "idx_rel_corr" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:253: NOTICE: relation "idx_rel_unique" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:282: NOTICE: relation "memory_summaries" already exists, skipping
CREATE TABLE
COMMENT
COMMENT
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:288: NOTICE: relation "idx_summary_scope" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:289: NOTICE: relation "idx_summary_created" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:290: NOTICE: relation "idx_summary_valid" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:291: NOTICE: relation "idx_summary_entities" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:294: NOTICE: relation "idx_summary_tenant" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:295: NOTICE: relation "idx_summary_org" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:296: NOTICE: relation "idx_summary_user" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:297: NOTICE: relation "idx_summary_corr" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:302: NOTICE: relation "idx_summary_vector" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:335: NOTICE: relation "reflection_store" already exists, skipping
CREATE TABLE
COMMENT
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:340: NOTICE: relation "idx_reflection_task" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:341: NOTICE: relation "idx_reflection_type" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:342: NOTICE: relation "idx_reflection_priority" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:343: NOTICE: relation "idx_reflection_agent" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:344: NOTICE: relation "idx_reflection_entities" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:345: NOTICE: relation "idx_reflection_tags" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:346: NOTICE: relation "idx_reflection_created" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:347: NOTICE: relation "idx_reflection_confidence" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:350: NOTICE: relation "idx_reflection_tenant" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:351: NOTICE: relation "idx_reflection_org" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:352: NOTICE: relation "idx_reflection_user" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:353: NOTICE: relation "idx_reflection_corr" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:358: NOTICE: relation "idx_reflection_vector" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:388: NOTICE: relation "task_reflections" already exists, skipping
CREATE TABLE
COMMENT
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:393: NOTICE: relation "idx_task_refl_outcome" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:394: NOTICE: relation "idx_task_refl_patterns" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:395: NOTICE: relation "idx_task_refl_created" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:398: NOTICE: relation "idx_task_refl_tenant" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:399: NOTICE: relation "idx_task_refl_org" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:400: NOTICE: relation "idx_task_refl_user" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:401: NOTICE: relation "idx_task_refl_corr" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:410: NOTICE: column "scope" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:413: NOTICE: column "importance_score" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:416: NOTICE: column "access_count" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:417: NOTICE: column "last_accessed" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:420: NOTICE: column "confidence_updated_at" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:421: NOTICE: column "contradiction_count" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:424: NOTICE: column "chunk_count" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:425: NOTICE: column "is_chunked" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:428: NOTICE: column "content_hash" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:431: NOTICE: column "processing_status" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:434: NOTICE: column "tenant_id" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:435: NOTICE: column "org_id" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:436: NOTICE: column "user_id" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:437: NOTICE: column "correlation_id" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:440: NOTICE: column "session_id" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:441: NOTICE: column "trace_id" of relation "packet_store" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:444: NOTICE: relation "idx_packet_scope" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:445: NOTICE: relation "idx_packet_scope_type" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:446: NOTICE: relation "idx_packet_scope_time" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:449: NOTICE: relation "idx_packet_importance" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:450: NOTICE: relation "idx_packet_importance_type" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:453: NOTICE: relation "idx_packet_accessed" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:454: NOTICE: relation "idx_packet_access_count" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:458: NOTICE: relation "idx_packet_content_hash" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:461: NOTICE: relation "idx_packet_tenant_ts" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:462: NOTICE: relation "idx_packet_org_ts" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:463: NOTICE: relation "idx_packet_user_ts" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:464: NOTICE: relation "idx_packet_corr" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:481: NOTICE: column "subject_normalized" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:482: NOTICE: column "object_normalized" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:485: NOTICE: column "object_type" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:488: NOTICE: column "confidence_updated_at" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:489: NOTICE: column "contradiction_count" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:490: NOTICE: column "supporting_packet_count" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:493: NOTICE: column "access_count" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:494: NOTICE: column "last_accessed" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:497: NOTICE: column "scope" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:500: NOTICE: column "tenant_id" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:501: NOTICE: column "org_id" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:502: NOTICE: column "user_id" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:503: NOTICE: column "correlation_id" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:506: NOTICE: relation "idx_facts_subject_norm" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:507: NOTICE: relation "idx_facts_object_norm" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:508: NOTICE: relation "idx_facts_scope" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:511: NOTICE: relation "idx_facts_confidence_desc" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:512: NOTICE: relation "idx_facts_access" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:515: NOTICE: relation "idx_facts_tenant_ts" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:516: NOTICE: relation "idx_facts_org_ts" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:517: NOTICE: relation "idx_facts_user_ts" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:518: NOTICE: relation "idx_facts_corr" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:531: NOTICE: column "importance_score" of relation "semantic_memory" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:532: NOTICE: column "access_count" of relation "semantic_memory" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:533: NOTICE: column "last_accessed" of relation "semantic_memory" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:534: NOTICE: column "embedding_type" of relation "semantic_memory" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:535: NOTICE: column "scope" of relation "semantic_memory" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:538: NOTICE: column "tenant_id" of relation "semantic_memory" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:539: NOTICE: column "org_id" of relation "semantic_memory" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:540: NOTICE: column "user_id" of relation "semantic_memory" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:541: NOTICE: column "correlation_id" of relation "semantic_memory" already exists, skipping
ALTER TABLE
psql:migrations/0008_memory_substrate_10x.sql:543: NOTICE: relation "idx_semantic_importance" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:544: NOTICE: relation "idx_semantic_scope" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:547: NOTICE: relation "idx_semantic_tenant" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:548: NOTICE: relation "idx_semantic_org" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:549: NOTICE: relation "idx_semantic_user" already exists, skipping
CREATE INDEX
CREATE FUNCTION
COMMENT
CREATE FUNCTION
COMMENT
CREATE FUNCTION
COMMENT
CREATE FUNCTION
COMMENT
CREATE FUNCTION
COMMENT
CREATE FUNCTION
COMMENT
CREATE FUNCTION
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:723: NOTICE: relation "mv_agent_recent_important" already exists, skipping
CREATE MATERIALIZED VIEW
psql:migrations/0008_memory_substrate_10x.sql:725: NOTICE: relation "idx_mv_agent_recent" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:726: NOTICE: relation "idx_mv_agent_score" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:742: NOTICE: relation "mv_entity_graph" already exists, skipping
CREATE MATERIALIZED VIEW
psql:migrations/0008_memory_substrate_10x.sql:744: NOTICE: relation "idx_mv_entity_unique" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:745: NOTICE: relation "idx_mv_entity_source" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:746: NOTICE: relation "idx_mv_entity_target" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:747: NOTICE: relation "idx_mv_entity_mentions" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:770: NOTICE: relation "mv_high_confidence_facts" already exists, skipping
CREATE MATERIALIZED VIEW
psql:migrations/0008_memory_substrate_10x.sql:772: NOTICE: relation "idx_mv_facts_id" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:773: NOTICE: relation "idx_mv_facts_subject" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:774: NOTICE: relation "idx_mv_facts_score" already exists, skipping
CREATE INDEX
psql:migrations/0008_memory_substrate_10x.sql:787: NOTICE: relation "mv_reflection_patterns" already exists, skipping
CREATE MATERIALIZED VIEW
psql:migrations/0008_memory_substrate_10x.sql:789: NOTICE: relation "idx_mv_refl_type" already exists, skipping
CREATE INDEX
CREATE FUNCTION
DROP TRIGGER
CREATE TRIGGER
CREATE FUNCTION
DROP TRIGGER
CREATE TRIGGER
CREATE PROCEDURE
CREATE PROCEDURE
CREATE PROCEDURE
CREATE PROCEDURE
DO
DO
DROP POLICY
CREATE POLICY
DROP POLICY
CREATE POLICY
DROP POLICY
CREATE POLICY
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
psql:migrations/0008_memory_substrate_10x.sql:1128: NOTICE: ✅ Migration 0008_memory_substrate_10x.sql completed successfully
psql:migrations/0008_memory_substrate_10x.sql:1128: NOTICE: - 6 new tables created
psql:migrations/0008_memory_substrate_10x.sql:1128: NOTICE: - Multi-tenant columns (tenant_id, org_id, user_id, correlation_id) added
psql:migrations/0008_memory_substrate_10x.sql:1128: NOTICE: - packet_store enhanced with scope, importance, access tracking
psql:migrations/0008_memory_substrate_10x.sql:1128: NOTICE: - knowledge_facts enhanced with normalization and confidence decay
psql:migrations/0008_memory_substrate_10x.sql:1128: NOTICE: - Row Level Security enabled with 4 policies per table
psql:migrations/0008_memory_substrate_10x.sql:1128: NOTICE: - Materialized views created for fast retrieval
psql:migrations/0008_memory_substrate_10x.sql:1128: NOTICE: - Maintenance procedures created for scheduled jobs
psql:migrations/0008_memory_substrate_10x.sql:1128: NOTICE: - Session variable functions: l9_set_scope(), l9_current_tenant(), etc.
DO
COMMIT
Running migrations/0009_feedback_and_effectiveness.sql...
BEGIN
psql:migrations/0009_feedback_and_effectiveness.sql:64: NOTICE: relation "feedback_events" already exists, skipping
CREATE TABLE
COMMENT
COMMENT
COMMENT
COMMENT
psql:migrations/0009_feedback_and_effectiveness.sql:72: NOTICE: relation "idx_feedback_packet" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:73: NOTICE: relation "idx_feedback_reflection" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:74: NOTICE: relation "idx_feedback_task" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:75: NOTICE: relation "idx_feedback_agent" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:76: NOTICE: relation "idx_feedback_type" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:77: NOTICE: relation "idx_feedback_processed" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:78: NOTICE: relation "idx_feedback_created" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:79: NOTICE: relation "idx_feedback_unprocessed" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:82: NOTICE: relation "idx_feedback_tenant" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:83: NOTICE: relation "idx_feedback_org" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:84: NOTICE: relation "idx_feedback_user" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:85: NOTICE: relation "idx_feedback_corr" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:94: NOTICE: column "success_count" of relation "reflection_store" already exists, skipping
ALTER TABLE
psql:migrations/0009_feedback_and_effectiveness.sql:95: NOTICE: column "failure_count" of relation "reflection_store" already exists, skipping
ALTER TABLE
psql:migrations/0009_feedback_and_effectiveness.sql:96: NOTICE: column "effectiveness_score" of relation "reflection_store" already exists, skipping
ALTER TABLE
psql:migrations/0009_feedback_and_effectiveness.sql:97: NOTICE: column "last_applied_at" of relation "reflection_store" already exists, skipping
ALTER TABLE
psql:migrations/0009_feedback_and_effectiveness.sql:98: NOTICE: column "times_applied" of relation "reflection_store" already exists, skipping
ALTER TABLE
psql:migrations/0009_feedback_and_effectiveness.sql:101: NOTICE: relation "idx_reflection_effectiveness" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:102: NOTICE: relation "idx_reflection_applied" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
CREATE FUNCTION
COMMENT
CREATE FUNCTION
COMMENT
CREATE FUNCTION
COMMENT
CREATE FUNCTION
COMMENT
psql:migrations/0009_feedback_and_effectiveness.sql:335: NOTICE: relation "mv_effective_reflections" already exists, skipping
CREATE MATERIALIZED VIEW
psql:migrations/0009_feedback_and_effectiveness.sql:338: NOTICE: relation "idx_mv_eff_refl_id" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:339: NOTICE: relation "idx_mv_eff_refl_type" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:340: NOTICE: relation "idx_mv_eff_refl_score" already exists, skipping
CREATE INDEX
psql:migrations/0009_feedback_and_effectiveness.sql:341: NOTICE: relation "idx_mv_eff_refl_agent" already exists, skipping
CREATE INDEX
COMMENT
ALTER TABLE
ALTER TABLE
DROP POLICY
CREATE POLICY
DROP POLICY
CREATE POLICY
DROP POLICY
CREATE POLICY
CREATE PROCEDURE
psql:migrations/0009_feedback_and_effectiveness.sql:445: NOTICE: ✅ Migration 0009_feedback_and_effectiveness.sql completed successfully
psql:migrations/0009_feedback_and_effectiveness.sql:445: NOTICE: - feedback_events table created
psql:migrations/0009_feedback_and_effectiveness.sql:445: NOTICE: - reflection_store enhanced with effectiveness tracking
psql:migrations/0009_feedback_and_effectiveness.sql:445: NOTICE: - 4 functions created: update_reflection_effectiveness, process_feedback_event, decay_reflection_confidence, get_effective_reflections
psql:migrations/0009_feedback_and_effectiveness.sql:445: NOTICE: - mv_effective_reflections materialized view created
psql:migrations/0009_feedback_and_effectiveness.sql:445: NOTICE: - RLS policies applied to feedback_events
psql:migrations/0009_feedback_and_effectiveness.sql:445: NOTICE: - refresh_memory_views procedure updated
DO
COMMIT
Running migrations/0010_add_fact_deprecation.sql...
psql:migrations/0010_add_fact_deprecation.sql:13: NOTICE: column "deprecated" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0010_add_fact_deprecation.sql:16: NOTICE: column "deprecated_at" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0010_add_fact_deprecation.sql:19: NOTICE: column "deprecated_reason" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0010_add_fact_deprecation.sql:22: NOTICE: column "contradiction_count" of relation "knowledge_facts" already exists, skipping
ALTER TABLE
psql:migrations/0010_add_fact_deprecation.sql:27: NOTICE: relation "idx_knowledge_facts_active" already exists, skipping
CREATE INDEX
psql:migrations/0010_add_fact_deprecation.sql:32: NOTICE: relation "idx_knowledge_facts_deprecated" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
Running migrations/0011_tool_audit_log.sql...
BEGIN
psql:migrations/0011_tool_audit_log.sql:19: NOTICE: relation "tool_audit_log" already exists, skipping
CREATE TABLE
psql:migrations/0011_tool_audit_log.sql:23: NOTICE: relation "idx_tool_audit_agent_timestamp" already exists, skipping
CREATE INDEX
psql:migrations/0011_tool_audit_log.sql:25: NOTICE: relation "idx_tool_audit_tool_timestamp" already exists, skipping
CREATE INDEX
psql:migrations/0011_tool_audit_log.sql:27: NOTICE: relation "idx_tool_audit_request_id" already exists, skipping
CREATE INDEX
COMMIT
Running migrations/0012_fix_graph_checkpoints_unique.sql...
psql:migrations/0012_fix_graph_checkpoints_unique.sql:25: NOTICE: Added UNIQUE constraint on graph_checkpoints.agent_id
DO
Running migrations/0013_mcp_audit_columns.sql...
BEGIN
psql:migrations/0013_mcp_audit_columns.sql:21: NOTICE: column "caller" of relation "tool_audit_log" already exists, skipping
ALTER TABLE
COMMENT
psql:migrations/0013_mcp_audit_columns.sql:28: NOTICE: column "project_id" of relation "tool_audit_log" already exists, skipping
ALTER TABLE
COMMENT
psql:migrations/0013_mcp_audit_columns.sql:36: NOTICE: relation "idx_tool_audit_caller" already exists, skipping
CREATE INDEX
psql:migrations/0013_mcp_audit_columns.sql:40: NOTICE: relation "idx_tool_audit_project" already exists, skipping
CREATE INDEX
psql:migrations/0013_mcp_audit_columns.sql:45: NOTICE: relation "idx_tool_audit_governance" already exists, skipping
CREATE INDEX
ANALYZE
COMMIT
Running migrations/0014_multi_checkpoint_support.sql...
psql:migrations/0014_multi_checkpoint_support.sql:35: NOTICE: Dropped UNIQUE constraint on graph_checkpoints.agent_id
DO
psql:migrations/0014_multi_checkpoint_support.sql:52: NOTICE: reason column already exists in graph_checkpoints
DO
psql:migrations/0014_multi_checkpoint_support.sql:69: NOTICE: checkpoint_number column already exists in graph_checkpoints
DO
DROP INDEX
psql:migrations/0014_multi_checkpoint_support.sql:80: NOTICE: relation "idx_graph_checkpoints_agent_updated" already exists, skipping
CREATE INDEX
psql:migrations/0014_multi_checkpoint_support.sql:84: NOTICE: relation "idx_graph_checkpoints_reason" already exists, skipping
CREATE INDEX
psql:migrations/0014_multi_checkpoint_support.sql:88: NOTICE: relation "idx_graph_checkpoints_agent_number" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
Running migrations/0015_knowledge_facts_upsert_key.sql...
psql:migrations/0015_knowledge_facts_upsert_key.sql:15: NOTICE: relation "idx_knowledge_facts_upsert_key" already exists, skipping
CREATE INDEX
COMMENT
Running migrations/0016_governance_scope_semantics.sql...
BEGIN
ALTER TABLE
ALTER TABLE
UPDATE 0
UPDATE 0
psql:migrations/0016_governance_scope_semantics.sql:61: NOTICE: relation "idx_packet_scope_governance" already exists, skipping
CREATE INDEX
DROP POLICY
CREATE POLICY
psql:migrations/0016_governance_scope_semantics.sql:108: NOTICE: === Migration 0016 Scope Semantics - Pre-Finalize ===
psql:migrations/0016_governance_scope_semantics.sql:108: NOTICE: Remaining shared: 0 (should be 0)
psql:migrations/0016_governance_scope_semantics.sql:108: NOTICE: Remaining cursor: 0 (should be 0)
psql:migrations/0016_governance_scope_semantics.sql:108: NOTICE: developer: 16
psql:migrations/0016_governance_scope_semantics.sql:108: NOTICE: global: 0
psql:migrations/0016_governance_scope_semantics.sql:108: NOTICE: l-private: 0
DO
ALTER TABLE
ALTER TABLE
DROP POLICY
CREATE POLICY
psql:migrations/0016_governance_scope_semantics.sql:146: NOTICE: ✅ Migration 0016 completed successfully
psql:migrations/0016_governance_scope_semantics.sql:146: NOTICE: - Scope semantics preserved: developer, global, l-private
psql:migrations/0016_governance_scope_semantics.sql:146: NOTICE: - Legacy scopes (shared, cursor) removed from CHECK constraint
psql:migrations/0016_governance_scope_semantics.sql:146: NOTICE: - New packets can only use: developer, global, l-private
DO
COMMIT
Running migrations/0017_governance_project_id.sql...
BEGIN
UPDATE 0
psql:migrations/0017_governance_project_id.sql:36: NOTICE: relation "idx_packet_project_id" already exists, skipping
CREATE INDEX
psql:migrations/0017_governance_project_id.sql:40: NOTICE: relation "idx_packet_scope_project" already exists, skipping
CREATE INDEX
ALTER TABLE
ALTER TABLE
psql:migrations/0017_governance_project_id.sql:85: NOTICE: === Migration 0017 Project ID Isolation ===
psql:migrations/0017_governance_project_id.sql:85: NOTICE: Total packets: 16
psql:migrations/0017_governance_project_id.sql:85: NOTICE: Packets with project_id=l9: 0
psql:migrations/0017_governance_project_id.sql:85: NOTICE: Packets with NULL project_id: 0 (should be 0)
psql:migrations/0017_governance_project_id.sql:85: NOTICE: ✅ Migration 0017 completed successfully
psql:migrations/0017_governance_project_id.sql:85: NOTICE: - All packets have project_id
psql:migrations/0017_governance_project_id.sql:85: NOTICE: - NOT NULL constraint enforced
DO
COMMIT
Running migrations/0018_semantic_facts.sql...
CREATE TABLE
psql:migrations/0018_semantic_facts.sql:68: ERROR: column cannot have more than 2000 dimensions for ivfflat index
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE FUNCTION
psql:migrations/0018_semantic_facts.sql:117: NOTICE: trigger "trigger_semantic_facts_updated_at" for relation "semantic_facts" does not exist, skipping
DROP TRIGGER
CREATE TRIGGER
ALTER TABLE
CREATE POLICY
CREATE POLICY
CREATE POLICY
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
Running migrations/0019_episodic_events.sql...
psql:migrations/0019_episodic_events.sql:61: ERROR: there is no unique constraint matching given keys for referenced table "packet_store"
psql:migrations/0019_episodic_events.sql:85: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:93: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:97: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:101: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:105: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:110: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:115: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:120: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:124: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:128: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:136: ERROR: relation "episodic_semantic_links" does not exist
psql:migrations/0019_episodic_events.sql:140: ERROR: relation "episodic_semantic_links" does not exist
psql:migrations/0019_episodic_events.sql:144: ERROR: relation "episodic_semantic_links" does not exist
CREATE FUNCTION
psql:migrations/0019_episodic_events.sql:157: NOTICE: relation "episodic_events" does not exist, skipping
DROP TRIGGER
psql:migrations/0019_episodic_events.sql:161: ERROR: relation "episodic_events" does not exist
CREATE FUNCTION
COMMENT
psql:migrations/0019_episodic_events.sql:189: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:194: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:202: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:211: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:216: ERROR: relation "episodic_semantic_links" does not exist
psql:migrations/0019_episodic_events.sql:226: ERROR: relation "episodic_semantic_links" does not exist
psql:migrations/0019_episodic_events.sql:231: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:232: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:233: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:234: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:235: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:236: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:237: ERROR: relation "episodic_events" does not exist
psql:migrations/0019_episodic_events.sql:239: ERROR: relation "episodic_semantic_links" does not exist
psql:migrations/0019_episodic_events.sql:240: ERROR: relation "episodic_semantic_links" does not exist
psql:migrations/0019_episodic_events.sql:241: ERROR: relation "episodic_semantic_links" does not exist
Running migrations/0020_optimize_vector_search.sql...
DROP INDEX
CREATE INDEX
psql:migrations/0020_optimize_vector_search.sql:23: NOTICE: relation "idx_semantic_memory_agent_created" already exists, skipping
CREATE INDEX
psql:migrations/0020_optimize_vector_search.sql:26: NOTICE: relation "idx_semantic_memory_payload_gin" already exists, skipping
CREATE INDEX
psql:migrations/0020_optimize_vector_search.sql:30: NOTICE: relation "idx_semantic_memory_payload_type" already exists, skipping
CREATE INDEX
Running migrations/0021_gmp_learning.sql...
psql:migrations/0021_gmp_learning.sql:32: NOTICE: relation "gmp_execution_history" already exists, skipping
CREATE TABLE
psql:migrations/0021_gmp_learning.sql:36: NOTICE: relation "idx_gmp_execution_gmp_id" already exists, skipping
CREATE INDEX
psql:migrations/0021_gmp_learning.sql:39: NOTICE: relation "idx_gmp_execution_task_type" already exists, skipping
CREATE INDEX
psql:migrations/0021_gmp_learning.sql:42: NOTICE: relation "idx_gmp_execution_created_at" already exists, skipping
CREATE INDEX
psql:migrations/0021_gmp_learning.sql:45: NOTICE: relation "idx_gmp_execution_task_type_confidence" already exists, skipping
CREATE INDEX
psql:migrations/0021_gmp_learning.sql:48: NOTICE: relation "idx_gmp_execution_error_analysis" already exists, skipping
CREATE INDEX
psql:migrations/0021_gmp_learning.sql:65: NOTICE: relation "learned_heuristics" already exists, skipping
CREATE TABLE
psql:migrations/0021_gmp_learning.sql:69: NOTICE: relation "idx_heuristics_heuristic_id" already exists, skipping
CREATE INDEX
psql:migrations/0021_gmp_learning.sql:73: NOTICE: relation "idx_heuristics_confidence" already exists, skipping
CREATE INDEX
psql:migrations/0021_gmp_learning.sql:76: NOTICE: relation "idx_heuristics_generated_date" already exists, skipping
CREATE INDEX
psql:migrations/0021_gmp_learning.sql:80: NOTICE: relation "idx_heuristics_active" already exists, skipping
CREATE INDEX
psql:migrations/0021_gmp_learning.sql:96: NOTICE: relation "autonomy_graduation_metrics" already exists, skipping
CREATE TABLE
CREATE FUNCTION
DROP TRIGGER
CREATE TRIGGER
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
psql:migrations/0021_gmp_learning.sql:151: NOTICE: Migration 0021_gmp_learning.sql completed successfully
DO
Running migrations/0022_temporal_fact_validity.sql...
ALTER TABLE
ALTER TABLE
ALTER TABLE
UPDATE 0
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE FUNCTION
COMMENT
COMMENT
COMMENT
COMMENT
Running migrations/0024_cmts_schema.sql...
BEGIN
psql:migrations/0024_cmts_schema.sql:20: ERROR: type "mutation_status" already exists
psql:migrations/0024_cmts_schema.sql:50: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:63: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:73: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:76: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:77: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:78: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:79: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:80: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:82: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:83: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:92: ERROR: current transaction is aborted, commands ignored until end of transaction block
psql:migrations/0024_cmts_schema.sql:97: ERROR: current transaction is aborted, commands ignored until end of transaction block
ROLLBACK
Running migrations/0025_tool_embeddings.sql...
psql:migrations/0025_tool_embeddings.sql:18: NOTICE: relation "tool_embeddings" already exists, skipping
CREATE TABLE
psql:migrations/0025_tool_embeddings.sql:25: NOTICE: relation "idx_tool_embeddings_vector" already exists, skipping
CREATE INDEX
psql:migrations/0025_tool_embeddings.sql:29: NOTICE: relation "idx_tool_embeddings_category" already exists, skipping
CREATE INDEX
CREATE FUNCTION
DROP TRIGGER
CREATE TRIGGER
COMMENT
COMMENT
COMMENT
Running migrations/0026_tool_bm25_index.sql...
psql:migrations/0026_tool_bm25_index.sql:10: NOTICE: column "search_vector" of relation "tool_embeddings" already exists, skipping
ALTER TABLE
UPDATE 0
psql:migrations/0026_tool_bm25_index.sql:19: NOTICE: relation "idx_tool_embeddings_search_vector" already exists, skipping
CREATE INDEX
CREATE FUNCTION
DROP TRIGGER
CREATE TRIGGER
COMMENT
Running migrations/0027_eval_results.sql...
psql:migrations/0027_eval_results.sql:38: NOTICE: relation "eval_results" already exists, skipping
CREATE TABLE
psql:migrations/0027_eval_results.sql:46: NOTICE: relation "idx_eval_results_agent_set_time" already exists, skipping
CREATE INDEX
psql:migrations/0027_eval_results.sql:50: NOTICE: relation "idx_eval_results_version" already exists, skipping
CREATE INDEX
psql:migrations/0027_eval_results.sql:54: NOTICE: relation "idx_eval_results_ci_run" already exists, skipping
CREATE INDEX
psql:migrations/0027_eval_results.sql:58: NOTICE: relation "idx_eval_results_created_at" already exists, skipping
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
CREATE VIEW
CREATE FUNCTION
COMMENT
Running migrations/20260125_tool_feedback_learning.sql...
BEGIN
psql:migrations/20260125_tool_feedback_learning.sql:39: NOTICE: relation "tool_execution_feedback" already exists, skipping
CREATE TABLE
psql:migrations/20260125_tool_feedback_learning.sql:45: NOTICE: relation "idx_tool_feedback_embedding" already exists, skipping
CREATE INDEX
psql:migrations/20260125_tool_feedback_learning.sql:49: NOTICE: relation "idx_tool_feedback_tool_success" already exists, skipping
CREATE INDEX
psql:migrations/20260125_tool_feedback_learning.sql:52: NOTICE: relation "idx_tool_feedback_task_type" already exists, skipping
CREATE INDEX
psql:migrations/20260125_tool_feedback_learning.sql:55: NOTICE: relation "idx_tool_feedback_agent" already exists, skipping
CREATE INDEX
psql:migrations/20260125_tool_feedback_learning.sql:72: NOTICE: relation "tool_success_rates_24h" already exists, skipping
CREATE MATERIALIZED VIEW
psql:migrations/20260125_tool_feedback_learning.sql:75: NOTICE: relation "idx_tool_success_rates_24h_lookup" already exists, skipping
CREATE INDEX
COMMENT
CREATE FUNCTION
psql:migrations/20260125_tool_feedback_learning.sql:112: NOTICE: relation "tool_learning_alerts" already exists, skipping
CREATE TABLE
psql:migrations/20260125_tool_feedback_learning.sql:116: NOTICE: relation "idx_tool_learning_alerts_unacked" already exists, skipping
CREATE INDEX
COMMIT
schemaname | tablename
------------+-----------
(0 rows)

[+] restart 0/1
⠇ Container l9-api Restarting
