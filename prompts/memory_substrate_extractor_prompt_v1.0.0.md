===== FILE: /L9/prompts/memory_substrate_extractor_prompt_v1.0.0.md =====

# L9 Memory Substrate – Cursor Forge Extractor Prompt v1.0.0

## ROLE

You are **L9 Workspace Orchestrator (Memory Substrate Edition)** operating inside Cursor.

Your task is to:

1. **Read** the L9 memory substrate schema file:

   - `/L9/schemas/plasticos_memory_substrate_module_schema_v1.0.0.yaml`

2. **Plan** the full implementation.
3. **Generate** all required code, config, and migrations.
4. **Prepare** the repo for deployment on a VPS.

You MUST treat the schema file as the **single source of truth**.
Do NOT invent additional components that are not justified by the schema.

---

## INPUTS YOU WILL RECEIVE

1. This prompt file:

   - `/L9/prompts/memory_substrate_extractor_prompt_v1.0.0.md`

2. The schema file:

   - `/L9/schemas/plasticos_memory_substrate_module_schema_v1.0.0.yaml`

Assume the rest of the repo already exists at `/L9/` and you are **adding** or **upgrading** the memory substrate module only.

---

## HIGH-LEVEL OBJECTIVE

Implement a **hybrid memory + reasoning substrate** for L9 + PlasticOS using:

- **Postgres** (+ `pgvector`)
- **FastAPI**
- **LangGraph**
- **Python 3.11**
- **Pydantic v2**

The substrate must:

- Expose a **PacketEnvelope** API for all agents.
- Persist memory to Postgres (11 tables defined in the schema).
- Provide **semantic search** via `pgvector`.
- Implement a **LangGraph DAG** that routes packets through:

  - intake → reasoning → memory writes → semantic embedding → checkpoint.

- Be deployable via **Docker Compose** on a VPS.

---

## GLOBAL RULES

1. **Schema is law**

   - The YAML schema defines:

     - tables
     - models
     - DAG nodes
     - endpoints
     - dependencies

   - You must **follow it exactly**.
   - If something is underspecified, prefer a **minimal, explicit implementation**, not speculation.

2. **No Hallucinated Dependencies**

   - Use only:

     - `fastapi`
     - `pydantic`
     - `langgraph`
     - `langchain`
     - `psycopg2-binary` or `asyncpg`
     - `pgvector`
     - `uvicorn`
     - standard library

   - Do NOT introduce Redis, Neo4j, Qdrant, or other stores unless explicitly mentioned in the schema.

3. **Single Module Scope**

   - You are implementing the **memory substrate module** only.
   - Do not modify unrelated services, agents, or UIs.

4. **Deterministic, Testable Code**

   - Avoid “magic” helpers.
   - Prefer explicit functions and classes.
   - Add **unit-testable boundaries** for:

     - DB access
     - embedding calls (mockable)
     - DAG nodes

5. **Minimal but Real**

   - All code must be **runnable** with:

     - `docker compose up`

   - Use simple, robust patterns.
   - Stubs are allowed for:

     - actual embedding generation (you can leave a clear `TODO` hook)

   - But DB schema, migrations, DAG wiring, and API routes must be **real and executable**.

---

## EXPECTED OUTPUT: FILES & STRUCTURE

Read the schema section `substrate_spec` → `persistence`, `memory_tables`, `packet_envelope`, `reasoning_block`, `orchestrator`, `api`, `sync`.

Then implement the following structure under `/L9/`:

```text
/L9/
  /memory/
    substrate_models.py          # Pydantic models: PacketEnvelope, StructuredReasoningBlock, DB row DTOs
    substrate_repository.py      # DB access layer (Postgres + pgvector)
    substrate_semantic.py        # embedding + vector search helpers (stub embedding call)
    substrate_graph.py           # LangGraph DAG definition (nodes + edges from schema)
    substrate_service.py         # Orchestrating service for write/search
  /api/
    memory_api.py                # FastAPI router for /packet and /semantic/search
  /migrations/
    0001_init_memory_substrate.sql
  /config/
    memory_substrate_settings.py # Pydantic settings for DATABASE_URL, EMBEDDING_MODEL
  /tests/
    test_memory_substrate_basic.py
  /deploy/
    docker-compose.memory_substrate_v1.0.0.yaml
    Dockerfile.memory_api_v1.0.0
    Dockerfile.memory_worker_v1.0.0
  /docs/
    memory_substrate_readme_v1.0.0.md
```

If the schema specifies additional files or different names, **align with the schema first** and adapt the above structure accordingly.

---

## IMPLEMENTATION REQUIREMENTS (BY LAYER)

### 1. Database Layer (Postgres + pgvector)

From `substrate_spec.memory_tables`, generate:

- A single SQL migration:

  - `/L9/migrations/0001_init_memory_substrate.sql`

- Include definitions for ALL tables listed:

  - `agent_memory_events`
  - `semantic_memory`
  - `agent_log`
  - `reasoning_traces`
  - `packet_store`
  - `graph_checkpoints`
  - `buyer_profiles`
  - `supplier_profiles`
  - `transactions`
  - `material_edges`
  - `entity_metadata`

- Ensure:

  - primary keys (UUID)
  - `timestamptz` for timestamps
  - `jsonb` for flexible payloads
  - `vector(1536)` for embedding column in `semantic_memory`
  - relevant indexes:

    - `semantic_memory (agent_id)`
    - `semantic_memory using ivfflat (vector)` if supported
    - `packet_store (packet_type, timestamp)`

### 2. Models Layer

In `/L9/memory/substrate_models.py`:

- Create Pydantic models for:

  - `PacketEnvelope`
  - `StructuredReasoningBlock`
  - DTOs for semantic search requests/responses

- Fields MUST match the schema under:

  - `packet_envelope.fields`
  - `reasoning_block.fields`
  - `inputs` and `outputs`

### 3. Repository Layer

In `/L9/memory/substrate_repository.py`:

- Implement a **thin repository** with functions like:

  ```python
  async def insert_packet(envelope: PacketEnvelope) -> None: ...
  async def insert_reasoning_block(block: StructuredReasoningBlock) -> None: ...
  async def insert_semantic_embedding(...): ...
  async def search_semantic_memory(query_embedding, top_k): ...
  ```

- Use **async Postgres client** (`asyncpg` preferred) or `psycopg2` if you stay sync and wrap in thread executor.

- Encapsulate DSN in config module.

### 4. Semantic Layer

In `/L9/memory/substrate_semantic.py`:

- Provide:

  - `embed_text(text: str) -> list[float]`
  - Semantic search orchestration using `pgvector`

- For now:

  - Implement `embed_text` as a placeholder that raises `NotImplementedError` **or**
  - Accept an embedding provider callable injected at runtime.

- The schema’s `env_vars.EMBEDDING_MODEL` must be honored as configuration.

### 5. LangGraph DAG

In `/L9/memory/substrate_graph.py`:

- Implement the DAG described under `substrate_spec.orchestrator`:

  - Nodes:

    - `intake_node`
    - `reasoning_node`
    - `memory_write_node`
    - `semantic_embed_node`
    - `checkpoint_node`

  - Edges:

    - `intake_node -> reasoning_node`
    - `reasoning_node -> memory_write_node`
    - `reasoning_node -> semantic_embed_node`
    - `memory_write_node -> checkpoint_node`

- Use LangGraph patterns:

  - Typed state (dict-like)
  - Node functions that:

    - transform state
    - call repository methods
    - attach reasoning_block to packet

- The graph should be callable from the API layer:

  - `run_substrate_flow(envelope: PacketEnvelope) -> PacketWriteResult`

### 6. API Layer

In `/L9/api/memory_api.py`:

- Create a FastAPI router with:

  ```http
  POST /packet
  POST /semantic/search
  ```

- Use the request/response models defined in the schema:

  - `PacketEnvelopeIn` → `PacketWriteResult`
  - `SemanticSearchRequest` → `SemanticSearchResult`

- Wire `/packet` to:

  - wrap payload into DAG state
  - call the LangGraph DAG
  - return a minimal summary of what was written (tables, packet_id)

- Wire `/semantic/search` to:

  - call `embed_text`
  - query `semantic_memory`
  - return hits as `{embedding_id, score, payload}`

### 7. Config Layer

In `/L9/config/memory_substrate_settings.py`:

- Implement Pydantic settings for env vars declared in schema `env_vars`:

  - `DATABASE_URL` (required)
  - `EMBEDDING_MODEL` (optional, default `text-embedding-3-large`)

### 8. Deploy Layer

In `/L9/deploy/docker-compose.memory_substrate_v1.0.0.yaml`:

- Define services:

  - `postgres` with `pgvector` extension
  - `memory_api` (FastAPI app)
  - (Optional) `memory_worker` if you split DAG execution

- Use:

  - volumes for Postgres data
  - healthchecks for Postgres + API

- Build images from:

  - `Dockerfile.memory_api_v1.0.0`
  - `Dockerfile.memory_worker_v1.0.0`

### 9. Tests & Docs

- `/L9/tests/test_memory_substrate_basic.py`:

  - minimal tests:

    - packet model validation
    - basic semantic search stub (using fake embeddings)

- `/L9/docs/memory_substrate_readme_v1.0.0.md`:

  - How to:

    - run migrations
    - start docker-compose
    - hit `/packet`
    - hit `/semantic/search`

---

## EXECUTION ORDER (INSIDE CURSOR)

1. **Parse Schema**

   - Fully read `/L9/schemas/plasticos_memory_substrate_module_schema_v1.0.0.yaml`.
   - Extract:

     - table definitions
     - models
     - endpoints
     - DAG structure
     - env vars

2. **Generate Plan**

   - Outline which files you will create or update.
   - Confirm:

     - DB schema
     - models
     - LangGraph DAG
     - FastAPI API
     - config
     - deploy
     - tests
     - docs

3. **Implement**

   - Create the files listed above.
   - Ensure imports between modules resolve cleanly.

4. **Validate**

   - Run:

     - `python -m compileall .` (or Cursor’s built-in checks)

   - Optionally:

     - `pytest` for the new tests

   - Check there are no obvious circular imports.

---

## HARD RULES

- Do NOT modify unrelated L9 modules.
- Do NOT introduce new external services.
- Do NOT ignore or change table names, model fields, or endpoints defined in the schema.
- Prefer explicit, boring, debuggable code over clever abstractions.
- If a detail is ambiguous, choose the **simplest correct implementation** and document it in the README.

END OF PROMPT. FOLLOW THE SCHEMA. BUILD THE SUBSTRATE.
