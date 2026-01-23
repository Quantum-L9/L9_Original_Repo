# Harvested Code Samples: Perplexity Refactor Analysis

**Source:** `current_work/01-20-2026/Refactor/PHASE 1_Refactor Plan.md`
**Harvested:** 2026-01-20
**Method:** Terminal `sed` extraction (content bypassed LLM)

## Files Extracted

| # | File | Lines | Description | ADR |
|---|------|-------|-------------|-----|
| 1 | `loop_stage_protocol.py` | 11 | LoopStage Protocol + LoopContext dataclass | [ADR-0040](../../adr/0040-loop-stage-protocol.md) |
| 2 | `loop_execution_pattern.py` | 4 | Simplified loop execution via stages | [ADR-0040](../../adr/0040-loop-stage-protocol.md) |
| 3 | `policy_protocols.py` | 11 | Cross-cutting policy protocols | [ADR-0044](../../adr/0044-agent-policy-protocols.md) |
| 4 | `policy_usage_pattern.py` | 8 | Policy injection in executor | [ADR-0044](../../adr/0044-agent-policy-protocols.md) |
| 5 | `tool_dispatch_protocols.py` | 9 | Tool dispatch service protocols | [ADR-0048](../../adr/0048-tool-dispatch-strategy.md) |
| 6 | `executor_config.py` | 6 | ExecutorConfig dataclass | [ADR-0041](../../adr/0041-executor-builder-pattern.md) |
| 7 | `execution_profile_protocol.py` | 4 | ExecutionProfile protocol | [ADR-0042](../../adr/0042-execution-profiles.md) |
| 8 | `executor_builder.py` | 8 | ExecutorBuilder pattern | [ADR-0041](../../adr/0041-executor-builder-pattern.md) |
| 9 | `controller_profile_protocol.py` | 3 | ControllerProfile protocol | [ADR-0043](../../adr/0043-controller-profiles.md) |
| 10 | `pipeline_usage.py` | 3 | Profile-based pipeline composition | [ADR-0043](../../adr/0043-controller-profiles.md) |
| 11 | `memory_facade.py` | 7 | MemorySubstrateService facade | [ADR-0047](../../adr/0047-memory-facade-decomposition.md) |

## Notes

- **Python 3.10+ Syntax:** Some samples use `Type | None` union syntax. Production implementations in ADRs use `typing.Union[Type, None]` for Python 3.9 compatibility.
- **Raw Samples:** These are verbatim extracts from Perplexity output. The ADRs contain expanded, production-ready versions.
- **Usage:** Reference these samples alongside their corresponding ADRs for implementation guidance.

## Related ADRs Created

| ADR | Title | Status |
|-----|-------|--------|
| 0040 | Loop Stage Protocol | Proposed |
| 0041 | Executor Builder Pattern | Proposed |
| 0042 | Execution Profiles | Proposed |
| 0043 | Controller Profiles | Proposed |
| 0044 | Agent Policy Protocols | Proposed |
| 0045 | Online/Offline Execution Split | Proposed |
| 0046 | Pipeline Stage Organization | Proposed |
| 0047 | Memory Facade Decomposition | Proposed |
| 0048 | Tool Dispatch Strategy | Proposed |
| 0049 | Checkpoint Plan Snapshots | Proposed |
| 0050 | Tool Registry Cache | Proposed |
