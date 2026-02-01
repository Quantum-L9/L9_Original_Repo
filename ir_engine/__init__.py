"""
L9 IR Engine - Intent Representation Engine
============================================

Core module for extracting, validating, and transforming user intents
into structured intermediate representations for execution.

Components:
- ir_schema: Data models for IR nodes and graphs
- semantic_compiler: Natural language to IR conversion
- ir_validator: Schema validation and completeness checks
- ir_generator: IR output generation
- constraint_challenger: Detect/challenge false constraints
- simulation_router: Route IR to simulation engine
- ir_to_plan_adapter: Convert IR to executable plans
- deliberation_cell: 2-agent collaboration for IR refinement
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Intent Representation Engine",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-31T22:21:58Z",
    "layer": "intelligence",
    "domain": "ir_compilation",
    "module_name": "__init__",
    "type": "adapter",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

from ir_engine.compile_meta_to_ir import (
    DependencyEdge,
    GenerationTarget,
    MetaToIRCompiler,
    ModuleIR,
    PacketSpec,
    TestSpec,
    WiringSpec,
    compile_contract_to_ir,
    compile_meta_to_ir,
)
from ir_engine.constraint_challenger import ConstraintChallenger
from ir_engine.deliberation_cell import DeliberationCell
from ir_engine.ir_generator import IRGenerator
from ir_engine.ir_schema import (
    ActionNode,
    ConstraintNode,
    IntentNode,
    IRGraph,
    IRMetadata,
    IRValidationResult,
)
from ir_engine.ir_to_plan_adapter import IRToPlanAdapter
from ir_engine.ir_to_python import (
    IRToPythonCompiler,
    compile_ir_to_python,
    compile_ir_to_single,
)
from ir_engine.ir_validator import IRValidator
from ir_engine.meta_ir import (
    AcceptanceSpec,
    BootImpact,
    DependencySpec,
    EnvironmentSpec,
    ErrorPolicy,
    ExternalSurface,
    GlobalInvariantsAck,
    IdempotencySpec,
    InterfacesSpec,
    MetaContract,
    MetaContractValidationError,
    MetaContractValidationResult,
    ModuleMetadata,
    ObservabilitySpec,
    OrchestrationSpec,
    OwnershipSpec,
    PacketContract,
    RepoSpec,
    RuntimeTouchpoints,
    RuntimeWiringSpec,
    SpecConfidence,
    StandardsSpec,
    TestScope,
)
from ir_engine.schema_validator import (
    SchemaValidationError,
    SchemaValidator,
    validate_and_parse,
    validate_schema,
)
from ir_engine.semantic_compiler import SemanticCompiler
from ir_engine.simulation_router import SimulationRouter

__all__ = [
    "AcceptanceSpec",
    "ActionNode",
    "BootImpact",
    "ConstraintChallenger",
    "ConstraintNode",
    "DeliberationCell",
    "DependencyEdge",
    "DependencySpec",
    "EnvironmentSpec",
    "ErrorPolicy",
    "ExternalSurface",
    "GenerationTarget",
    "GlobalInvariantsAck",
    "IRGenerator",
    "IRGraph",
    "IRMetadata",
    "IRToPlanAdapter",
    # IR to Python Compiler
    "IRToPythonCompiler",
    "IRValidationResult",
    "IRValidator",
    "IdempotencySpec",
    # Schema
    "IntentNode",
    "InterfacesSpec",
    # MetaContract (Module-Spec v2.4)
    "MetaContract",
    "MetaContractValidationError",
    "MetaContractValidationResult",
    # IR Compiler
    "MetaToIRCompiler",
    "ModuleIR",
    "ModuleMetadata",
    "ObservabilitySpec",
    "OrchestrationSpec",
    "OwnershipSpec",
    "PacketContract",
    "PacketSpec",
    "RepoSpec",
    "RuntimeTouchpoints",
    "RuntimeWiringSpec",
    "SchemaValidationError",
    # Schema Validator
    "SchemaValidator",
    # Components
    "SemanticCompiler",
    "SimulationRouter",
    "SpecConfidence",
    "StandardsSpec",
    "TestScope",
    "TestSpec",
    "WiringSpec",
    "compile_contract_to_ir",
    "compile_ir_to_python",
    "compile_ir_to_single",
    "compile_meta_to_ir",
    "validate_and_parse",
    "validate_schema",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "IR_-INTE-005",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["adapter", "intelligence", "ir-compilation", "testing"],
    "keywords": ["agent", "engine", "intent", "module", "representation"],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:58Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
