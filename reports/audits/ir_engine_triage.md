# Dead Code Triage: `ir_engine`

**Date:** 2026-02-14 05:42 UTC

## Symbol Classification

**USED** (19): `ConstraintChallenger`, `DeliberationCell`, `IRGenerator`, `IRGraph`, `IRToPlanAdapter`, `IRToPythonCompiler`, `IRValidator`, `MetaContract`, `MetaContractValidationResult`, `MetaToIRCompiler`, `ModuleIR`, `ModuleMetadata`, `SchemaValidationError`, `SchemaValidator`, `SemanticCompiler`, `SimulationRouter`, `WiringSpec`, `compile_meta_to_ir`, `validate_schema`
**INTERNAL_ONLY** (7): `ActionNode`, `ConstraintNode`, `GenerationTarget`, `IRMetadata`, `IRValidationResult`, `IntentNode`, `MetaContractValidationError`
**TEST_ONLY** (12): `AcceptanceSpec`, `BootImpact`, `DependencySpec`, `ErrorPolicy`, `ExternalSurface`, `IdempotencySpec`, `OwnershipSpec`, `PacketContract`, `RuntimeTouchpoints`, `RuntimeWiringSpec`, `SpecConfidence`, `TestScope`
**ZERO_REF** (14): `DependencyEdge`, `EnvironmentSpec`, `GlobalInvariantsAck`, `InterfacesSpec`, `ObservabilitySpec`, `OrchestrationSpec`, `PacketSpec`, `RepoSpec`, `StandardsSpec`, `TestSpec`, `compile_contract_to_ir`, `compile_ir_to_python`, `compile_ir_to_single`, `validate_and_parse`

## File Classification

**WIRED** (12):
- `ir_engine/compile_meta_to_ir.py`
- `ir_engine/constraint_challenger.py`
- `ir_engine/deliberation_cell.py`
- `ir_engine/ir_generator.py`
- `ir_engine/ir_schema.py`
- `ir_engine/ir_to_plan_adapter.py`
- `ir_engine/ir_to_python.py`
- `ir_engine/ir_validator.py`
- `ir_engine/meta_ir.py`
- `ir_engine/schema_validator.py`
- `ir_engine/semantic_compiler.py`
- `ir_engine/simulation_router.py`

## Recommended Actions

### Remove 7 internal-only symbols from `__all__`
These are used within the package but not externally. Remove from `__all__` to reduce API surface noise.

### Review 14 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.
