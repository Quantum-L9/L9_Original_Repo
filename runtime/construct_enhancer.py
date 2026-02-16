"""
Construct Enhancer from Perplexity
===================================

Applies LLM-generated enhancements to code generation constructs.

This module bridges the SuperPrompt Emitter output with the
CodeGenAgent pipeline, allowing gaps in specs to be automatically
filled via Perplexity and then used for code generation.

Key Features:
- Parses Perplexity responses into structured patches
- Applies patches to MetaContract instances
- Validates enhanced contracts
- Supports batch enhancement

Part of the CodeGenAgent pipeline (Phase 6).

Version: 1.0.0
"""

from __future__ import annotations

from core.decorators import must_stay_async

# ============================================================================
__dora_meta__ = {
    "component_name": "Construct Enhancer",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-02T15:15:57Z",
    "updated_at": "2026-01-14T15:03:00Z",
    "layer": "operations",
    "domain": "runtime_operations",
    "module_name": "construct_enhancer",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Perplexity API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

from dataclasses import dataclass, field
from typing import Any

import aiofiles
import structlog
import yaml

from ir_engine.meta_ir import MetaContract, MetaContractValidationResult
from ir_engine.schema_validator import SchemaValidator
from runtime.superprompt_emitter import (
    GapAnalysis,
    GapDetector,
    PerplexityEnricher,
    SpecPatcher,
    SuperPromptEmitter,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# ENHANCEMENT RESULT
# =============================================================================


@dataclass
class EnhancementResult:
    """Result of a construct enhancement operation."""

    success: bool
    module_id: str

    # Input state
    original_gaps: int

    # Output state
    remaining_gaps: int
    patches_applied: int

    # Enhanced contract (if successful)
    enhanced_contract: MetaContract | None = None
    enhanced_spec: dict[str, Any] | None = None

    # Validation
    validation_result: MetaContractValidationResult | None = None

    # Errors
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def gaps_filled(self) -> int:
        """
        Calculates the number of gaps filled during the construct enhancement process.
        Args:
            self: Instance of EnhancementResult containing gap metrics.
        Returns:
            int: The count of gaps filled, representing progress in construct enhancement.
        """
        return self.original_gaps - self.remaining_gaps

    @property
    def fill_rate(self) -> float:
        """
        Calculates the fill rate of gaps filled during construct enhancement.
        Returns:
            float: The ratio of gaps filled to original gaps, representing enhancement completeness.
        """
        if self.original_gaps == 0:
            return 1.0
        return self.gaps_filled / self.original_gaps


# =============================================================================
# CONSTRUCT ENHANCER
# =============================================================================


class ConstructEnhancer:
    """
    Enhances incomplete specifications using LLM (Perplexity).

    Pipeline:
    1. Detect gaps in spec
    2. Generate SuperPrompt
    3. Send to Perplexity
    4. Parse response patches
    5. Apply patches to spec
    6. Validate enhanced spec
    7. Return MetaContract
    """

    def __init__(
        self,
        perplexity_api_key: str | None = None,
        strict_validation: bool = False,
    ):
        """
        Initialize the enhancer.

        Args:
            perplexity_api_key: API key for Perplexity (or use env var)
            strict_validation: Treat validation warnings as errors
        """
        self._gap_detector = GapDetector()
        self._prompt_emitter = SuperPromptEmitter()
        self._enricher = PerplexityEnricher(api_key=perplexity_api_key)
        self._patcher = SpecPatcher()
        self._validator = SchemaValidator(strict=strict_validation)

        logger.info(
            "construct_enhancer_initialized",
            strict_validation=strict_validation,
        )

    @must_stay_async("callers use await")
    async def enhance_spec(
        self,
        spec: dict[str, Any],
        max_iterations: int = 2,
    ) -> EnhancementResult:
        """
        Enhance a specification via Perplexity.

        Args:
            spec: Parsed YAML specification
            max_iterations: Maximum enhancement rounds

        Returns:
            EnhancementResult with enhanced contract
        """
        module_id = spec.get("metadata", {}).get("module_id", "unknown")

        result = EnhancementResult(
            success=False,
            module_id=module_id,
            original_gaps=0,
            remaining_gaps=0,
            patches_applied=0,
        )

        try:
            # Initial gap analysis
            gap_analysis = self._gap_detector.analyze(spec)
            result.original_gaps = gap_analysis.total_gaps

            if gap_analysis.total_gaps == 0:
                # No gaps, try direct conversion
                result.enhanced_spec = spec
                result.enhanced_contract = MetaContract(**spec)
                result.success = True
                logger.info("no_gaps_detected", module_id=module_id)
                return result

            # Enhancement loop
            current_spec = spec
            total_patches = 0

            for iteration in range(max_iterations):
                logger.info(
                    "enhancement_iteration",
                    module_id=module_id,
                    iteration=iteration + 1,
                    gaps=gap_analysis.total_gaps,
                )

                # Generate and send prompt
                superprompt = self._prompt_emitter.emit_from_spec(
                    current_spec,
                    gap_analysis,
                )

                enrichment = await self._enricher.enrich(superprompt)
                patches = enrichment.get("patches", [])

                if not patches:
                    logger.warning(
                        "no_patches_received",
                        module_id=module_id,
                        iteration=iteration + 1,
                    )
                    break

                # Apply patches
                current_spec = self._patcher.apply_patches(current_spec, patches)
                total_patches += len(patches)

                # Re-analyze
                gap_analysis = self._gap_detector.analyze(current_spec)

                if gap_analysis.total_gaps == 0:
                    break

            result.patches_applied = total_patches
            result.remaining_gaps = gap_analysis.total_gaps
            result.enhanced_spec = current_spec

            # Validate and convert to MetaContract
            validation = self._validator.validate_dict(current_spec)
            result.validation_result = validation

            if validation.valid:
                result.enhanced_contract = MetaContract(**current_spec)
                result.success = True
            else:
                for error in validation.errors:
                    result.errors.append(f"{error.field}: {error.message}")

            for warning in validation.warnings:
                result.warnings.append(f"{warning.field}: {warning.message}")

            logger.info(
                "enhancement_complete",
                module_id=module_id,
                success=result.success,
                gaps_filled=result.gaps_filled,
                fill_rate=f"{result.fill_rate:.0%}",
            )

        except Exception as e:
            result.errors.append(str(e))
            logger.error(
                "enhancement_failed",
                module_id=module_id,
                error=str(e),
            )

        return result

    async def enhance_yaml(self, yaml_path: str) -> EnhancementResult:
        """
        Enhance a YAML specification file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            EnhancementResult
        """
        async with aiofiles.open(yaml_path, encoding="utf-8") as f:
            spec = yaml.safe_load(await f.read())

        return await self.enhance_spec(spec)

    def analyze_gaps(self, spec: dict[str, Any]) -> GapAnalysis:
        """
        Analyze gaps without enhancement.

        Args:
            spec: Parsed specification

        Returns:
            GapAnalysis
        """
        return self._gap_detector.analyze(spec)

    def preview_enhancement(
        self,
        spec: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Preview what would be enhanced without making API calls.

        Args:
            spec: Parsed specification

        Returns:
            Preview information
        """
        gap_analysis = self._gap_detector.analyze(spec)
        superprompt = self._prompt_emitter.emit_from_spec(spec, gap_analysis)

        return {
            "module_id": gap_analysis.module_id,
            "total_gaps": gap_analysis.total_gaps,
            "critical_gaps": gap_analysis.critical_gaps,
            "can_proceed_without_enhancement": gap_analysis.can_proceed,
            "gaps": [
                {
                    "section": g.section,
                    "field": g.field,
                    "severity": g.severity,
                    "description": g.description,
                }
                for g in gap_analysis.gaps
            ],
            "prompt_length": len(superprompt.prompt_text),
            "prompt_preview": superprompt.prompt_text[:500] + "...",
        }


# =============================================================================
# BATCH ENHANCER
# =============================================================================


@dataclass
class BatchEnhancementResult:
    """Result of batch enhancement operation."""

    total_specs: int
    successful: int
    failed: int
    skipped: int

    results: list[EnhancementResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Returns the success rate of batch code enhancements as a float between 0.0 and 1.0, representing the proportion of successful enhancements."""
        if self.total_specs == 0:
            return 0.0
        return self.successful / self.total_specs


class BatchEnhancer:
    """
    Enhances multiple specifications in batch.
    """

    def __init__(
        self,
        perplexity_api_key: str | None = None,
        rate_limit_delay: float = 1.0,
    ):
        """
        Initialize batch enhancer.

        Args:
            perplexity_api_key: API key for Perplexity
            rate_limit_delay: Seconds between API calls
        """
        self._enhancer = ConstructEnhancer(perplexity_api_key=perplexity_api_key)
        self._rate_limit_delay = rate_limit_delay

        logger.info(
            "batch_enhancer_initialized",
            rate_limit_delay=rate_limit_delay,
        )

    @must_stay_async("callers use await")
    async def enhance_directory(
        self,
        directory: str,
        pattern: str = "*.yaml",
        skip_valid: bool = True,
    ) -> BatchEnhancementResult:
        """
        Enhance all specs in a directory.

        Args:
            directory: Directory containing YAML specs
            pattern: Glob pattern for files
            skip_valid: Skip specs that are already valid

        Returns:
            BatchEnhancementResult
        """
        import asyncio
        from pathlib import Path

        dir_path = Path(directory)
        yaml_files = list(dir_path.glob(pattern))

        batch_result = BatchEnhancementResult(
            total_specs=len(yaml_files),
            successful=0,
            failed=0,
            skipped=0,
        )

        logger.info(
            "batch_enhancement_starting",
            directory=str(directory),
            file_count=len(yaml_files),
        )

        for yaml_file in yaml_files:
            try:
                async with aiofiles.open(yaml_file) as f:
                    spec = yaml.safe_load(await f.read())

                # Check if already valid
                if skip_valid:
                    gap_analysis = self._enhancer.analyze_gaps(spec)
                    if gap_analysis.total_gaps == 0:
                        batch_result.skipped += 1
                        logger.debug("spec_skipped_valid", path=str(yaml_file))
                        continue

                # Enhance
                result = await self._enhancer.enhance_spec(spec)
                batch_result.results.append(result)

                if result.success:
                    batch_result.successful += 1
                else:
                    batch_result.failed += 1

                # Rate limiting
                await asyncio.sleep(self._rate_limit_delay)

            except Exception as e:
                batch_result.failed += 1
                logger.error(
                    "batch_file_failed",
                    path=str(yaml_file),
                    error=str(e),
                )

        logger.info(
            "batch_enhancement_complete",
            total=batch_result.total_specs,
            successful=batch_result.successful,
            failed=batch_result.failed,
            skipped=batch_result.skipped,
        )

        return batch_result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def enhance_spec(spec: dict[str, Any]) -> EnhancementResult:
    """
    Enhance a specification via Perplexity.

    Args:
        spec: Parsed specification

    Returns:
        EnhancementResult
    """
    enhancer = ConstructEnhancer()
    return await enhancer.enhance_spec(spec)


async def enhance_yaml(yaml_path: str) -> EnhancementResult:
    """
    Enhance a YAML file via Perplexity.

    Args:
        yaml_path: Path to YAML file

    Returns:
        EnhancementResult
    """
    enhancer = ConstructEnhancer()
    return await enhancer.enhance_yaml(yaml_path)


def preview_enhancement(spec: dict[str, Any]) -> dict[str, Any]:
    """
    Preview what would be enhanced.

    Args:
        spec: Parsed specification

    Returns:
        Preview information
    """
    enhancer = ConstructEnhancer()
    return enhancer.preview_enhancement(spec)


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "RUN-OPER-005",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["runtime.superprompt_emitter"],
    "tags": [
        "api",
        "async",
        "batch-processing",
        "config",
        "dataclass",
        "debugging",
        "filesystem",
        "logging",
        "messaging",
        "operations",
    ],
    "keywords": [
        "analyze",
        "applies",
        "batch",
        "codegenagent",
        "construct",
        "directory",
        "enhance",
        "enhancement",
    ],
    "business_value": "This module bridges the SuperPrompt Emitter output with the CodeGenAgent pipeline, allowing gaps in specs to be automatically filled via Perplexity and then used for code generation. Parses Perplexity",
    "last_modified": "2026-01-14T15:03:00Z",
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
