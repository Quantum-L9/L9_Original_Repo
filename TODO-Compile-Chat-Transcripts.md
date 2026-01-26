# TODO: Compile Chat Transcripts with AI Extraction

**Created:** 2026-01-19
**Priority:** MEDIUM
**Status:** PENDING

---

## Summary

The current `formal_lesson_extractor.py` uses **primitive regex pattern matching** to extract lessons from chat exports. This yields low-quality, generic lessons.

**Goal:** Build a proper AI-powered extractor using L9's existing infrastructure to extract:

- Lessons (mistakes and solutions)
- Preferences (user workflow patterns)
- Architecture decisions (what was chosen and why)
- Workflow patterns (successful sequences to reuse)

---

## Data Sources

| Source         | Location                                                 | Files   | Content                  |
| -------------- | -------------------------------------------------------- | ------- | ------------------------ |
| Session JSONs  | `.cursor-commands/intelligence/context-memory/sessions/` | 1,556   | Hourly session snapshots |
| Chat Exports   | `.cursor-commands/ops/logs/chat_exports/`                | 106,919 | Raw chat data            |
| Memory Index   | `.cursor-commands/ops/logs/memory_index.json`            | 1       | 133 extracted patterns   |
| Learning Files | `.cursor-commands/learning/failures/`                    | 6       | Existing lessons         |

---

## Existing Infrastructure to Use

| Component                     | Location                         | Purpose                                         |
| ----------------------------- | -------------------------------- | ----------------------------------------------- |
| **SemanticCompiler**          | `ir_engine/semantic_compiler.py` | LLM-based intent/constraint extraction (GPT-4o) |
| **IngestionPipeline**         | `memory/ingestion.py`            | Embedding generation + pgvector storage         |
| **SemanticSearch**            | `memory/semantic_search.py`      | pgvector similarity search                      |
| **InsightExtractionPipeline** | `memory/insight_extraction.py`   | Heuristic extraction (baseline)                 |

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│        GOVERNANCE KNOWLEDGE EXTRACTOR                        │
│        (LLM-powered, uses SemanticCompiler)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    ▼                      ▼                      ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ SESSION     │     │ LEARNING    │     │ CHAT        │
│ ANALYZER    │     │ SYNTHESIZER │     │ EXTRACTOR   │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ sessions/   │     │ failures/   │     │ chat_exports│
│ *.json      │     │ patterns/   │     │ *.txt       │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ INGESTION PIPELINE     │
              │ (embeddings + pgvector)│
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │ SYNTHESIZED OUTPUT:    │
              │ • lessons.yaml         │
              │ • preferences.yaml     │
              │ • decisions.md         │
              │ • workflow_patterns.md │
              └────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Create Extractor Script

- [ ] Create `scripts/governance_knowledge_extractor.py`
- [ ] Use `SemanticCompiler` or direct OpenAI calls
- [ ] Define extraction prompts for each category:
  - Lessons
  - Preferences
  - Architecture decisions
  - Workflow patterns

### Phase 2: Batch Processing

- [ ] Process session JSONs in batches (avoid token limits)
- [ ] Deduplicate similar extractions
- [ ] Score by confidence and frequency

### Phase 3: Storage Integration

- [ ] Store via `IngestionPipeline` with embeddings
- [ ] Enable semantic search for relevant lessons
- [ ] Link to source files (packet lineage)

### Phase 4: Output Generation

- [ ] Generate structured YAML outputs
- [ ] Update `repeated-mistakes.md` with high-quality lessons
- [ ] Create `preferences.yaml` for always-applied rules
- [ ] Generate architecture decision records

---

## Completed Today (2026-01-19)

- [x] Archived unused files (`signatures/`, migration scripts)
- [x] Fixed `formal_lesson_extractor.py` threshold references
- [x] Created `lesson_extraction_dry_run.py` for testing
- [x] Ran extraction: 20 lessons added to `repeated-mistakes.md`
- [x] Updated `92-learned-lessons.mdc` with positive patterns + repeat-mistake signals
- [x] Added Phase 0.5 (Context Harvest) to `/gmp` command

---

## Key Insight

> The 43 "user correction" occurrences show that **asking clarifying questions BEFORE starting** would prevent most rework. This is the highest-value lesson extracted.

---

## Reference Files

- Dry run script: `.cursor-commands/ops/scripts/lesson_extraction_dry_run.py`
- Current extractor: `.cursor-commands/ops/scripts/formal_lesson_extractor.py`
- Semantic compiler: `ir_engine/semantic_compiler.py`
- Ingestion pipeline: `memory/ingestion.py`

---

## Notes

- Current approach (regex) extracts ~20 lessons from 133 patterns
- AI approach should extract 100+ high-quality, specific lessons
- Should cluster similar patterns and generate canonical lessons
- Consider using Perplexity or Claude for extraction (not just GPT-4o)
