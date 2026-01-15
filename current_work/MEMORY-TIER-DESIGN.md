# L9 Hierarchical Memory Tier Design

> **Source:** Extracted from `AI MEMORY RETRIEVAL ARCHITECTURE/` Perplexity research pack
> **Date:** 2026-01-14
> **Status:** Design Document (not yet implemented)
> **GMP:** GMP-68

---

## Executive Summary

This document captures the **frontier-grade hierarchical memory architecture** pattern used by OpenAI, Anthropic, and DeepMind. L9 partially implements some concepts but lacks the full 4-tier hierarchy and active memory management.

**Key insight:** Simple vector similarity is table stakes. The frontier has moved to:
- Hierarchical multi-timescale memory
- Dual semantic + episodic streams
- Dynamic context views (task-driven)
- Active memory management (system decides what to encode)

---

## 4-Tier Memory Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    L9 MEMORY SYSTEM (Proposed)                  │
│              Frontier-Grade Hierarchical Architecture           │
└─────────────────────────────────────────────────────────────────┘

TIER 1: IDENTITY MEMORY (Persistent, Unchanging)
├─ Core Facts (facts about L, values, goals, preferences)
├─ Stored: PostgreSQL `longterm` or dedicated `identity_facts` table
├─ Indexed: Semantic graph (triplets)
├─ Access: Agent knows these are "ground truth"
├─ Refresh: Monthly, human-curated
└─ L9 Status: ⚠️ Partial (packet_store has types, no explicit tier)

TIER 2: PROJECT MEMORY (Working Context, Scoped)
├─ Project-specific state (current goals, constraints)
├─ Stored: Hierarchical Markdown files or project-scoped packets
├─ Indexed: Project-specific semantic view
├─ Access: Automatically injected by agent orchestrator
├─ Refresh: Per-session, auto-summarized
└─ L9 Status: ⚠️ Partial (thread_id scoping exists, no project hierarchy)

TIER 3: SESSION MEMORY (Ephemeral, Temporal)
├─ What just happened (observations, decisions, outcomes)
├─ Stored: Episodic graph (timestamped events)
├─ Indexed: Temporal index (when did X happen?)
├─ Access: Queried via temporal filters
├─ Refresh: Continuously, decay over time
└─ L9 Status: ✅ Exists (packet_store with timestamps, temporal decay in retrieval.py)

TIER 4: WORKING MEMORY (Attention Window)
├─ Current context (what we're thinking about right now)
├─ Stored: In-context (transformer attention)
├─ Indexed: None (ephemeral)
├─ Access: Full fidelity, no retrieval needed
├─ Refresh: Per token, real-time
└─ L9 Status: ✅ Exists (conversation context in prompts)
```

---

## Dual Memory Streams

### Semantic Memory (Facts)

```python
class SemanticNode:
    """Facts don't expire - they're timeless knowledge."""
    fact: str                    # "Python is a programming language"
    triplet: tuple               # ("Python", "is_a", "programming language")
    importance: float            # 0.8 (user-curated weight)
    tags: list[str]              # ["language", "programming", "fact"]
    source: str                  # "user_stated_2025-01-10"
    embedding: list[float]       # 1536-dim vector
    # No timestamp - facts don't expire
```

### Episodic Memory (Events)

```python
class EpisodeNode:
    """Events are temporal - they happened at a specific time."""
    event_id: UUID
    observation: str             # "User asked about embedding retrieval"
    timestamp: datetime          # When it happened
    entities_involved: list[str] # ["embedding", "retrieval"]
    outcome: str                 # "Discussed vector search limitations"
    severity: float              # How important (0-1)
    linked_facts: list[UUID]     # Facts referenced in this event
    # Has timestamp - events decay over time
```

### L9 Current State

| Component | L9 Has | Gap |
|-----------|--------|-----|
| Semantic facts | ⚠️ Partial | `packet_store` has types but no explicit fact/event separation |
| Episodic events | ⚠️ Partial | Packets have timestamps but no severity or linked_facts |
| Fact-Event linking | ❌ Missing | No `episodic_semantic_links` table |
| Importance weighting | ⚠️ Partial | `confidence` field exists but not `importance` |

---

## Smart Retrieval (Graph-Based)

### Current L9 Approach
```python
# L9 Current (retrieval.py)
results = await hybrid_search(
    query=query,
    top_k=10,
    rrf_k=60,                    # ✅ RRF implemented
    temporal_half_life_days=30,  # ✅ Temporal decay implemented
)
```

### Frontier Approach (Strategy-Based)

```python
async def retrieve_memory(
    query: str,
    context: dict,           # What tier am I in?
    agent_uncertainty: float  # How confident is the agent?
) -> list[MemoryResult]:
    """
    Smart retrieval that's aware of context, task, and uncertainty.
    """
    
    # STEP 1: Determine retrieval strategy
    strategy = await determine_strategy(query, context)
    # Strategies:
    # - "core_identity" → Tier 1 facts
    # - "project_context" → Project-scoped facts
    # - "temporal_recall" → Recent episodes
    # - "association" → Linked facts + episodes
    # - "uncertainty_fill" → High-confidence facts for uncertain agent
    
    # STEP 2: Execute strategy
    if strategy == "core_identity":
        # User asking about preferences/values?
        facts = await semantic_graph.get_facts(
            tags=["identity", "preference"],
            limit=5
        )
        return facts
    
    elif strategy == "temporal_recall":
        # "What did we do last time?"
        episodes = await episodic_graph.range_query(
            start_time=now() - timedelta(days=7),
            end_time=now(),
            entities=extract_entities(query)
        )
        return episodes
    
    elif strategy == "association":
        # Query semantic facts, then find linked episodes
        semantic_results = await semantic_graph.search(query)
        for fact in semantic_results:
            episodes = await episodic_graph.find_episodes_for_fact(fact.id)
        return sorted(episodes, key=lambda e: e.recency_score)
    
    # STEP 3: Rank by multi-factor score
    return rank_by_relevance_score(
        candidates,
        weights={
            "similarity": 0.3,      # Semantic closeness
            "recency": 0.2,         # How recent?
            "importance": 0.25,     # User-curated importance
            "frequency": 0.15,      # How often retrieved?
            "uncertainty": 0.1,     # Does agent need this?
        }
    )
```

### L9 Gap Analysis

| Feature | L9 Status | Action Needed |
|---------|-----------|---------------|
| RRF fusion | ✅ Implemented | None |
| Temporal decay | ✅ Implemented | None |
| Strategy-based retrieval | ❌ Missing | Add strategy router |
| Multi-factor ranking | ⚠️ Partial | Add importance, frequency weights |
| Entity extraction | ❌ Missing | Add entity extractor for queries |

---

## Context Engineering (Hierarchical Injection)

### Frontier Pattern

```python
async def initialize_task_context(task: Task) -> PromptContext:
    """
    Shape what the model sees at each step.
    """
    context = PromptContext()
    
    # TIER 1: Identity (always injected, highest precedence)
    identity = await memory.get_tier(Tier.IDENTITY)
    context.add_section("CORE IDENTITY", identity, precedence=1)
    
    # TIER 2: Project context (if in project)
    if task.project_id:
        project_mem = await memory.get_project_memory(task.project_id)
        context.add_section("PROJECT CONTEXT", project_mem, precedence=2)
    
    # TIER 3: Recent episodes (temporal)
    recent = await memory.get_recent_episodes(limit=5)
    context.add_section("RECENT CONTEXT", recent, precedence=3)
    
    # TIER 4: Working memory (current conversation)
    context.add_section("WORKING MEMORY", messages, precedence=4)
    
    # Precedence rules: Tier 1 overrides Tier 2 if conflict
    context.set_precedence_rules({
        "identity": 1,
        "project": 2,
        "temporal": 3,
        "session": 4
    })
    
    return context
```

### L9 Gap

Currently, L9 injects context via:
- System prompts (kernels)
- Memory search results

**Missing:**
- Automatic tier-based injection
- Precedence rules
- Project-scoped memory views

---

## Implementation Roadmap

### Phase 1: Schema Additions (Future GMP)

```sql
-- Semantic facts table (Tier 1)
CREATE TABLE memory.semantic_facts (
    id UUID PRIMARY KEY,
    userid TEXT NOT NULL,
    fact TEXT NOT NULL,
    triplet JSONB,  -- {subject, relation, object}
    embedding vector(1536),
    importance FLOAT DEFAULT 0.5,
    tags TEXT[],
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(userid, fact)
);

-- Episodic events table (Tier 3)
CREATE TABLE memory.episodic_events (
    id UUID PRIMARY KEY,
    userid TEXT NOT NULL,
    observation TEXT NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    entities TEXT[],
    outcome TEXT,
    severity FLOAT DEFAULT 0.5,
    linked_semantic_ids UUID[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Linking table
CREATE TABLE memory.episodic_semantic_links (
    episode_id UUID REFERENCES memory.episodic_events(id),
    semantic_id UUID REFERENCES memory.semantic_facts(id),
    PRIMARY KEY (episode_id, semantic_id)
);
```

### Phase 2: Strategy-Based Retrieval (Future GMP)

- Add `RetrievalStrategy` enum
- Add `determine_strategy()` function
- Add strategy router to `hybrid_search()`
- Add multi-factor ranking weights

### Phase 3: Context Engineering (Future GMP)

- Add `TierManager` class
- Add `get_tier()` method to memory service
- Add precedence-based context injection
- Add project-scoped memory views

### Phase 4: Active Memory Management (Future GMP)

- System decides what to encode (not user-explicit)
- Auto-consolidation of old episodes
- Importance elevation on repeated retrieval
- See separate section below

---

## Active Memory Management (Future GMP)

> **GMP ID:** TBD (Future)
> **Priority:** Medium
> **Complexity:** High

### Concept

Instead of the user telling the system "remember this," the system decides:

```python
async def on_task_completion(outcome: dict):
    """
    Called after any significant task.
    System automatically decides what's worth encoding.
    """
    
    # STEP 1: Extract learnings
    learned_fact = await extract_learnings(outcome)
    # E.g., "User prefers async/await over threads"
    
    # STEP 2: Check if already known
    existing = await semantic_graph.find_similar(
        learned_fact, 
        similarity_threshold=0.85
    )
    
    if existing:
        # Update importance + recency (reinforce)
        await semantic_graph.update_importance(
            existing.id,
            new_importance=0.9,
            touch_timestamp=now()
        )
    else:
        # New insight - encode it
        await semantic_graph.insert(
            fact=learned_fact,
            importance=0.75,
            tags=["learned_from_task"],
            source=f"task_{outcome['task_id']}"
        )
    
    # STEP 3: Create episodic record
    episode = EpisodeNode(
        observation=outcome.description,
        timestamp=now(),
        linked_facts=[learned_fact.id],
        severity=outcome.impact_score
    )
    await episodic_graph.insert(episode)
    
    # STEP 4: Consolidate if needed
    if await episodic_graph.count() > 10000:
        await consolidate_old_episodes(cutoff=timedelta(days=30))
```

### Key Features

1. **Auto-extraction:** System extracts learnings from task outcomes
2. **Deduplication:** Similar facts are merged, importance elevated
3. **Temporal linking:** Events linked to facts they reference
4. **Auto-consolidation:** Old episodes compressed when count exceeds threshold

### L9 Integration Points

| Hook | Location | Purpose |
|------|----------|---------|
| Task completion | `executor.py` | Extract learnings |
| Slack conversation | `slack_ingest.py` | Extract preferences |
| GMP completion | `/gmp` command | Extract patterns |
| Error correction | User feedback | Extract corrections |

---

## Summary

### What L9 Already Has
- ✅ RRF (Reciprocal Rank Fusion)
- ✅ Temporal decay
- ✅ Packet store with timestamps
- ✅ Semantic embeddings (pgvector)
- ✅ Neo4j graph (partial)

### What L9 Needs (Future GMPs)
- ❌ Explicit 4-tier hierarchy
- ❌ Semantic vs Episodic separation
- ❌ Fact-Event linking
- ❌ Strategy-based retrieval
- ❌ Multi-factor ranking (importance, frequency)
- ❌ Context engineering (tier injection)
- ❌ Active memory management

### Recommended GMP Sequence

1. **GMP-69:** Add `semantic_facts` and `episodic_events` tables (schema)
2. **GMP-70:** Add strategy-based retrieval router
3. **GMP-71:** Add tier-based context injection
4. **GMP-72:** Add active memory management (auto-encoding)

---

## References

- Source: `current_work/AI MEMORY RETRIEVAL ARCHITECTURE/AI MEMORY RETRIEVAL ARCHITECTURE.md`
- Anthropic Claude Memory: File-based hierarchy
- OpenAI Agents SDK: State-based + context injection
- DeepMind AriGraph: Dual semantic + episodic graphs
- Google Gemini: Agent plans its own retrieval strategy
