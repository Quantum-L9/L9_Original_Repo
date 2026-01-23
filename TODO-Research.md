# TODO-Research.md — Knowledge Gap Bridge

> **Purpose:** Track research needed to bridge AI training cutoff gaps
> **Method:** Use Perplexity tools (`search`, `reason`, `deep_research`) to get current info
> **Updated:** 2026-01-20T16:05:00Z

---

## 🔴 HIGH PRIORITY — L9 Core Stack

### LangGraph (v0.3+)
- [ ] Current checkpoint/persistence patterns with PostgreSQL
- [ ] State management changes in 0.3+
- [ ] Multi-agent coordination patterns
- [ ] Memory integration best practices
- **Query:** `"LangGraph 0.3 checkpoint persistence PostgreSQL 2026 best practices"`

### Pydantic v2
- [ ] New validation patterns (`Annotated`, `model_validator`)
- [ ] Migration patterns from v1
- [ ] Performance optimization
- **Query:** `"Pydantic v2 Annotated validation patterns 2026"`

### FastAPI
- [ ] Latest async patterns
- [ ] Lifespan context managers
- [ ] Dependency injection updates
- **Query:** `"FastAPI lifespan async patterns 2026"`

### pgvector
- [ ] HNSW vs IVFFlat performance benchmarks
- [ ] Optimal indexing strategies for 1536-dim embeddings
- [ ] Hybrid search patterns (vector + full-text)
- **Query:** `"pgvector HNSW indexing 1536 dimensions performance 2026"`

### OpenAI API
- [ ] text-embedding-3-large best practices
- [ ] Dimension truncation strategies
- [ ] Batch sizing optimization
- [ ] Structured outputs (JSON mode)
- **Query:** `"OpenAI text-embedding-3-large dimension truncation best practices"`

### Neo4j
- [ ] Graph RAG patterns 2025-2026
- [ ] Cypher query optimization
- [ ] Vector index integration
- **Query:** `"Neo4j Graph RAG patterns 2026"`

---

## 🟡 MEDIUM PRIORITY — Agent Architecture

### Frontier Agent Patterns
- [ ] ReAct vs LATS vs Tree of Thoughts — current state
- [ ] Multi-agent orchestration frameworks
- [ ] Tool use optimization patterns
- **Query:** `"frontier AI agent architectures 2026 ReAct LATS comparison"`

### MCP Protocol (Model Context Protocol)
- [ ] Full specification deep dive
- [ ] Edge cases and error handling
- [ ] Server implementation patterns
- **Query:** `"Anthropic MCP Model Context Protocol server implementation 2026"`

### Memory Systems
- [ ] Is L9's 4-tier memory (identity/semantic/episodic/working) still frontier?
- [ ] Hierarchical summarization approaches
- [ ] Salience decay models
- **Query:** `"frontier AI memory architectures 2026 hierarchical summarization"`

---

## 🟢 LOWER PRIORITY — Infrastructure

### Docker/Deployment
- [ ] Multi-container orchestration patterns
- [ ] Health check best practices
- [ ] Zero-downtime deployment

### Observability
- [ ] OpenTelemetry for AI agents
- [ ] Prometheus metrics for LLM apps
- [ ] Tracing distributed agent calls

---

## 📋 Research Execution Template

```bash
# Quick lookup
python3 -c "from perplexity_search import search; print(search('query here'))"

# Or use Cursor's Perplexity tools:
# - search: Quick facts
# - reason: Complex analysis  
# - deep_research: Comprehensive reports
```

---

## ✅ Completed Research

| Date | Topic | Tool Used | Result Location |
|------|-------|-----------|-----------------|
| | | | |

---

## Notes

- **Training cutoff:** My knowledge frozen ~early 2024
- **Perplexity bypass:** Real-time web search with citations
- **Priority:** Focus on L9 core stack first (LangGraph, pgvector, embeddings)
