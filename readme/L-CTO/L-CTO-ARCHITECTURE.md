# L-CTO System Architecture

*Updated: 2026-01-08 (GMP-44 Auto-Discovery)*

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         L-CTO SYSTEM ARCHITECTURE                           │
│                        (After Migration - Jan 2026)                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            ACTIVE SYSTEM                                    │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────┐
                              │  api/server.py   │
                              │    (lifespan)    │
                              └────────┬─────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────────┐
                    │   core/agents/kernel_registry.py     │
                    │      KernelAwareAgentRegistry        │
                    │                                      │
                    │  • _initialize_with_kernels()        │
                    │  • Creates AgentConfig with kernels  │
                    │  • Sets L9_KERNEL_STATE = ACTIVE     │
                    └──────────────────┬───────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ runtime/            │  │ agents/l_cto.py     │  │ l-cto/l-cto-yaml-   │
│ kernel_loader.py    │  │                     │  │ files/              │
│                     │  │   LCTOAgent         │  │                     │
│ • load_kernels()    │  │   • absorb_kernels()│  │ • 00-masterkernel   │
│ • parse YAML        │  │   • run()           │  │ • 02-identity       │
│ • validate kernels  │  │   • emit_reasoning  │  │ • 08-safety         │
└─────────────────────┘  │     _packet()       │  │ • etc. (10 kernels) │
                         └─────────────────────┘  └─────────────────────┘
                                       │
                                       ▼
                         ┌─────────────────────────┐
                         │  core/agents/executor.py│
                         │  AgentExecutorService   │
                         │                         │
                         │  • Pre-exec governance  │
                         │  • validate_authority() │
                         │  • validate_safety()    │
                         │  • Post-exec audit_log()│
                         └───────────┬─────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ core/agents/        │  │ memory/             │  │ core/governance/    │
│ aios_runtime.py     │  │ substrate_service.py│  │ validation.py       │
│                     │  │                     │  │                     │
│ AIOSRuntime         │  │ MemorySubstrate     │  │ • validate_authority│
│ • execute_reasoning │  │   Service           │  │ • validate_safety   │
│ • LLM calls         │  │ • ingest_packet()   │  │ • detect_drift      │
│ • tool dispatch     │  │ • PacketEnvelopeIn  │  │ • audit_log         │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                          ARCHIVED (deprecated)                              │
│                     archive/deprecated/l-cto-legacy/                        │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
  │   startup.py      │   │   l_cto_core/     │   │  l_cto_interface/ │
  │   ❌ ARCHIVED     │   │   ❌ ARCHIVED     │   │   ❌ ARCHIVED     │
  │                   │   │                   │   │                   │
  │   LStartup class  │   │   LIdentity       │   │   RuntimeClient   │
  │   Old boot seq    │   │   Hardcoded ID    │   │   Basic HTTP      │
  └───────────────────┘   └───────────────────┘   └───────────────────┘

  ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
  │   l_governance/   │   │    l_memory/      │   │    engine.py      │
  │   ❌ ARCHIVED     │   │   ❌ ARCHIVED     │   │   ❌ ARCHIVED     │
  │                   │   │                   │   │                   │
  │   Broken imports  │   │   Broken imports  │   │   LEngine class   │
  └───────────────────┘   └───────────────────┘   └───────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW SUMMARY                                 │
└─────────────────────────────────────────────────────────────────────────────┘

  Request                          Processing                         Storage
 ─────────                        ────────────                        ─────────
                                        
 HTTP/Slack  ─────►  server.py  ─────►  KernelAwareAgentRegistry
    │                                          │
    │                              ┌───────────┴───────────┐
    │                              │                       │
    │                        load_kernels()          LCTOAgent
    │                         (10 YAML)           (absorb kernels)
    │                              │                       │
    │                              └───────────┬───────────┘
    │                                          │
    │                                          ▼
    │                              AgentExecutorService
    │                                          │
    │                              ┌───────────┼───────────┐
    │                              │           │           │
    │                        Pre-Govern    AIOSRuntime  Post-Audit
    │                              │           │           │
    │                              └───────────┼───────────┘
    │                                          │
    ▼                                          ▼
 Response  ◄────────────────────  MemorySubstrateService ────► PostgreSQL
                                          │                        │
                                          └──────────────────►  Neo4j
```

## Key Files

| Component | File | Purpose |
|-----------|------|---------|
| Entry Point | `api/server.py` | FastAPI lifespan, initializes registry |
| Registry | `core/agents/kernel_registry.py` | Creates kernel-aware agents |
| Kernel Loader | `runtime/kernel_loader.py` | Parses 10 YAML kernels |
| Agent | `agents/l_cto.py` | LCTOAgent with kernel absorption |
| Executor | `core/agents/executor.py` | Governance + execution loop |
| Runtime | `core/agents/aios_runtime.py` | LLM calls + tool dispatch |
| Memory | `memory/substrate_service.py` | Packet ingestion |
| Governance | `core/governance/validation.py` | Authority/safety checks |

## Kernel Files

Located in `l-cto/l-cto-yaml-files/`:
- `00-masterkernel.yaml`
- `02-identity.yaml`
- `08-safety.yaml`
- ... (10 total kernels)

## Tool Auto-Discovery (GMP-44)

Tools are **auto-discovered** from `ToolDefinition.agent_id`:

```
register_l_tools() → _TOOL_AGENT_IDS["tool"] = "L" → get_approved_tools() checks dict
```

| Component | File | Role |
|-----------|------|------|
| Executor functions | `runtime/l_tools.py` | 71 async functions |
| ToolDefinitions | `core/tools/registry_adapter.py` | Metadata + auto-discovery |
| CI Gate | `ci/check_tool_wiring.py` | Validates consistency |

**To add a tool:** 
1. Add executor to `l_tools.py`
2. Add ToolDefinition with `agent_id="L"` to `register_l_tools()`

No manual enum or capability list updates needed.

