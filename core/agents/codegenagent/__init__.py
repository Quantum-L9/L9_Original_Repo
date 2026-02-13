"""
CodeGenAgent Package
====================

Autonomous code generation agent for the Quantum AI Factory.
Transforms YAML specs into production code via Module-Spec-v2.4.

Pipeline:
1. MetaLoader -> Load and validate YAML spec
2. MetaToIRCompiler -> Transform to intermediate representation
3. IRToPythonCompiler -> Generate Python code from IR
4. FileEmitter -> Write files and wire into L9

Features:
- Contract-driven code generation from Module-Spec-v2.4
- SymPy-powered mathematical code expansion (optional)
- Automatic server.py wiring
- Rollback support
- Batch generation

Version: 2.0.0
"""

from .c_gmp_engine import CGMPEngine, CGMPEngineError
from .codegen_agent import (
    BatchResult,
    CodeGenAgent,
    DryRunResult,
    GenerationResult,
    generate_from_spec,
    preview_spec,
)
from .file_emitter import (
    EmissionResult,
    FileChange,
    FileEmitter,
    emit_files,
    preview_emission,
)
from .meta_loader import MetaLoader, MetaLoaderError, load_as_contract, load_meta
from .readme_generator import (
    GeneratedReadme,
    ReadmeGenerator,
    ReadmeMetadata,
    ReadmeSection,
    generate_readme_for_module,
)

__all__ = [
    "BatchResult",
    # Code generation engine (legacy)
    "CGMPEngine",
    "CGMPEngineError",
    # Main orchestrator
    "CodeGenAgent",
    "DryRunResult",
    "EmissionResult",
    "FileChange",
    # File emission
    "FileEmitter",
    "GeneratedReadme",
    "GenerationResult",
    # Meta loading
    "MetaLoader",
    "MetaLoaderError",
    # README generation
    "ReadmeGenerator",
    "ReadmeMetadata",
    "ReadmeSection",
    "emit_files",
    "generate_from_spec",
    "generate_readme_for_module",
    "load_as_contract",
    "load_meta",
    "preview_emission",
    "preview_spec",
]
