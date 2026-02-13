# File: tools/codegen/test_generator.py
"""
Production-grade autonomous test generator from YAML specs.

This is the core engine that:
  1. Loads and validates spec files
  2. Maps modules to test files
  3. Instantiates strategies
  4. Generates deterministic pytest code
  5. Validates generated code
  6. Emits diffs for human review

Design principles:
  - Deterministic: same spec + code = same tests every run
  - Fail-closed: errors are actionable, never silent incompatibility
  - Auditable: generated tests include genealogy (spec, version, date, strategy)
  - Extensible: strategies are composable; new patterns don't require core changes

Phase 1 Target:
  - TwoPhaseLoaderStrategy fully working
  - kernelloader + prompt_builder specs generateable
  - 50+ tests generated, passing, 95%+ coverage
"""

import json
import logging  # noqa: ADR-0019
import sys
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)

try:
    import jsonschema
except ImportError:
    jsonschema = None  # Optional dependency

# ============================================================================
# PHASE 1: MINIMAL VIABLE ENGINE
# ============================================================================

log = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for code generation."""

    spec_file: Path
    output_dir: Path
    mode: str = "check"  # check, write, diff, dry-run
    context_lines: int = 3
    force_write: bool = False  # Skip confirmation prompt
    run_tests: bool = False
    test_executor_config: Path | None = None


@dataclass
class GenerationResult:
    """Result of a generation run."""

    success: bool
    test_files: dict[str, str]  # filepath -> code
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)  # count, coverage, etc.


class SpecValidationError(Exception):
    """Raised when spec is invalid."""

    pass


class StrategyNotApplicableError(Exception):
    """Raised when strategy doesn't apply to module."""

    pass


class CodeGenerationError(Exception):
    """Raised when code generation fails."""

    pass


# ============================================================================
# SCAFFOLD 1: Spec Models (Dataclasses)
# ============================================================================

# TODO: Move to tools/codegen/models/spec_models.py in Phase 1


@dataclass
class FixtureSpec:
    """Fixture specification."""

    name: str
    scope: str  # function, class, module, session
    source: str | None = None  # Pre-existing fixture reference
    generator: str | None = None  # monkeypatch, tmpdir, custom
    description: str = ""


@dataclass
class AssertionSpec:
    """Single assertion specification."""

    type: str  # return_success, raises, string_contains, invariant, etc.
    expected: Any | None = None
    exception: str | None = None
    message_contains: list[str] | None = None
    predicate: str | None = None
    invariant_name: str | None = None


@dataclass
class ScenarioSpec:
    """Single test scenario (happy path, error case, edge case)."""

    scenario_id: str
    condition: str
    setup: list[dict[str, Any]] = field(default_factory=list)
    mocks: list[dict[str, Any]] = field(default_factory=list)
    execute: dict[str, Any] = field(default_factory=dict)
    assertions: list[AssertionSpec] = field(default_factory=list)


@dataclass
class UnitTestSpec:
    """Single unit test specification."""

    test_id: str
    name: str
    type: str  # filesystem_io, async, decorator, integration, resilience
    description: str = ""
    scenarios: list[ScenarioSpec] = field(default_factory=list)


@dataclass
class TestSuiteSpec:
    """Top-level test suite specification."""

    suite_id: str
    module: str  # e.g., core.kernels.kernelloader
    strategy: str  # e.g., two_phase_loader
    priority: str = "p1"  # p0, p1, p2
    metadata: dict[str, Any] = field(default_factory=dict)
    fixtures: list[FixtureSpec] = field(default_factory=list)
    unit_tests: list[UnitTestSpec] = field(default_factory=list)
    integration_tests: list[UnitTestSpec] = field(default_factory=list)
    resilience_tests: list[UnitTestSpec] = field(default_factory=list)


# ============================================================================
# SCAFFOLD 2: Strategy Base Class (ABC)
# ============================================================================

# TODO: Move to tools/codegen/strategies/base.py in Phase 1


class BaseStrategy(ABC):
    """
    Abstract base for test generation strategies.

    Each strategy encodes:
      - How to inspect module code facts
      - Pattern-specific test idioms
      - Governance invariants

    Concrete strategies must implement:
      - validate_applicability: Can I generate tests for this module?
      - extract_module_facts: What are the module's signatures, types, errors?
      - generate_*: Imports, fixtures, test functions
      - validate_generated_code: Is the code syntactically correct?
    """

    def __init__(self, engine: "TestTemplateEngine"):
        self.engine = engine
        self.name = self.__class__.__name__

    @abstractmethod
    def validate_applicability(self, module_path: str) -> tuple[bool, str | None]:
        """
        Check if this strategy applies to the given module.

        Returns:
            (is_applicable, error_message_if_not)

        Example:
            TwoPhaseLoaderStrategy checks: Does module have load_X + phase1 logic?
        """
        pass

    @abstractmethod
    def extract_module_facts(self, module_path: str) -> dict[str, Any]:
        """
        Introspect module to extract signatures, return types, error types, etc.

        Returns:
            {
              "functions": {"load_kernels": {"params": [...], "returns": ...}},
              "classes": {...},
              "errors": ["RuntimeError", "ValidationError"],
              "async_functions": [...],
            }
        """
        pass

    @abstractmethod
    def generate_imports(self) -> str:
        """Generate pytest imports, fixtures, etc."""
        pass

    @abstractmethod
    def generate_fixtures(self, fixtures: list[FixtureSpec]) -> str:
        """Generate @pytest.fixture definitions."""
        pass

    @abstractmethod
    def generate_test_function(
        self,
        test_spec: UnitTestSpec,
        scenario: ScenarioSpec,
    ) -> str:
        """Generate a single test function."""
        pass

    @abstractmethod
    def validate_generated_code(self, code: str) -> tuple[bool, str | None]:
        """
        Validate generated code before emitting.

        Returns:
            (is_valid, error_message_if_not)
        """
        pass


# ============================================================================
# SCAFFOLD 3: Test Template Engine (Core)
# ============================================================================


class TestTemplateEngine:
    """
    Deterministic test code generator from YAML specs.

    Workflow:
      1. Load spec(s)
      2. Validate against schema
      3. For each suite, resolve strategy
      4. For each test, generate code
      5. Validate generated code
      6. Emit to file or diff
    """

    # Strategy registry (populated as strategies are implemented)
    STRATEGIES: dict[str, type] = {}

    def __init__(self, repo_root: Path):
        """
        Initialize engine.

        Args:
            repo_root: Root of L9 repo
        """
        self.repo_root = repo_root
        self.spec_dir = repo_root / "private" / "specs"
        self.test_dir = repo_root / "tests"
        self.schema_file = Path(__file__).parent / "fixtures" / "spec_schema_v1.0.json"

        # Load JSON schema
        self.schema = self._load_schema()

        # Instantiate strategies
        self.strategies = {}
        # TODO: Import and instantiate concrete strategies here
        # from tools.codegen.strategies.two_phase_loader import TwoPhaseLoaderStrategy
        # self.strategies["two_phase_loader"] = TwoPhaseLoaderStrategy(self)

    def _load_schema(self) -> dict[str, Any]:
        """Load JSON schema for validation."""
        try:
            with open(self.schema_file) as f:
                return json.load(f)
        except FileNotFoundError:
            log.warning(
                f"Schema file not found: {self.schema_file}; skipping schema validation"
            )
            return {}

    def generate(
        self,
        config: GenerationConfig,
    ) -> GenerationResult:
        """
        Main entry point: load spec, generate tests, return result.

        Args:
            config: Generation configuration

        Returns:
            GenerationResult with generated code or errors
        """
        result = GenerationResult(success=False, test_files={})

        try:
            # Phase 1: Load and validate spec
            specs = self._load_and_validate_spec(config.spec_file)
            log.info(f"Loaded spec: {config.spec_file}")

            # Phase 2: Generate test code for each suite
            for suite_spec in specs.get("test_suites", []):
                test_code = self._generate_suite(suite_spec)
                test_file = self._module_to_test_path(suite_spec["module"])
                result.test_files[str(test_file)] = test_code
                log.info(f"Generated: {test_file}")

            # Phase 3: Apply mode (check, write, diff, etc.)
            self._apply_mode(config, result)

            result.success = True
            result.metrics = {
                "spec_file": str(config.spec_file),
                "num_test_files": len(result.test_files),
                "mode": config.mode,
            }

            return result

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            log.error(f"Generation failed: {e}", exc_info=True)
            return result

    def _load_and_validate_spec(self, spec_file: Path) -> dict[str, Any]:
        """
        Load YAML spec and validate against schema.

        Raises:
            SpecValidationError if spec is invalid
        """
        with open(spec_file) as f:
            spec = yaml.safe_load(f)

        # Validate against JSON schema (if available)
        if self.schema and jsonschema:
            try:
                jsonschema.validate(spec, self.schema)
                log.info("Spec validated against schema")
            except jsonschema.ValidationError as e:
                raise SpecValidationError(f"Schema validation failed: {e}")

        return spec

    def _generate_suite(self, suite_spec: dict[str, Any]) -> str:
        """
        Generate all test functions for a suite.

        Args:
            suite_spec: Suite specification dict

        Returns:
            Complete test file code as string
        """
        module_path = suite_spec["module"]
        strategy_name = suite_spec["strategy"]

        # Get strategy
        if strategy_name not in self.strategies:
            raise CodeGenerationError(f"Unknown strategy: {strategy_name}")

        strategy = self.strategies[strategy_name]

        # Validate applicability
        is_applicable, error = strategy.validate_applicability(module_path)
        if not is_applicable:
            raise StrategyNotApplicableError(
                f"Strategy {strategy_name} not applicable to {module_path}: {error}"
            )

        # Extract module facts
        module_facts = strategy.extract_module_facts(module_path)
        log.info(
            f"Extracted module facts from {module_path}: {len(module_facts.get('functions', {}))} functions"
        )

        # Generate code
        code_parts = []

        # Header comment (genealogy)
        header = self._generate_header(suite_spec, strategy_name)
        code_parts.append(header)
        code_parts.append("")

        # Imports
        imports = strategy.generate_imports()
        code_parts.append(imports)
        code_parts.append("")

        # Fixtures
        fixtures = suite_spec.get("fixtures", [])
        if fixtures:
            fixtures_code = strategy.generate_fixtures(fixtures)
            if fixtures_code:
                code_parts.append(fixtures_code)
                code_parts.append("")

        # Test functions
        for test_spec in suite_spec.get("unit_tests", []):
            for scenario in test_spec.get("scenarios", []):
                test_code = strategy.generate_test_function(test_spec, scenario)
                code_parts.append(test_code)
                code_parts.append("")

        # For integration + resilience tests
        for test_spec in suite_spec.get("integration_tests", []):
            for scenario in test_spec.get("scenarios", []):
                test_code = strategy.generate_test_function(test_spec, scenario)
                code_parts.append(test_code)
                code_parts.append("")

        for test_spec in suite_spec.get("resilience_tests", []):
            for scenario in test_spec.get("scenarios", []):
                test_code = strategy.generate_test_function(test_spec, scenario)
                code_parts.append(test_code)
                code_parts.append("")

        full_code = "\n".join(code_parts)

        # Validate
        is_valid, error = strategy.validate_generated_code(full_code)
        if not is_valid:
            raise CodeGenerationError(f"Generated code validation failed: {error}")

        return full_code

    def _generate_header(self, suite_spec: dict[str, Any], strategy_name: str) -> str:
        """Generate header comment with genealogy."""
        from datetime import datetime

        now = datetime.now().isoformat()
        module = suite_spec["module"]

        return textwrap.dedent(f"""
            # =============================================================================
            # AUTO-GENERATED TEST FILE
            # Spec: {suite_spec.get("spec_file", "unknown")}
            # Strategy: {strategy_name}
            # Module: {module}
            # Generated: {now}
            # DO NOT EDIT - Update spec and regenerate
            # =============================================================================
        """).strip()

    def _module_to_test_path(self, module_path: str) -> Path:
        """Map core.kernels.kernelloader → tests/core/kernels/test_kernelloader.py"""
        parts = module_path.split(".")
        test_file = f"test_{parts[-1]}.py"
        return self.test_dir / Path(*parts[:-1]) / test_file

    def _apply_mode(self, config: GenerationConfig, result: GenerationResult) -> None:
        """Apply mode: check, write, diff, etc."""
        if config.mode == "check":
            log.info("Mode=check: validation passed; no files written")

        elif config.mode == "write":
            if not config.force_write:
                # Prompt user
                logger.info("\n📝 generated {len(result.test_files)} test file(s):")
                for filepath in result.test_files:
                    logger.info("  • filepath", filepath=filepath)

                response = input("\nWrite changes? (y/n): ").strip().lower()
                if response != "y":
                    log.info("Write cancelled by user")
                    return

            # Write files
            for filepath, code in result.test_files.items():
                path = Path(filepath)
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w") as f:
                    f.write(code)
                log.info(f"✓ Wrote {filepath}")

        elif config.mode == "diff":
            # Show diffs (requires existing test files)
            for filepath, code in result.test_files.items():
                path = Path(filepath)
                if path.exists():
                    with open(path) as f:
                        old_code = f.read()

                    # Compute unified diff
                    diff = self._compute_diff(old_code, code, str(filepath))
                    logger.info("output", value=diff)
                else:
                    logger.info("[new file] filepath", filepath=filepath)
                    logger.info("output", value=code)

        elif config.mode == "dry-run":
            log.info("Mode=dry-run: spec validation passed")

    def _compute_diff(self, old: str, new: str, filepath: str) -> str:
        """Compute unified diff between old and new code."""
        import difflib

        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)

        diff_lines = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=filepath,
            tofile=filepath,
            n=3,
        )

        return "".join(diff_lines)


# ============================================================================
# SCAFFOLD 4: CLI Entry Point
# ============================================================================


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Autonomous test generator for L9",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            EXAMPLES:
              # Check if spec generates valid tests (no writes)
              %(prog)s --spec private/specs/core_kernels_tests.yaml --mode check

              # Show diff of changes
              %(prog)s --spec private/specs/core_kernels_tests.yaml --mode diff

              # Generate and write tests
              %(prog)s --spec private/specs/core_kernels_tests.yaml --mode write

              # Batch generate from all specs
              %(prog)s --spec-glob "private/specs/*.yaml" --mode check
        """),
    )

    parser.add_argument(
        "--spec",
        type=Path,
        help="Path to spec file",
    )
    parser.add_argument(
        "--spec-glob",
        type=str,
        help="Glob pattern for spec files (e.g., 'private/specs/*.yaml')",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tests"),
        help="Output directory for generated tests (default: tests/)",
    )
    parser.add_argument(
        "--mode",
        choices=["check", "write", "diff", "dry-run"],
        default="check",
        help="Generation mode (default: check)",
    )
    parser.add_argument(
        "--context-lines",
        type=int,
        default=3,
        help="Context lines in diff (default: 3)",
    )
    parser.add_argument(
        "--force-write",
        action="store_true",
        help="Skip confirmation prompt in write mode",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run pytest after generation",
    )
    parser.add_argument(
        "--test-executor-config",
        type=Path,
        help="Path to test executor config (for --run-tests)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Determine repo root
    repo_root = Path.cwd()

    # Create engine
    engine = TestTemplateEngine(repo_root)

    # Generate
    if args.spec:
        config = GenerationConfig(
            spec_file=args.spec,
            output_dir=args.output_dir,
            mode=args.mode,
            context_lines=args.context_lines,
            force_write=args.force_write,
            run_tests=args.run_tests,
            test_executor_config=args.test_executor_config,
        )
        result = engine.generate(config)

        if not result.success:
            logger.error("❌ generation failed:")
            for error in result.errors:
                logger.error("  • error", error=error)
            sys.exit(1)

        logger.info("✓ generated {len(result.test_files)} test file(s)")

    elif args.spec_glob:
        import glob

        spec_files = glob.glob(args.spec_glob)
        for spec_file in spec_files:
            config = GenerationConfig(
                spec_file=Path(spec_file),
                output_dir=args.output_dir,
                mode=args.mode,
                context_lines=args.context_lines,
                force_write=args.force_write,
                run_tests=args.run_tests,
                test_executor_config=args.test_executor_config,
            )
            result = engine.generate(config)

            if not result.success:
                logger.error("❌ spec file: {result.errors}", spec_file=spec_file)
                sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
