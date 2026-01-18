"""
CodeGenAgent GMP Engine
=======================

Code generation and expansion engine with SymPy integration.
Handles mathematical code generation and template expansion.

Part of the Quantum AI Factory architecture.

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
# DORA HEADER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_meta__ = {
    "component_id": "AGE-INTE-001",
    "component_name": "Gmp-Engine",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T02:12:34Z",
    "updated_at": "2026-01-18T02:12:34Z",
    "layer": "intelligence",
    "domain": "error_handling",
    "module_name": "GMP-Engine",
    "type": "exception",
    "status": "active",
    "purpose": "Handles mathematical code generation and template expansion. Part of the Quantum AI Factory architecture. Version: 1.0.0",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import asyncio
from typing import Any, Dict, List, Optional

import structlog

from services.symbolic_computation import (
    SymbolicComputation,
    CodeGenResult,
)
from .meta_loader import MetaLoader, MetaLoaderError
from .readme_generator import ReadmeGenerator, GeneratedReadme

logger = structlog.get_logger(__name__)


class CGMPEngineError(Exception):
    """Exception raised when code generation fails."""

    pass


class CGMPEngine:
    """
    Code Generation and Mathematical Processing Engine.

    Uses SymPy for mathematical code sections and template expansion
    for non-mathematical sections.
    """

    def __init__(
        self,
        meta_loader: Optional[MetaLoader] = None,
        symbolic_engine: Optional[SymbolicComputation] = None,
        readme_generator: Optional[ReadmeGenerator] = None,
        auto_generate_readme: bool = True,
    ):
        """
        Initialize the C-GMP engine.

        Args:
            meta_loader: MetaLoader instance for YAML parsing
            symbolic_engine: SymbolicComputation engine for math code
            readme_generator: ReadmeGenerator for documentation
            auto_generate_readme: Whether to auto-generate READMEs with code
        """
        self._meta_loader = meta_loader or MetaLoader()
        self._symbolic = symbolic_engine or SymbolicComputation()
        self._readme_generator = readme_generator or ReadmeGenerator()
        self._auto_generate_readme = auto_generate_readme
        self._generated_files: List[Dict[str, Any]] = []
        self._generated_readmes: List[GeneratedReadme] = []

        logger.info("c_gmp_engine_initialized", auto_readme=auto_generate_readme)

    async def expand_code_blocks(
        self,
        meta: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Expand all code blocks in a meta specification.

        Args:
            meta: Parsed meta specification with code sections

        Returns:
            List of expanded code blocks with generated content
        """
        code_sections = self._meta_loader.get_code_sections(meta)
        expanded = []

        for section in code_sections:
            try:
                if self._is_mathematical(section):
                    result = await self._expand_mathematical(section)
                else:
                    result = self._expand_template(section)

                expanded.append(
                    {
                        "original": section,
                        "expanded": result,
                        "success": True,
                    }
                )
            except Exception as e:
                logger.error(
                    "code_expansion_failed",
                    section_type=section.get("type", "unknown"),
                    error=str(e),
                )
                expanded.append(
                    {
                        "original": section,
                        "expanded": None,
                        "success": False,
                        "error": str(e),
                    }
                )

        logger.info(
            "code_blocks_expanded",
            total=len(code_sections),
            success=sum(1 for e in expanded if e["success"]),
        )

        return expanded

    def _is_mathematical(self, section: Dict[str, Any]) -> bool:
        """
        Determine if a code section is mathematical.

        Args:
            section: Code section dictionary

        Returns:
            True if section should use SymPy, False otherwise
        """
        # Check explicit type
        if section.get("type") == "mathematical":
            return True

        # Check for SymPy markers
        content = section.get("content", "")
        sympy_markers = [
            "sympy",
            "Symbol",
            "Expr",
            "lambdify",
            "integrate",
            "diff",
            "solve",
            "simplify",
        ]

        return any(marker in content for marker in sympy_markers)

    async def _expand_mathematical(
        self,
        section: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Expand a mathematical code section using SymPy.

        Args:
            section: Code section with mathematical content

        Returns:
            Expanded code with SymPy-generated output
        """
        expression = section.get("expression", section.get("content", ""))
        variables = section.get("variables", ["x"])
        language = section.get("language", "C")
        function_name = section.get("function_name", "generated_func")

        # Generate code using SymPy
        result: CodeGenResult = await self._symbolic.generate_code(
            expression=expression,
            variables=variables if isinstance(variables, list) else [variables],
            language=language,
            function_name=function_name,
        )

        if not result.success:
            raise CGMPEngineError(f"SymPy codegen failed: {result.error_message}")

        return {
            "type": "mathematical",
            "expression": expression,
            "language": result.language.value,
            "source_code": result.source_code,
            "function_name": function_name,
            "variables": variables,
        }

    def _expand_template(
        self,
        section: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Expand a template code section.

        Args:
            section: Code section with template content

        Returns:
            Expanded code with substitutions applied
        """
        content = section.get("content", "")
        substitutions = section.get("substitutions", {})

        # Apply simple string substitutions
        expanded_content = content
        for key, value in substitutions.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            expanded_content = expanded_content.replace(placeholder, str(value))

        return {
            "type": "template",
            "source_code": expanded_content,
            "substitutions_applied": list(substitutions.keys()),
        }

    async def generate_from_meta(
        self,
        meta_path: str,
    ) -> Dict[str, Any]:
        """
        Generate code from a meta specification file.

        Args:
            meta_path: Path to YAML meta specification

        Returns:
            Generation result with all expanded code blocks
        """
        try:
            # Load meta specification
            meta = self._meta_loader.load_meta(meta_path)

            if not self._meta_loader.validate_meta(meta):
                raise CGMPEngineError("Invalid meta specification")

            # Expand all code blocks
            expanded = await self.expand_code_blocks(meta)

            # Collect output files
            output_files = []
            for block in expanded:
                if block["success"] and "source_code" in block.get("expanded", {}):
                    filename = meta.get("filename", f"{meta.get('name', 'output')}.py")
                    output_files.append(
                        {
                            "filename": filename,
                            "content": block["expanded"]["source_code"],
                            "language": block["expanded"].get("language", "Python"),
                        }
                    )

            # Auto-generate README if enabled
            readme = None
            readme_metadata = None
            if self._auto_generate_readme:
                readme = self._generate_readme_for_meta(meta, expanded)
                self._generated_readmes.append(readme)
                readme_metadata = {
                    "filename": readme.filename,
                    "content": readme.content,
                    "metadata_yaml": readme.metadata_yaml,
                }

            result = {
                "success": True,
                "meta_path": meta_path,
                "name": meta.get("name", "unknown"),
                "description": meta.get("description", ""),
                "expanded_blocks": expanded,
                "output_files": output_files,
                "readme": readme_metadata,
            }

            self._generated_files.extend(output_files)

            logger.info(
                "meta_generation_complete",
                meta_path=meta_path,
                output_files=len(output_files),
                readme_generated=readme is not None,
            )

            return result

        except MetaLoaderError as e:
            logger.error("meta_generation_failed", error=str(e))
            return {
                "success": False,
                "meta_path": meta_path,
                "error": str(e),
            }
        except Exception as e:
            logger.error("meta_generation_error", error=str(e))
            return {
                "success": False,
                "meta_path": meta_path,
                "error": str(e),
            }

    async def generate_batch(
        self,
        meta_paths: List[str],
        parallel: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Generate code from multiple meta specifications.

        Args:
            meta_paths: List of paths to YAML specs
            parallel: Whether to generate in parallel

        Returns:
            List of generation results
        """
        if parallel:
            tasks = [self.generate_from_meta(path) for path in meta_paths]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to error results
            processed = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed.append(
                        {
                            "success": False,
                            "meta_path": meta_paths[i],
                            "error": str(result),
                        }
                    )
                else:
                    processed.append(result)

            return processed
        else:
            return [await self.generate_from_meta(path) for path in meta_paths]

    def get_generated_files(self) -> List[Dict[str, Any]]:
        """
        Get list of all generated files.

        Returns:
            List of generated file dictionaries
        """
        return self._generated_files.copy()

    def clear_generated(self) -> None:
        """Clear the list of generated files and READMEs."""
        self._generated_files.clear()
        self._generated_readmes.clear()

    def get_generated_readmes(self) -> List[GeneratedReadme]:
        """
        Get list of all generated READMEs.

        Returns:
            List of GeneratedReadme objects
        """
        return self._generated_readmes.copy()

    def _generate_readme_for_meta(
        self,
        meta: Dict[str, Any],
        expanded_blocks: List[Dict[str, Any]],
    ) -> GeneratedReadme:
        """
        Generate README documentation for a meta specification.

        Args:
            meta: The parsed meta specification
            expanded_blocks: The expanded code blocks

        Returns:
            GeneratedReadme with content and metadata
        """
        name = meta.get("name", "UnnamedModule")
        description = meta.get("description", "")
        version = meta.get("version", "1.0.0")

        # Extract API functions from expanded blocks
        api_functions = []
        for block in expanded_blocks:
            if block.get("success") and block.get("expanded"):
                exp = block["expanded"]
                if exp.get("function_name"):
                    api_functions.append(
                        {
                            "name": exp["function_name"],
                            "signature": f"def {exp['function_name']}({', '.join(exp.get('variables', []))})",
                            "description": f"Generated {exp.get('type', 'code')} function",
                        }
                    )

        # Extract dependencies
        dependencies = meta.get("dependencies", [])
        if not dependencies:
            # Infer from expanded blocks
            for block in expanded_blocks:
                if block.get("success") and block.get("expanded"):
                    exp = block["expanded"]
                    if exp.get("type") == "mathematical":
                        if "sympy" not in dependencies:
                            dependencies.append("sympy")
                        if "numpy" not in dependencies:
                            dependencies.append("numpy")

        # Extract configuration
        configuration = meta.get("configuration", {})

        # Generate purpose from meta
        purpose = meta.get("purpose", f"Provides {name} functionality.")

        # Extract responsibilities
        responsibilities = meta.get("responsibilities", [])
        if not responsibilities:
            responsibilities = [
                f"Implements {name} logic",
                "Exposes public API functions",
                "Handles error cases gracefully",
            ]

        # Determine AI scopes
        allowed_scopes = meta.get(
            "ai_allowed_scopes",
            [
                f"- `{name.lower()}/*.py` — Core module logic",
                f"- `tests/{name.lower()}/` — Unit tests",
            ],
        )
        restricted_scopes = meta.get(
            "ai_restricted_scopes",
            [
                "- API signature changes",
                "- Schema modifications",
            ],
        )
        forbidden_scopes = meta.get(
            "ai_forbidden_scopes",
            [
                "- Kernel entry points",
                "- Security-sensitive code",
            ],
        )

        # Generate the README
        readme = self._readme_generator.generate_module_readme(
            module_name=name,
            overview=description,
            purpose=purpose,
            responsibilities=responsibilities,
            api_functions=api_functions,
            dependencies=dependencies,
            configuration=configuration,
            version=version,
            allowed_scopes=allowed_scopes,
            restricted_scopes=restricted_scopes,
            forbidden_scopes=forbidden_scopes,
        )

        logger.info(
            "readme_generated_for_meta",
            module=name,
            api_count=len(api_functions),
            deps_count=len(dependencies),
        )

        return readme


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    # === IDENTITY ===
    "component_id": "AGE-INTE-001",
    # === GOVERNANCE ===
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "security_classification": "internal",
    # === DEPENDENCIES ===
    "dependencies": [],
    # === OPERATIONAL ===
    "execution_mode": "on-demand",
    "timeout_seconds": 30,
    "performance_tier": "batch",
    "retry_policy": "exponential",
    "circuit_breaker_enabled": True,
    "circuit_breaker_threshold": 5,
    # === OBSERVABILITY ===
    "monitoring_required": True,
    "logging_level": "info",
    "success_metrics": {
        "latency_p95_ms": 500,
        "throughput_ops_per_sec": 100,
        "availability_percent": 99.9,
        "error_rate_percent": 0.1,
    },
    # === DISCOVERY ===
    "tags": ["async", "error-handling", "exception", "intelligence", "logging"],
    "keywords": ["batch", "blocks", "clear", "code", "engine", "error"],
    "business_value": "Handles mathematical code generation and template expansion. Part of the Quantum AI Factory architecture. Version: 1.0.0",
    # === CHANGE TRACKING ===
    "last_modified": "2026-01-18T02:12:34Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================

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
