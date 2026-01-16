# GMP v2.0 Prompts

> Super prompts for evolving GMP from L2 (constrained) to L5 (autonomous)

## Files

| File | Purpose | Use With |
|------|---------|----------|
| `GMP-v2.0-Super-Prompt.md` | Main 725-line prompt for code generation | Perplexity Pro, Claude |
| `GMP-v2.0-Quick-Start.md` | Implementation guide with 5-phase roadmap | Human planning |
| `DELIVERY-SUMMARY.md` | Package overview and metrics | Quick reference |
| `GMP-v2.0-Summary.md` | Executive summary | Quick reference |

## How to Use

### Generate GMP v2.0 Implementation

1. Open `GMP-v2.0-Super-Prompt.md`
2. Paste into Perplexity Pro (or Claude)
3. Add instructions:
   ```
   Generate:
   1. All 8 GMP v2.0 prompt files
   2. SQL migrations for learning database
   3. Python modules for autonomy controller
   4. Test templates
   
   Quality: Production-ready, L9-aligned
   ```
4. Review and extract generated code via `/harvest`

### Implementation Roadmap

| Phase | Duration | Focus |
|-------|----------|-------|
| 1 | Weeks 1-2 | Knowledge extraction, pattern analysis |
| 2 | Weeks 3-4 | GMP v2.0 core (Phase 0/5 evolution) |
| 3 | Weeks 5-6 | Meta-learning system |
| 4 | Weeks 7-8 | Integration & testing |
| 5 | Weeks 9-10 | Production rollout |

## Related

- `core/gmp/` — Python implementation (extracted)
- `codegen/C-GMP Suite/` — GMP v1.0 prompts
- `.cursor/rules/80-gmp-execution.mdc` — Execution rules

---

**Extracted:** 2026-01-15 from `current_work/GMP-Evolution-Super-Prompt/`
