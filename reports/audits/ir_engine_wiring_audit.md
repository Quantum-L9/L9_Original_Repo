# Package Wiring Audit: ir_engine

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `ir_engine`

Files checked: 12
- WIRED: 11
- PARTIAL: 1
- ORPHAN: 0
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `ir_engine/compile_meta_to_ir.py` | 4 | 1 | - | Y | OK |
| `ir_engine/constraint_challenger.py` | 2 | 0 | - | Y | OK |
| `ir_engine/deliberation_cell.py` | 1 | 0 | - | Y | OK |
| `ir_engine/ir_generator.py` | 0 | 1 | - | Y | PARTIAL |
| `ir_engine/ir_schema.py` | 2 | 6 | - | Y | OK |
| `ir_engine/ir_to_plan_adapter.py` | 2 | 2 | - | Y | OK |
| `ir_engine/ir_to_python.py` | 2 | 1 | - | Y | OK |
| `ir_engine/ir_validator.py` | 2 | 3 | - | Y | OK |
| `ir_engine/meta_ir.py` | 6 | 2 | - | Y | OK |
| `ir_engine/schema_validator.py` | 3 | 2 | - | Y | OK |
| `ir_engine/semantic_compiler.py` | 2 | 2 | - | Y | OK |
| `ir_engine/simulation_router.py` | 2 | 1 | Y | Y | OK |

## Level C: API Instantiation — `ir_engine`

API Status: **HAS_API**
Symbols checked: 52
- USED: 19
- TEST_ONLY: 17
- UNUSED: 16

| Symbol | Ext | Test | Status |
|--------|----:|-----:|--------|
| `AcceptanceSpec` | 0 | 2 | TEST_ONLY |
| `ActionNode` | 0 | 4 | TEST_ONLY |
| `BootImpact` | 0 | 2 | TEST_ONLY |
| `ConstraintNode` | 0 | 3 | TEST_ONLY |
| `DependencyEdge` | 0 | 0 | UNUSED |
| `DependencySpec` | 0 | 2 | TEST_ONLY |
| `EnvironmentSpec` | 0 | 0 | UNUSED |
| `ErrorPolicy` | 0 | 2 | TEST_ONLY |
| `ExternalSurface` | 0 | 2 | TEST_ONLY |
| `GenerationTarget` | 0 | 0 | UNUSED |
| `GlobalInvariantsAck` | 0 | 0 | UNUSED |
| `IRMetadata` | 0 | 5 | TEST_ONLY |
| `IRValidationResult` | 0 | 1 | TEST_ONLY |
| `IdempotencySpec` | 0 | 2 | TEST_ONLY |
| `IntentNode` | 0 | 4 | TEST_ONLY |
| `InterfacesSpec` | 0 | 0 | UNUSED |
| `MetaContractValidationError` | 0 | 0 | UNUSED |
| `ObservabilitySpec` | 0 | 0 | UNUSED |
| `OrchestrationSpec` | 0 | 0 | UNUSED |
| `OwnershipSpec` | 0 | 2 | TEST_ONLY |
| `PacketContract` | 0 | 2 | TEST_ONLY |
| `PacketSpec` | 0 | 0 | UNUSED |
| `RepoSpec` | 0 | 0 | UNUSED |
| `RuntimeTouchpoints` | 0 | 2 | TEST_ONLY |
| `RuntimeWiringSpec` | 0 | 2 | TEST_ONLY |
| `SpecConfidence` | 0 | 2 | TEST_ONLY |
| `StandardsSpec` | 0 | 0 | UNUSED |
| `TestScope` | 0 | 2 | TEST_ONLY |
| `TestSpec` | 0 | 0 | UNUSED |
| `compile_contract_to_ir` | 0 | 0 | UNUSED |
| `compile_ir_to_python` | 0 | 0 | UNUSED |
| `compile_ir_to_single` | 0 | 0 | UNUSED |
| `validate_and_parse` | 0 | 0 | UNUSED |

**API-pattern symbols NOT in `__all__`:**
- `EscalationConfig`
- `LogsConfig`
- `MetricsConfig`
- `RetryConfig`
- `TracesConfig`
