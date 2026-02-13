"""
CodeGenAgent - Central Orchestrator
====================================

Main entry point for L9 code generation from YAML specifications.

Chains the complete pipeline:
1. MetaLoader: Load and validate YAML spec
2. MetaToIRCompiler: Transform to intermediate representation
3. IRToPythonCompiler: Generate Python code from IR
4. FileEmitter: Write files and wire into L9

Supports:
- Single spec generation
- Batch generation from directory
- Preview mode (dry run)
- Rollback capability

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Central Orchestrator",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-17T14:27:43Z",
    "layer": "intelligence",
    "domain": "agent_execution",
    "module_name": "codegen_agent",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from agents.codegenagent.file_emitter import FileEmitter
from agents.codegenagent.meta_loader import MetaLoader, MetaLoaderError
from core.decorators import must_stay_async
from ir_engine.compile_meta_to_ir import MetaToIRCompiler, ModuleIR
from ir_engine.ir_to_python import IRToPythonCompiler
from ir_engine.meta_ir import MetaContract, MetaContractValidationResult

# Symbolic verification pipeline (optional - graceful degradation if not available)
try:
    from codegen.symbolic.pipeline import SymbolicCodegenPipeline
    from codegen.symbolic.spec import CodegenIntent, CodegenSpec

    SYMBOLIC_PIPELINE_AVAILABLE = True
except ImportError:
    SYMBOLIC_PIPELINE_AVAILABLE = False
    SymbolicCodegenPipeline = None
    CodegenSpec = None
    CodegenIntent = None

logger = structlog.get_logger(__name__)


# =============================================================================
# RESULT MODELS
# =============================================================================


@dataclass
class GenerationResult:
    """Result of a code generation operation."""

    success: bool
    module_id: str
    source_path: str

    # Generated outputs
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)

    # Intermediate artifacts
    ir: ModuleIR | None = None
    generated_code: dict[str, str] = field(default_factory=dict)

    # Errors
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @property
    def duration_ms(self) -> float | None:
        """
        Calculates the duration of the code generation process in milliseconds.

        Args:
            None

        Returns:
            Optional[float]: Duration in milliseconds if the process has completed; otherwise, None.

        Raises:
            None
        """
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None

    def to_summary(self) -> dict[str, Any]:
        """Returns a summary dictionary of the code generation result, including success status, module ID, source path, and counts of created and modified files."""
        return {
            "success": self.success,
            "module_id": self.module_id,
            "source_path": self.source_path,
            "files_created": len(self.files_created),
            "files_modified": len(self.files_modified),
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_ms": self.duration_ms,
        }


@dataclass
class DryRunResult:
    """Result of a preview/dry-run operation."""

    module_id: str
    source_path: str

    # What would be created
    new_files: list[dict[str, Any]] = field(default_factory=list)
    """Returns the number of new files that would be created in the code generation dry-run."""
    modified_files: list[dict[str, Any]] = field(default_factory=list)
    directories_to_create: list[str] = field(default_factory=list)
    """Returns the number of files that would be modified during the dry run, indicating potential changes in the code generation process."""

    # Validation
    validation_result: MetaContractValidationResult | None = None

    # Generated code (for inspection)
    generated_code: dict[str, str] = field(default_factory=dict)

    @property
    def would_create(self) -> int:
        """Returns the number of new files that would be created in the code generation dry-run, indicating potential changes based on the YAML specifications."""
        return len(self.new_files)

    @property
    def would_modify(self) -> int:
        """Returns the number of files that would be modified during a dry run of the code generation process."""
        return len(self.modified_files)


@dataclass
class BatchResult:
    """Returns True if the batch code generation succeeded without failures."""

    """Result of batch generation operation."""

    total_specs: int
    successful: int
    failed: int
    skipped: int

    results: list[GenerationResult] = field(default_factory=list)
    """Returns True if the batch code generation succeeded without failures."""

    @property
    def success(self) -> bool:
        """Returns True if the batch code generation succeeded without failures."""
        return self.failed == 0


@dataclass
class SymbolicVerificationResult:
    """Result of symbolic code verification/generation."""

    success: bool
    """Returns a dictionary representation of the symbolic verification result, including success status, generated code, evaluation metrics, and rationale."""
    code: str | None = None
    candidates_evaluated: int = 0
    invariants_verified: bool = False
    selection_rationale: str = ""

    # Error info
    error: str | None = None
    spec: dict[str, Any] | None = None

    # Pipeline metadata
    pipeline_available: bool = SYMBOLIC_PIPELINE_AVAILABLE
    """Returns a dictionary representation of the symbolic verification result, including success status, generated code, evaluation metrics, and rationale."""

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the symbolic verification result, including success status, generated code, evaluated candidates, verified invariants, and selection rationale."""
        return {
            "success": self.success,
            "code": self.code,
            "candidates_evaluated": self.candidates_evaluated,
            "invariants_verified": self.invariants_verified,
            "selection_rationale": self.selection_rationale,
            "error": self.error,
            "pipeline_available": self.pipeline_available,
        }


# =============================================================================
# CODEGEN AGENT
# =============================================================================


class CodeGenAgent:
    """
    Central orchestrator for L9 code generation.

    Provides a high-level interface for generating code from YAML specs,
    chaining MetaLoader -> IR Compiler -> Python Compiler -> File Emitter.
    """

    def __init__(
        self,
        repo_root: str = "/Users/ib-mac/Projects/L9",
        specs_dir: str | None = None,
        strict_validation: bool = False,
    ):
        """
        Initialize the CodeGenAgent.

        Args:
            repo_root: Root path of L9 repository
            specs_dir: Directory containing YAML specs (default: auto-detect)
            strict_validation: Treat validation warnings as errors
        """
        self.repo_root = Path(repo_root)
        self.specs_dir = (
            Path(specs_dir) if specs_dir else self.repo_root / "codegen" / "specs"
        )
        self.strict_validation = strict_validation

        # Initialize components
        self._loader = MetaLoader(
            specs_dir=str(self.specs_dir),
            strict_validation=strict_validation,
        )
        self._ir_compiler = MetaToIRCompiler(repo_root=str(self.repo_root))
        self._py_compiler = IRToPythonCompiler()

        # Initialize symbolic verification pipeline (optional)
        self._symbolic_pipeline = None
        if SYMBOLIC_PIPELINE_AVAILABLE:
            try:
                self._symbolic_pipeline = SymbolicCodegenPipeline()
                logger.info("symbolic_pipeline_initialized")
            except Exception as e:
                logger.warning("symbolic_pipeline_init_failed", error=str(e))

        logger.info(
            "codegen_agent_initialized",
            repo_root=str(self.repo_root),
            specs_dir=str(self.specs_dir),
            strict_validation=strict_validation,
            symbolic_pipeline=self._symbolic_pipeline is not None,
        )

    @must_stay_async("callers use await")
    async def generate_from_contract(
        self,
        contract: MetaContract,
        dry_run: bool = False,
    ) -> GenerationResult:
        """
        Generate code from a validated MetaContract.

        Args:
            contract: Validated MetaContract instance
            dry_run: If True, don't write files

        Returns:
            GenerationResult with details
        """
        result = GenerationResult(
            success=False,
            module_id=contract.metadata.module_id,
            source_path="<contract>",
        )

        try:
            # Step 1: Compile to IR
            logger.info(
                "compiling_contract_to_ir", module_id=contract.metadata.module_id
            )
            ir = self._ir_compiler.compile(contract)
            result.ir = ir

            # Step 2: Generate Python code
            logger.info("generating_python_code", module_id=ir.module_id)
            generated_code = self._py_compiler.compile(ir)
            result.generated_code = generated_code

            # Step 3: Emit files
            if not dry_run:
                logger.info(
                    "emitting_files",
                    module_id=ir.module_id,
                    file_count=len(generated_code),
                )
                emitter = FileEmitter(repo_root=str(self.repo_root), dry_run=dry_run)
                emission = emitter.emit_from_ir(ir, generated_code)

                result.files_created = emission.created_files
                result.files_modified = emission.modified_files

                if emission.errors:
                    for path, error in emission.errors:
                        result.errors.append(f"{path}: {error}")

            result.success = len(result.errors) == 0
            result.completed_at = datetime.now(UTC)

            logger.info(
                "generation_complete",
                **result.to_summary(),
            )

        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.now(UTC)
            logger.error(
                "generation_failed",
                module_id=contract.metadata.module_id,
                error=str(e),
            )

        return result

    @must_stay_async("callers use await")
    async def generate_from_meta(
        self,
        meta_path: str,
        dry_run: bool = False,
    ) -> GenerationResult:
        """
        Generate code from a YAML meta specification file.

        Args:
            meta_path: Path to YAML file (absolute or relative to specs_dir)
            dry_run: If True, don't write files

        Returns:
            GenerationResult with details
        """
        result = GenerationResult(
            success=False,
            module_id="unknown",
            source_path=meta_path,
        )

        try:
            # Step 1: Load and validate
            logger.info("loading_meta", path=meta_path)
            contract = self._loader.load_as_contract(meta_path)
            result.module_id = contract.metadata.module_id

            # Delegate to generate_from_contract
            gen_result = await self.generate_from_contract(contract, dry_run=dry_run)

            # Copy results
            result.success = gen_result.success
            result.files_created = gen_result.files_created
            result.files_modified = gen_result.files_modified
            result.ir = gen_result.ir
            result.generated_code = gen_result.generated_code
            result.errors = gen_result.errors
            result.warnings = gen_result.warnings
            result.completed_at = datetime.now(UTC)

        except MetaLoaderError as e:
            result.errors.append(f"Load error: {e}")
            result.completed_at = datetime.now(UTC)
            logger.error("meta_load_failed", path=meta_path, error=str(e))
        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.now(UTC)
            logger.error("generation_failed", path=meta_path, error=str(e))

        return result

    @must_stay_async("callers use await")
    async def preview(self, meta_path: str) -> DryRunResult:
        """
        Preview what would be generated without writing files.

        Args:
            meta_path: Path to YAML file

        Returns:
            DryRunResult with preview information
        """
        result = DryRunResult(
            module_id="unknown",
            source_path=meta_path,
        )

        try:
            # Load and validate
            contract = self._loader.load_as_contract(meta_path)
            result.module_id = contract.metadata.module_id

            # Validate
            result.validation_result = self._loader.validate_meta(meta_path)

            # Compile to IR
            ir = self._ir_compiler.compile(contract)

            # Generate code
            generated_code = self._py_compiler.compile(ir)
            result.generated_code = generated_code

            # Preview emission
            emitter = FileEmitter(repo_root=str(self.repo_root), dry_run=True)
            preview = emitter.preview(generated_code)

            result.new_files = preview.get("new_files", [])
            result.modified_files = preview.get("modified_files", [])
            result.directories_to_create = preview.get("directories_to_create", [])

            logger.info(
                "preview_complete",
                module_id=result.module_id,
                would_create=result.would_create,
                would_modify=result.would_modify,
            )

        except Exception as e:
            logger.error("preview_failed", path=meta_path, error=str(e))
            raise

        return result

    @must_stay_async("callers use await")
    async def generate_batch(
        self,
        pattern: str = "*.yaml",
        directory: str | None = None,
        dry_run: bool = False,
        stop_on_error: bool = False,
    ) -> BatchResult:
        """
        Generate code from multiple YAML specs.

        Args:
            pattern: Glob pattern for spec files
            directory: Directory to search (default: specs_dir)
            dry_run: If True, don't write files
            stop_on_error: If True, stop on first error

        Returns:
            BatchResult with aggregate results
        """
        search_dir = Path(directory) if directory else self.specs_dir
        yaml_files = list(search_dir.glob(pattern))

        batch_result = BatchResult(
            total_specs=len(yaml_files),
            successful=0,
            failed=0,
            skipped=0,
        )

        logger.info(
            "batch_generation_starting",
            total_specs=len(yaml_files),
            directory=str(search_dir),
            pattern=pattern,
        )

        for yaml_file in yaml_files:
            # Check if this is a Module-Spec-v2.4 format
            try:
                raw = self._loader.load_meta(str(yaml_file))
                schema_format = self._loader.detect_schema_format(raw)

                if schema_format != "module-spec-v2.4":
                    logger.debug(
                        "spec_skipped_wrong_format",
                        path=str(yaml_file),
                        format=schema_format,
                    )
                    batch_result.skipped += 1
                    continue

                # Generate
                gen_result = await self.generate_from_meta(
                    str(yaml_file), dry_run=dry_run
                )
                batch_result.results.append(gen_result)

                if gen_result.success:
                    batch_result.successful += 1
                else:
                    batch_result.failed += 1
                    if stop_on_error:
                        logger.warning("batch_stopped_on_error", path=str(yaml_file))
                        break

            except Exception as e:
                batch_result.failed += 1
                logger.error("batch_file_failed", path=str(yaml_file), error=str(e))
                if stop_on_error:
                    break

        logger.info(
            "batch_generation_complete",
            total=batch_result.total_specs,
            successful=batch_result.successful,
            failed=batch_result.failed,
            skipped=batch_result.skipped,
        )

        return batch_result

    def validate_spec(self, meta_path: str) -> MetaContractValidationResult:
        """
        Validate a YAML spec without generating code.

        Args:
            meta_path: Path to YAML file

        Returns:
            Validation result
        """
        return self._loader.validate_meta(meta_path)

    def list_available_specs(
        self,
        pattern: str = "*.yaml",
        format_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List available YAML specs in the specs directory.

        Args:
            pattern: Glob pattern
            format_filter: Only return specs of this format

        Returns:
            List of spec information dicts
        """
        specs = []

        for yaml_file in self.specs_dir.glob(pattern):
            try:
                raw = self._loader.load_meta(str(yaml_file))
                schema_format = self._loader.detect_schema_format(raw)

                if format_filter and schema_format != format_filter:
                    continue

                specs.append(
                    {
                        "path": str(yaml_file),
                        "name": yaml_file.name,
                        "format": schema_format,
                        "module_id": raw.get("metadata", {}).get("module_id"),
                    }
                )
            except Exception as e:
                logger.debug("spec_list_error", path=str(yaml_file), error=str(e))

        return specs

    # =========================================================================
    # SYMBOLIC VERIFICATION
    # =========================================================================

    @must_stay_async("callers use await")
    async def generate_with_symbolic_verification(
        self,
        intent: str,
        target_behavior: str,
        input_code: str | None = None,
        invariants: list[str] | None = None,
        constraints: list[str] | None = None,
        variables: list[str] | None = None,
    ) -> SymbolicVerificationResult:
        """
        Generate or transform code using symbolic verification.

        Uses the SymPy-based symbolic pipeline to:
        1. Build CodegenSpec from inputs
        2. Generate multiple symbolic candidates
        3. Analyze each candidate mathematically
        4. Verify equivalence and invariant preservation
        5. Select best candidate based on heuristics

        This enforces:
        - Spec-first (CodegenSpec)
        - Symbolic proof (EquivalenceVerifier)
        - Test-bound (verifications)
        - Kernel-governed (SYMBOLIC_CODEGEN_KERNEL.v2)

        Args:
            intent: One of "generate", "refactor", "optimize", "verify"
            target_behavior: Natural language or formal description of desired behavior
            input_code: Existing code (required for refactor/optimize/verify)
            invariants: Symbolic or logical invariants the code must preserve
            constraints: Hard constraints (e.g., 'no floating point division')
            variables: Variable names and types for symbolic analysis

        Returns:
            SymbolicVerificationResult with verified code or error
        """
        # Check if pipeline is available
        if not SYMBOLIC_PIPELINE_AVAILABLE or self._symbolic_pipeline is None:
            logger.warning("symbolic_verification_unavailable")
            return SymbolicVerificationResult(
                success=False,
                error="Symbolic pipeline not available. Install sympy and ensure codegen.symbolic is accessible.",
                pipeline_available=False,
            )

        # Ensure CodegenSpec and CodegenIntent are available
        if CodegenSpec is None or CodegenIntent is None:
            logger.warning("symbolic_spec_classes_unavailable")
            return SymbolicVerificationResult(
                success=False,
                error="Symbolic spec classes not available. Check codegen.symbolic.spec imports.",
                pipeline_available=False,
            )

        try:
            # Stage 1: Build spec
            spec = CodegenSpec(
                intent=CodegenIntent(intent),
                target_behavior=target_behavior,
                input_code=input_code,
                invariants=invariants or [],
                constraints=constraints or [],
                variables=variables or [],
            )

            logger.info(
                "symbolic_verification_started",
                intent=intent,
                target_behavior=target_behavior[:50] if target_behavior else "",
                has_input_code=input_code is not None,
                num_invariants=len(invariants or []),
                num_variables=len(variables or []),
            )

            # Stage 2-5: Run pipeline
            result = self._symbolic_pipeline.execute(spec)

            if not result.success:
                logger.warning(
                    "symbolic_verification_failed",
                    errors=result.errors,
                )
                return SymbolicVerificationResult(
                    success=False,
                    error="; ".join(result.errors),
                    spec=spec.model_dump()
                    if hasattr(spec, "model_dump")
                    else spec.dict(),
                )

            # Extract verification status
            invariants_verified = (
                all(v.all_invariants_pass for v in result.verifications)
                if result.verifications
                else True
            )

            logger.info(
                "symbolic_verification_complete",
                candidates_evaluated=len(result.candidates),
                invariants_verified=invariants_verified,
            )

            return SymbolicVerificationResult(
                success=True,
                code=result.selected_code,
                candidates_evaluated=len(result.candidates),
                invariants_verified=invariants_verified,
                selection_rationale=result.selection_result.get(
                    "selection_rationale", ""
                ),
            )

        except Exception as e:
            logger.error("symbolic_verification_error", error=str(e))
            return SymbolicVerificationResult(
                success=False,
                error=str(e),
            )

    def is_symbolic_pipeline_available(self) -> bool:
        """Check if the symbolic verification pipeline is available."""
        return SYMBOLIC_PIPELINE_AVAILABLE and self._symbolic_pipeline is not None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def generate_from_spec(
    spec_path: str,
    dry_run: bool = False,
) -> GenerationResult:
    """
    Generate code from a YAML spec file.

    Args:
        spec_path: Path to YAML file
        dry_run: If True, don't write files

    Returns:
        GenerationResult
    """
    agent = CodeGenAgent()
    return await agent.generate_from_meta(spec_path, dry_run=dry_run)


async def preview_spec(spec_path: str) -> DryRunResult:
    """
    Preview what would be generated.

    Args:
        spec_path: Path to YAML file

    Returns:
        DryRunResult
    """
    agent = CodeGenAgent()
    return await agent.preview(spec_path)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "AGE-INTE-014",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "agents.codegenagent.file_emitter",
        "agents.codegenagent.meta_loader",
        "core.decorators",
    ],
    "tags": [
        "agent-execution",
        "async",
        "batch-processing",
        "config",
        "dataclass",
        "debugging",
        "filesystem",
        "intelligence",
        "logging",
        "testing",
    ],
    "keywords": [
        "agent",
        "available",
        "batch",
        "central",
        "contract",
        "create",
        "dry",
        "duration",
    ],
    "business_value": "1. MetaLoader: Load and validate YAML spec 2. MetaToIRCompiler: Transform to intermediate representation 3. IRToPythonCompiler: Generate Python code from IR 4. FileEmitter: Write files and wire into L",
    "last_modified": "2026-01-17T14:27:43Z",
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
