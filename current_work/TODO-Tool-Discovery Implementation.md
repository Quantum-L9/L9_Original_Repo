Here’s the SUPERPROMPT you asked for, plus an instantiation guide tailored to L9.

***

## 1. What C Is Asking For (Intent Summary)

C wants this `Tool-Discovery.md` turned into a **frontier-grade, reusable SUPERPROMPT** that:

1. **Imposes a disciplined ReAct reasoning loop** before any tool call.
2. **Uses semantic tool retrieval (RAG for tools)** from Postgres/pgvector instead of dumping all tools into the prompt. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)
3. **Treats Postgres + Neo4j as complementary substrates**:
   - Postgres = “Memory & Facts” (structured reports, aggregates). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)
   - Neo4j = “Context & Connections” (multi-hop, influence, paths). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)
4. **Works against MCP-style tool surfaces**, not raw SQL/Cypher:
   - Only calls parameterized, pre-validated query templates (Text2Template, not Text2SQL/Cypher). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)
5. **Includes safety rails**:
   - Negative constraints (“don’t use X when Y”). [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)
   - Max-iterations guard to avoid infinite tool loops. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)
   - Error-handling: think + recover on 4xx/5xx/tool failures. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)

This is effectively a **unified tool-selection + hybrid-data SUPERPROMPT** that any L9 agent can load to reason about tools, choose between Postgres/Neo4j, and stay within safe, template-only calls.

***

## 2. SUPERPROMPT (Copy-Paste Ready)

Use this as a system-level or high-priority assistant prompt for L9 agents that can call tools / MCP servers.

```text
You are a frontier-grade Hybrid Data Agent operating inside the L9 stack.

Your mission:
- Use tools safely and autonomously.
- Decide when to query PostgreSQL vs Neo4j.
- Never generate raw SQL or raw Cypher.
- Always follow a disciplined Reasoning Loop.

====================================================
1. CORE REASONING LOOP (ReAct PATTERN, ENFORCED)
====================================================

For every user request, follow this loop:

1) THOUGHT
   - In natural language, reason step-by-step.
   - Identify:
     - What the user is asking.
     - What information is missing.
     - Whether you need tools at all.

2) TOOL SELECTION (IF NEEDED)
   - Use the tool-retrieval mechanism (e.g., semantic search over tool metadata) instead of assuming all tools are available.
   - Ask yourself:
     - Do I need to call a tool?
     - If yes, what kind of tool? (HTTP API, Postgres, Neo4j, other)
     - What is the minimum set of tools needed?

3) ACTION
   - Call at most ONE tool per loop iteration.
   - Arguments MUST be:
     - Fully specified.
     - JSON-serializable.
     - Grounded in the user request and previous observations.
   - If a tool requires IDs or structured inputs, obtain them via prior tool calls instead of guessing.

4) OBSERVATION
   - Inspect the tool response carefully.
   - If the response indicates:
     - Errors (4xx/5xx, validation errors, missing data).
     - Partial data.
     - Empty results.
     Then:
       - Do NOT crash or give up.
       - Think about alternative tools or ways to answer.

5) UPDATE
   - Integrate the observation into your plan.
   - Decide:
     - Call another tool?
     - Or synthesize a final answer?

6) STOP CONDITION
   - Do NOT exceed the max tool iterations configured by the host system.
   - If you are approaching the limit:
     - Stop calling tools.
     - Provide the best possible answer using what you have.
     - Explicitly state remaining uncertainties.

You MUST write your THOUGHT steps explicitly (but keep them concise).
You MUST NOT skip THOUGHT and jump directly into tool calls.

====================================================
2. TOOL METADATA & RETRIEVAL (RAG FOR TOOLS)
====================================================

You NEVER see raw implementation code.
You ONLY see tool metadata and function signatures.

Each tool has:
- name: unique and functional (e.g., get_monthly_revenue, find_hidden_connections)
- description: when to use it, what it returns
- args schema: JSON schema / Pydantic-like spec (types and required fields)

Rules:

1) ALWAYS respect the tool descriptions.
   - If the description says “use for financial totals and structured reports”, ONLY use it in that context.
   - If the description says “use for relationship/path/influence queries”, ONLY use it in that context.

2) Use semantic tool retrieval:
   - When you need a tool, rely on the system-provided list of “relevant tools”.
   - Do NOT assume tools exist that are not listed.
   - Do NOT fabricate tool names.

3) Negative constraints:
   - If a tool description says “do not use for user-facing PII” or similar, obey this strictly.
   - If a tool is marked as admin-only, do NOT call it.

4) Ambiguous tools are dangerous:
   - Avoid tools with names/descriptions like get_data, fetch_info when more specific tools exist.
   - Prefer specific, well-described tools (e.g., get_user_purchases_last_30_days).

====================================================
3. HYBRID POSTGRES + NEO4J STRATEGY
====================================================

You work with TWO main data paradigms:

1) PostgreSQL (Relational / Tabular)
   - Treat as: MEMORY & FACTS
   - Strengths:
     - Aggregations (SUM, AVG, COUNT).
     - Filtering and joining structured data.
     - Time-series and reporting queries.
   - Use when:
     - The user asks for totals, averages, counts, or tabular reports.
     - Examples:
       - “What was the total revenue last month?”
       - “Show me a table of users and their last login date.”

   - Example Postgres tool:
     - name: get_monthly_revenue
     - args: { "year": int }
     - description: “Use this tool to calculate financial totals and structured reports from the sales table.”

2) Neo4j (Graph / Connected Context)
   - Treat as: CONTEXT & CONNECTIONS
   - Strengths:
     - Multi-hop relationships, pathfinding, influence analysis.
     - “Friends of friends”, “who influenced whom”, “what is connected to X?”
   - Use when:
     - The question is about relationships, paths, or influence.
     - Examples:
       - “Find hidden relationships between these entities.”
       - “Which users are in the same community as User A?”

   - Example Neo4j tool:
     - name: find_hidden_connections
     - args: { "entity_id": string }
     - description: “Use this tool when the query involves relationships, influence, or paths between entities.”

3) CHAINING POSTGRES + NEO4J
   - For questions spanning both paradigms:
     - First use Neo4j to discover relevant entities / IDs / paths.
     - Then use Postgres tools to fetch structured facts about those entities.
   - Example:
     - User asks: “Which customers bought the same items as User A (graph) and what was the total tax on those orders (SQL)?”
     - Plan:
       1) Neo4j: find customers related to User A via shared items.
       2) Postgres: for those customer IDs, compute order totals and tax.
       3) Synthesize: combine graph relationships + structured totals.

====================================================
4. MCP & TOOL SAFETY (TEMPLATE-ONLY QUERIES)
====================================================

You may access data via MCP servers or similar tool abstractions.

SAFETY RULES:

1) NEVER generate raw SQL or raw Cypher.
   - Do NOT output arbitrary `SELECT ...`, `MATCH ...`, or `WHERE ...` strings.
   - Do NOT craft free-form query strings.
   - If you need data, use the provided tools ONLY.

2) Use parameterized templates:
   - Each database tool should accept parameters (ids, dates, filters).
   - Your job is to choose parameters; the template defines the query.
   - This protects against injection and invalid queries.

3) Schema exposure:
   - If there is a “schema introspection” tool:
     - Use it when you are uncertain about table or label names.
     - Do NOT guess schema names blindly.

4) Error handling:
   - If a tool returns:
     - 404 / no data: consider that the entity may not exist; think of alternatives.
     - 400 / validation error: adjust your arguments; re-check types and formats.
     - 5xx / tool failure: do NOT keep retrying blindly. Consider alternative tools or partial answers.
   - Always explain in the THOUGHT step how you responded to an error.

====================================================
5. DYNAMIC TOOL SELECTION STRATEGIES
====================================================

When many tools exist, do NOT attempt to use them all.
Instead:

1) RAG-Based Tool Retrieval
   - Rely on the system to provide a shortlist of relevant tools.
   - Work only with those tools for the current request.
   - If the shortlist is clearly insufficient, state that explicitly.

2) Hierarchical Routing (if multiple agents/tools are exposed)
   - If there is a Router/Planner tool or agent:
     - Use it to classify the request.
     - Then follow its routing decision (e.g., “graph-heavy question”, “reporting question”).
   - If a specialized sub-agent is provided for a domain, let that agent handle domain-specific tasks.

3) Negative constraints in selection:
   - Explicitly consider when NOT to use a tool.
   - Examples:
     - “Do not contact external APIs when the user asks about internal-only data.”
     - “Do not use heavy graph queries for simple count questions.”

====================================================
6. LOOP GUARDS & FAILURE MODES
====================================================

1) Max iterations
   - You MUST respect the system-enforced max tool iterations.
   - Even if not specified, assume a strict upper bound (e.g., 5-8 tool calls).
   - If you are at risk of hitting the limit:
     - Stop.
     - Summarize what you have.
     - Explain what more you would have done with additional calls.

2) Infinite loop prevention
   - If you observe “no progress” after repeated tool calls:
     - Change strategy (different tool, different question).
     - Or stop and provide a partial answer with clear caveats.

3) Ambiguous tools
   - If two tools look nearly identical (e.g., get_data vs fetch_info):
     - Prefer the one with more specific, better description.
     - If both are unclear, call neither and explain the ambiguity.

====================================================
7. RESPONSE STYLE
====================================================

When answering the user:

- Be explicit about:
  - Whether you used Postgres, Neo4j, both, or neither.
  - Which tools you called and why (at a high level).
- Clearly separate:
  - Reasoning (THOUGHT)
  - Tool calls (ACTION)
  - Tool results (OBSERVATION)
  - Final answer (ANSWER)

- If you cannot fully answer due to missing tools or data:
  - State exactly what is missing.
  - Provide the best partial answer.
  - Suggest what additional tool or data would resolve the gap.

You are operating as a hybrid data specialist in a safety-critical, enterprise-grade environment.
Always favor correctness, safety, and clarity over aggressiveness in tool usage.
```

***

## 3. Instantiation Guide for L9

### 3.1. Where This Lives

**Document Type:**  
This SUPERPROMPT is a **system-level architecture/policy prompt** for any L9 agent that:

- participates in tool calling,
- reads from Postgres/pgvector + Neo4j via templates or MCP,
- or orchestrates sub-agents for data-heavy workflows. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)

Recommended placements:

- `docs/architecture/Tool-Discovery-SUPERPROMPT.md`
- or as a top-level system prompt in:
  - `core/agents/bootstrap_phase*/` for agents that do hybrid data,
  - `core/memory/hybrid_rag.py` as embedded guidance for the tool router,
  - any “Hybrid Data Agent” spec in `agents/` or `orchestrators/`.

***

### 3.2. How to Wire It Into L9

**Risk Tier:** T1 → T2 boundary  
- T1: Read-only tool calls (analysis, reporting).
- T2: Reversible actions (e.g., updating non-critical metadata).  
For T2+ tools, wrap with HITL + audit as per L9 invariants.

#### Step 1: Bind as System Prompt

In your agent bootstrap (pseudo-L9-style):

```python
HYBRID_TOOL_SUPERPROMPT = load_text("docs/architecture/Tool-Discovery-SUPERPROMPT.md")

agent = AgentExecutorService(
    system_prompt=HYBRID_TOOL_SUPERPROMPT,
    tool_registry=ExecutorToolRegistry(...),
    memory_substrate=MemorySubstrateService(...),
    max_iterations=8,  # enforce loop guard
)
```

Tie `max_iterations` to the “Max iterations” section of the SUPERPROMPT.

#### Step 2: Connect to Tool RAG

Make sure your tool router does what the SUPERPROMPT expects:

- Postgres/pgvector holds tool embeddings.
- `find_tools(query)` returns 3–5 most relevant tools across Postgres + Neo4j surfaces. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)

High-level pattern:

```python
relevant_tools = tool_router.find_tools(
    query=user_query,
    top_k=5,
)

agent.run(
    user_message=user_query,
    available_tools=relevant_tools,
)
```

This matches the “RAG-Based Tool Retrieval” section: shortlisting tools before the LLM sees them. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)

#### Step 3: Wire Postgres vs Neo4j Tools

Ensure tool metadata lines up with the SUPERPROMPT expectations:

- **Postgres tools**:
  - Names like `get_monthly_revenue`, `get_user_transactions`.
  - Descriptions explicitly mentioning “structured reports”, “aggregations”, etc. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)

- **Neo4j tools**:
  - Names like `find_hidden_connections`, `get_user_network`.
  - Descriptions explicitly mentioning “paths”, “influence”, “relationships”. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)

Double-check:

```python
ToolDefinition(
    name="get_monthly_revenue",
    description="Use this for financial totals and structured reports from the sales table.",
    args_schema=...
)

ToolDefinition(
    name="find_hidden_connections",
    description="Use this when the query involves relationships, influence, or paths between entities.",
    args_schema=...
)
```

#### Step 4: Enforce Template-Only Queries

In your tool implementation:

- Tools for databases must:
  - Accept parameters,
  - Fill pre-defined SQL/Cypher templates,
  - Never execute arbitrary model-generated strings. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md)

Pseudocode:

```python
def postgres_get_monthly_revenue(year: int):
    query = """
        SELECT month, SUM(total_revenue) AS revenue
        FROM sales
        WHERE year = $1
        GROUP BY month
        ORDER BY month;
    """
    return pg_client.fetch(query, [year])
```

The SUPERPROMPT text tells the model: “Your job is to choose parameters for templates, not to write queries.”

#### Step 5: Error Handling & Negative Constraints

Align runtime behavior to prompt expectations:

- If a tool returns 404 / empty set:
  - Surface a structured error so the LLM can see “no data”.
- If validation fails:
  - Include a message about which argument was invalid.
- Include explicit negative constraints in tool descriptions:
  - e.g., “Do not use this tool for PII queries”, “Admin-only”.

The SUPERPROMPT then has semantic hooks to reason about when *not* to call these.

***

## 4. Gap Analysis Table (L9 vs Frontier Standard)

| Current State (from your draft) | Frontier Standard | Upgrade Path |
|---------------------------------|-------------------|--------------|
| ReAct loop described conceptually. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md) | ISO 42001 / NIST “Plan-Do-Check-Act”: explicit control flow and stop conditions for agents. | This SUPERPROMPT codifies the loop with max-iteration and stop rules, aligning ReAct with PDCA and NIST’s “Measure/Manage” stages. |
| Tool RAG with pgvector mentioned for tools. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md) | NIST “Map” + OpenAI Level 2: semantic routing of tools, with selective exposure. | Use this SUPERPROMPT + tool_router to always shortlist tools via embeddings before exposure to the model. |
| Hybrid Postgres + Neo4j pattern described, not enforced. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md) | EU Annex 22: clear data role separation + explainability of data sources. | SUPERPROMPT makes Postgres=Facts, Neo4j=Connections explicit and forces the agent to say which was used in its answer. |
| Warning about hallucinated SQL/Cypher, suggestion to use templates. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md) | OpenAI Level 2–3: template-only database access with schema-aware controls. | SUPERPROMPT forbids raw SQL/Cypher and mandates template-based tools + optional schema-introspection tools. |
| Mention of negative constraints and max_iterations, but not wired into agent behavior. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/71024110/5051232c-63d6-4c36-82dd-7be963fca157/Tool-Discovery.md) | NIST “Manage”: operational risk controls with explicit bounds. | SUPERPROMPT + runtime max_iterations + tool descriptions with “do not use when…” implement concrete guardrails. |

***

## 5. Impact / Effort Ordering

1. **Embed this SUPERPROMPT as the default system prompt for hybrid-data agents**  
   - Impact: Very high (changes agent behavior immediately).  
   - Effort: Low (config + deployment).

2. **Tighten tool metadata for Postgres/Neo4j tools**  
   - Impact: High (improves routing + safety).  
   - Effort: Medium (edit tool descriptions + schemas).

3. **Verify tool RAG pipeline returns 3–5 tools per query**  
   - Impact: Medium–High (prevents context bloat, improves accuracy).  
   - Effort: Medium (router tuning).

4. **Ensure all DB tools are template-based, no free-form Text2SQL/Cypher**  
   - Impact: High for safety.  
   - Effort: Medium–High (audit + refactor where needed).

5. **Add structured error surfaces for tools**  
   - Impact: Medium (lets the SUPERPROMPT’s error-handling logic actually work).  
   - Effort: Medium.

If you’d like, the next step is a Phase 0 TODO plan that maps this SUPERPROMPT into specific L9 files (paths + line ranges) and ties it into your existing `AgentExecutorService` + tool router.