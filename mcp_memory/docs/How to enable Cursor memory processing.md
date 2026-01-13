<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# How to enable the memory processing and refining and embedding I have in L9 for C

You already have all the machinery; enabling “for C” is mostly wiring Cursor to call the MCP memory server you built, which in turn writes into L’s packetstore + memoryembeddings and runs embeddings + refinement on every write/search.[^1][^2][^3]

## 1. Make sure MCP memory server is live

- Confirm the L9 MCP Memory Server is running and reachable via HTTPS (Caddy + Cloudflare fronting port 9001).[^1]
- Health checks:
    - `curl https://l9.quantumaipartners.com/health`
    - `curl -H "Authorization: Bearer YOUR_MCP_API_KEY" https://l9.quantumaipartners.com/mcptools` should list tools including memory operations.[^1]

This server already:

- Connects to Postgres with pgvector.[^1]
- Calls OpenAI to generate embeddings on each `saveMemory` / `searchMemory`.[^1]
- Logs to `memory.auditlog` and enforces scope filters when you migrate to unified packetstore.[^2][^1]


## 2. Wire Cursor to MCP so C uses the pipeline

In Cursor, add your memory MCP server so every “memory” call goes through that API instead of Cursor’s built‑in memory:

- In `.cursor/mcp.json` (or the UI equivalent), configure:

```json
{
  "mcpServers": {
    "l9-memory": {
      "command": "node",
      "args": ["path/to/mcp-http-bridge.js"],
      "env": {
        "MCPSERVERURL": "https://l9.quantumaipartners.com",
        "MCPAPIKEY": "YOUR_MCP_API_KEY"
      }
    }
  }
}
```

or simpler, as documented:

```json
{
  "mcpServers": {
    "l9-memory": {
      "command": "curl",
      "args": [
        "-X", "GET",
        "https://l9.quantumaipartners.com/mcptools",
        "-H", "Authorization: Bearer YOUR_MCP_API_KEY"
      ]
    }
  }
}
```

Once this is in place, Cursor will:

- Discover tools via `/mcptools`.[^1]
- Invoke them via `POST /mcp/call` with `toolName`, `arguments`, and `userid`.[^1]
- Those calls hit `routes/memory.py`, which runs your embedding + search pipeline.


## 3. Ensure memory processing + embeddings are actually L9-style

On the MCP side, you already have:

- **Embeddings**: `embeddings.py` uses `AsyncOpenAI` and `settings.OPENAI_EMBED_MODEL` to generate vectors for `saveMemory` and search queries.[^1]
- **Semantic search**: `searchMemory` computes a query embedding, runs vector similarity against stored embeddings, and returns ranked results with similarity scores and timings.[^1]
- **Audit + cleanup**: background cleanup deletes expired short/medium memories; audit rows are written on save/search.[^1]

To align this fully with the unified substrate:

- Follow `memory-setup-instructions.md` and `ARCHITECTURE.md` to migrate from `memory.shortterm/mediumterm/longterm` into `packetstore` + `memoryembeddings` with `projectid` + `scope`.[^3][^2]
- Update MCP handlers to:
    - Insert into `packetstore` with `scope='developer'` (or `global`) and `projectid='l9'` for C’s repo.[^2][^3]
    - Store vectors in `memoryembeddings` keyed by `packetid`.[^2]
    - Enforce `WHERE scope IN ('developer','global')` on all C reads.[^3][^2]

That gives C the same processing/refinement/embedding stack L uses, just through MCP.

## 4. Turn on “always-process” behavior for C’s writes

In practice, “enable processing and refining” for C means:

- **C always uses `saveMemory`** for anything you want refined \& embedded:
    - Content, kind (`preference`, `fact`, `error`, etc.), scope (`developer` / `global`), `projectid`, tags, importance.[^2][^1]
- On each call, the MCP:
    - Runs embedding via OpenAI.
    - Persists to Postgres.
    - Logs to audit.
    - Makes it available to L’s SubstrateService and any downstream DAGs you’ve wired.[^4][^1]

If you’ve already built more advanced memory DAG processing (e.g., reflection, fact extraction) on top of packetstore, you enable it for C simply by:

- Having those DAGs trigger off the same packet writes (no special path for C).
- Keeping the scopes invariant: C writes only `developer/global`, L can process across all scopes.[^4][^3][^2]


## 5. Optional: plug C into the “Intelition” refiners

If you want C’s memories to also benefit from Intelition‑style consolidation and reflection:

- Ensure IntelitionRuntime or your nested memory manager operates on the unified substrate tables (`packetstore`, `memoryembeddings`, knowledgefacts, reflectionstore) without caring who wrote the packets.[^4][^2]
- Since C and L share the substrate, any background consolidation, pattern extraction, or reflection applied there automatically refines C’s memories too. No extra work is needed on the Cursor side—only that C always writes via MCP.

If you tell what’s already implemented from the Intelition roadmap (nested tiers, reflection, knowledgefacts, etc.), a next step can be a concrete TODO list for the MCP handlers so C’s writes hit every stage of that pipeline.
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: L9-MCP-IMPL.md

[^2]: memory-setup-instructions.md

[^3]: ARCHITECTURE.md

[^4]: L9-Intelition-Framework-Always-Active.md

[^5]: agent_catalog.txt

[^6]: api_surfaces.txt

[^7]: architecture.txt

[^8]: async_function_map.txt

[^9]: bootstrap_phases.txt

[^10]: class_definitions.txt

[^11]: config_files.txt

[^12]: decorator_catalog.txt

[^13]: dependencies.txt

[^14]: deployment_manifest.txt

[^15]: dynamic_tool_catalog.txt

[^16]: entrypoints.txt

[^17]: env_refs.txt

[^18]: event_types.txt

[^19]: feature_flags.txt

[^20]: file_metrics.txt

[^21]: function_signatures.txt

[^22]: governance_model.txt

[^23]: imports.txt

[^24]: inheritance_graph.txt

[^25]: agent_labs_research_prompt.md

[^26]: Example-L9_Tensor-AIOS_Layer_Schemas_v6.md

