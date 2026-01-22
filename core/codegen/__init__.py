"""
Unified CodeGen System v1.0.0

Complete code generation system consolidating 11 existing systems into one
intelligent agent-driven architecture.

Components:
- CodeGenGatekeeperAgent: Main entry point for all code generation
- ModuleCompiler: Deterministic Module-Spec v2.6 → Python compiler
- CodeValidator: 14-gate validation pipeline
- DORABlockGenerator: Metadata block generation
- GitSafetyManager: Git-based safety and rollback
- PerplexityResearcher: Live research integration

Author: L9 AIOS
Version: 1.0.0
Created: 2025-12-31
"""

from .gatekeeper.codegen_gatekeeper import (
    CodeGenGatekeeperAgent,
    ContractType,
    NormalizedSpec,
    CodeGenOutput,
    BlindSpot,
    ResearchFinding
)

from .compiler.module_compiler import (
    ModuleCompiler,
    CompilationResult
)

__version__ = "1.0.0"
__all__ = [
    "CodeGenGatekeeperAgent",
    "ContractType",
    "NormalizedSpec",
    "CodeGenOutput",
    "BlindSpot",
    "ResearchFinding",
    "ModuleCompiler",
    "CompilationResult",
]
