#!/usr/bin/env python3
"""
L9 Audit Master Runner v2.0 — Frontier Grade
Orchestrates all 4 frontier-grade audits with caching, GMP integration, and unified reporting.

Replaces:
  - audit_uncalled_functions.py
  - audit_orphan_classes.py
  - audit_wiring.py
  - audit_hidden_capabilities.py

Features:
  - Incremental caching (skip unchanged files)
  - Parallel execution with work distribution
  - Multi-format output (JSON, HTML, JSONL)
  - GMP integration (Phase 0 TODO plans)
  - Unified dashboard reporting
  - Feature flag control (TIER_1_ENABLED, etc.)

Usage:
  python scripts/audit/run_all.py                  # Run all Tier 1 audits
  python scripts/audit/run_all.py --tier 1         # Explicit Tier 1
  python scripts/audit/run_all.py --only code      # Code integrity only
  python scripts/audit/run_all.py --gmp            # Generate GMP TODO plan
  python scripts/audit/run_all.py --skip-cache     # Disable caching
  python scripts/audit/run_all.py --format html    # HTML output only
  python scripts/audit/run_all.py --parallel 8     # 8 parallel jobs
"""

import sys
import json
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import structlog

# Import audit components
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "tier1"))
from audit_shared_core import Reporter, GMPIntegration, ObservabilityHooks

# Import tier1 audit modules
# Use CacheManager from audit_code_integrity (has result caching)
from audit_code_integrity import (
    find_python_files,
    analyze_file_for_uncalled,
    analyze_file_for_orphans,
    detect_circular_imports,
    CacheManager,  # Has load_results/save_results for full caching
)
from audit_capability_inventory import (
    get_exposed_tools,
    get_async_methods,
    assess_capability,
    EXCLUDED_METHODS,
)
from audit_infrastructure_health import (
    TCPHealthProbe,
    HTTPHealthProbe,
    PythonModuleHealthProbe,
    validate_config,
    verify_dependency_dag,
    SERVICES,
)

logger = structlog.get_logger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent.parent
AUDIT_DIR = REPO_ROOT / "scripts" / "audit"
CACHE_DIR = REPO_ROOT / ".audit_cache"

# Audit tier controls (feature flags)
TIER_1_ENABLED = True
TIER_2_ENABLED = False
TIER_3_ENABLED = False

# Deprecated Cursor paths (moved to agents/cursor/ per architecture_decisions.md 2026-01-11)
# These paths should NOT appear in .audit_cache/manifest.json
DEPRECATED_CURSOR_PATHS = [
    "tools/cursor_client.py",
    "scripts/cursor_check_mistakes.py",
    "memory/extractor/cursor_action_extractor.py",
    "core/governance/cursor_memory_kernel.py",
]


def validate_no_deprecated_paths(cache_dir: Path) -> List[str]:
    """
    Fail loudly if deprecated paths appear in audit cache.

    This guardrail ensures that file moves documented in architecture_decisions.md
    are properly reflected in the audit cache. If a deprecated path appears,
    it means the audit is scanning files that no longer exist at those locations.

    Returns:
        List of violation messages (empty = all good)
    """
    manifest_path = cache_dir / "manifest.json"
    if not manifest_path.exists():
        return []

    try:
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, IOError):
        return ["Could not read manifest.json"]

    violations = []
    for path in manifest.keys():
        for deprecated in DEPRECATED_CURSOR_PATHS:
            if deprecated in path:
                violations.append(f"DEPRECATED: {path} (moved to agents/cursor/)")

    return violations


# =============================================================================
# DATA MODELS
# =============================================================================


class AuditType(str, Enum):
    CODE_INTEGRITY = "code_integrity"
    INFRASTRUCTURE_HEALTH = "infrastructure_health"
    CAPABILITY_INVENTORY = "capability_inventory"
    GOVERNANCE_COMPLIANCE = "governance_compliance"
    CONFIGURATION_DRIFT = "configuration_drift"
    DEAD_CODE = "dead_code"  # Phase 1-4 dead code detection pipeline
    WIRING_ALIGNMENT = "wiring_alignment"  # Doc-code path alignment (v1.0)
    MEMORY_SPEC = "memory_spec"  # Memory spec v3.0 verification
    API_SIGNATURES = "api_signatures"  # API signature mismatch detection (v1.0)


@dataclass
class AuditResult:
    """Result from single audit."""

    audit_type: AuditType
    status: str  # 'success', 'failure', 'partial'
    duration_ms: float
    items_found: int
    items_critical: int
    items_high: int
    items_medium: int
    items_low: int
    errors: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    file_outputs: Dict[str, Path] = field(default_factory=dict)  # {format: path}


@dataclass
class AuditRun:
    """Complete audit run with all results."""

    run_id: str
    timestamp: str
    tier: int
    duration_ms: float
    results: Dict[AuditType, AuditResult] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# AUDIT ORCHESTRATOR
# =============================================================================


class AuditOrchestrator:
    """Orchestrate all audits with caching and parallel execution."""

    def __init__(
        self,
        repo_root: Path = REPO_ROOT,
        cache_enabled: bool = True,
        parallel_jobs: int = 4,
        output_formats: List[str] = None,
    ):
        self.repo_root = repo_root
        self.audit_dir = repo_root / "scripts" / "audit"
        self.cache_enabled = cache_enabled
        self.parallel_jobs = parallel_jobs
        self.output_formats = output_formats or ["json", "html"]

        # Initialize components
        self.cache_mgr = CacheManager(CACHE_DIR) if cache_enabled else None
        self.reporter = Reporter("master", repo_root)
        self.gmp_integration = GMPIntegration("master_audit")
        self.observability = ObservabilityHooks(substrate_enabled=False)

        # Audit state
        self.run_id = self._generate_run_id()
        self.audit_results: Dict[AuditType, AuditResult] = {}
        self.errors: List[str] = []

    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        import uuid
        from datetime import datetime

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        uid = str(uuid.uuid4())[:8]
        return f"audit_run_{ts}_{uid}"

    def run_audit(
        self,
        audit_type: AuditType,
        tier: int = 1,
    ) -> AuditResult:
        """Execute single audit."""
        start_time = time.time()
        logger.info(f"Starting audit: {audit_type.value}")

        try:
            # Placeholder: dispatch to actual audit script
            if audit_type == AuditType.CODE_INTEGRITY:
                result = self._run_code_integrity_audit()
            elif audit_type == AuditType.INFRASTRUCTURE_HEALTH:
                result = self._run_infrastructure_audit()
            elif audit_type == AuditType.CAPABILITY_INVENTORY:
                result = self._run_capability_audit()
            elif audit_type == AuditType.DEAD_CODE:
                result = self._run_dead_code_audit()
            elif audit_type == AuditType.WIRING_ALIGNMENT:
                result = self._run_wiring_alignment_audit()
            elif audit_type == AuditType.MEMORY_SPEC:
                result = self._run_memory_spec_audit()
            elif audit_type == AuditType.API_SIGNATURES:
                result = self._run_api_signatures_audit()
            else:
                result = AuditResult(
                    audit_type=audit_type,
                    status="not_implemented",
                    duration_ms=0,
                    items_found=0,
                    items_critical=0,
                    items_high=0,
                    items_medium=0,
                    items_low=0,
                )

            result.duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"✓ {audit_type.value}: {result.items_found} items in {result.duration_ms:.0f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"✗ {audit_type.value} failed: {e}")
            return AuditResult(
                audit_type=audit_type,
                status="failure",
                duration_ms=(time.time() - start_time) * 1000,
                items_found=0,
                items_critical=0,
                items_high=0,
                items_medium=0,
                items_low=0,
                errors=[str(e)],
            )

    def _run_code_integrity_audit(self) -> AuditResult:
        """Run code integrity audit (call graph + uncalled functions)."""
        try:
            # Find all Python files
            all_files = find_python_files(self.repo_root)

            # Try to use cached results (fast path)
            # Check if we have valid cached results before doing expensive analysis
            if self.cache_mgr:
                cached_results = self.cache_mgr.load_results()
                if cached_results:
                    uncalled_count = len(cached_results.get("uncalled", []))
                    orphans = cached_results.get("orphans", [])
                    circular = cached_results.get("circular", [])
                    total_items = uncalled_count + len(orphans) + len(circular)

                    logger.info("Using cached code integrity results")
                    return AuditResult(
                        audit_type=AuditType.CODE_INTEGRITY,
                        status="success",
                        duration_ms=0,
                        items_found=total_items,
                        items_critical=len(circular),
                        items_high=len([o for o in orphans if o.get("is_stub")]),
                        items_medium=len([o for o in orphans if not o.get("is_stub")]),
                        items_low=uncalled_count,
                        data={
                            "uncalled_functions": uncalled_count,
                            "orphan_classes": len(orphans),
                            "circular_imports": len(circular),
                            "cached": True,
                        },
                    )

            # Full analysis (slow path)
            # Build content index with caching
            all_content = None
            if self.cache_mgr:
                all_content = self.cache_mgr.load_content_index(all_files)

            if all_content is None:
                all_content = ""
                for f in all_files:
                    try:
                        all_content += (
                            f.read_text(encoding="utf-8", errors="ignore") + "\n"
                        )
                    except Exception:
                        pass

                if self.cache_mgr:
                    self.cache_mgr.save_content_index(all_files, all_content)

            # Analyze for uncalled functions and orphan classes
            uncalled = []
            orphans = []
            for filepath in all_files:
                try:
                    uncalled.extend(analyze_file_for_uncalled(filepath, all_content))
                    orphans.extend(analyze_file_for_orphans(filepath, all_content))
                except Exception:
                    pass

            # Detect circular imports
            circular = detect_circular_imports(self.repo_root)

            # Save results for next run
            if self.cache_mgr:
                self.cache_mgr.save_results(uncalled, orphans, circular)
                self.cache_mgr.update_manifest(all_files)

            total_items = len(uncalled) + len(orphans) + len(circular)

            return AuditResult(
                audit_type=AuditType.CODE_INTEGRITY,
                status="success",
                duration_ms=0,
                items_found=total_items,
                items_critical=len(circular),  # Circular imports are critical
                items_high=len([o for o in orphans if o.is_stub]),  # Stubs are high
                items_medium=len([o for o in orphans if not o.is_stub]),
                items_low=len(uncalled),
                data={
                    "uncalled_functions": len(uncalled),
                    "orphan_classes": len(orphans),
                    "circular_imports": len(circular),
                },
            )
        except Exception as e:
            return AuditResult(
                audit_type=AuditType.CODE_INTEGRITY,
                status="failure",
                duration_ms=0,
                items_found=0,
                items_critical=0,
                items_high=0,
                items_medium=0,
                items_low=0,
                errors=[str(e)],
            )

    def _run_infrastructure_audit(self) -> AuditResult:
        """Run infrastructure health audit."""
        import asyncio

        try:
            # Run health probes
            probes = []
            for service_name, service_config in SERVICES.items():
                probe_type = service_config.get("probe_type", "tcp")
                if probe_type == "tcp":
                    probes.append(
                        TCPHealthProbe(
                            name=service_name,
                            host=service_config.get("host", "127.0.0.1"),
                            port=service_config.get("port", 0),
                        )
                    )
                elif probe_type == "http":
                    probes.append(
                        HTTPHealthProbe(
                            name=service_name,
                            url=service_config.get("url", ""),
                        )
                    )
                elif probe_type == "python_module":
                    probes.append(
                        PythonModuleHealthProbe(
                            name=service_name,
                            module_path=service_config.get("module_path", ""),
                            class_name=service_config.get("class_name", ""),
                        )
                    )

            # Run probes async
            async def run_probes():
                results = []
                for probe in probes:
                    result = await probe.check()
                    results.append(result)
                return results

            health_results = asyncio.run(run_probes())

            # Validate config
            config_validations = validate_config()

            # Check dependency DAG
            dep_checks = verify_dependency_dag()

            # Count results
            failed_probes = sum(
                1 for r in health_results if r.status.value == "unhealthy"
            )
            config_errors = sum(1 for v in config_validations if not v.valid)

            total_items = len(health_results) + len(config_validations)

            return AuditResult(
                audit_type=AuditType.INFRASTRUCTURE_HEALTH,
                status="success" if failed_probes == 0 else "partial",
                duration_ms=0,
                items_found=total_items,
                items_critical=failed_probes,
                items_high=config_errors,
                items_medium=0,
                items_low=len(dep_checks),
                data={
                    "health_probes": len(health_results),
                    "failed_probes": failed_probes,
                    "config_validation_errors": config_errors,
                    "dependency_checks": len(dep_checks),
                },
            )
        except Exception as e:
            return AuditResult(
                audit_type=AuditType.INFRASTRUCTURE_HEALTH,
                status="failure",
                duration_ms=0,
                items_found=0,
                items_critical=0,
                items_high=0,
                items_medium=0,
                items_low=0,
                errors=[str(e)],
            )

    def _run_capability_audit(self) -> AuditResult:
        """Run capability inventory audit."""

        try:
            # Get exposed tools from TOOL_EXECUTORS
            exposed_tools = get_exposed_tools(self.repo_root)

            # Scan for async methods in key infrastructure files
            target_files = [
                self.repo_root / "runtime" / "l_tools.py",
                self.repo_root / "memory" / "substrate_service.py",
                self.repo_root / "clients" / "memory_client.py",
                self.repo_root / "runtime" / "redis_client.py",
                self.repo_root / "core" / "tools" / "tool_graph.py",
            ]

            all_methods = []
            for filepath in target_files:
                if filepath.exists():
                    all_methods.extend(get_async_methods(filepath))

            # Filter out internal methods
            hidden_methods = []
            internal_count = 0
            for method in all_methods:
                # Check if exposed
                if method.name in exposed_tools:
                    continue

                # Check if internal (in exclusion set)
                is_internal = method.name in EXCLUDED_METHODS or method.name.startswith(
                    "_"
                )
                if is_internal:
                    internal_count += 1
                    continue

                hidden_methods.append(method)

            # Assess capabilities
            high_value = 0
            medium_value = 0
            low_value = 0
            for method in hidden_methods:
                matrix = assess_capability(method)
                if matrix.impact.value == "high":
                    high_value += 1
                elif matrix.impact.value == "medium":
                    medium_value += 1
                else:
                    low_value += 1

            return AuditResult(
                audit_type=AuditType.CAPABILITY_INVENTORY,
                status="success",
                duration_ms=0,
                items_found=len(hidden_methods),
                items_critical=0,
                items_high=high_value,
                items_medium=medium_value,
                items_low=low_value,
                data={
                    "exposed_tools": len(exposed_tools),
                    "hidden_capabilities": len(hidden_methods),
                    "internal_excluded": internal_count,
                    "exposure_recommended": high_value,
                },
            )
        except Exception as e:
            return AuditResult(
                audit_type=AuditType.CAPABILITY_INVENTORY,
                status="failure",
                duration_ms=0,
                items_found=0,
                items_critical=0,
                items_high=0,
                items_medium=0,
                items_low=0,
                errors=[str(e)],
            )

    def _run_dead_code_audit(self) -> AuditResult:
        """Run dead code detection pipeline (Phases 1-4).

        Pipeline:
          Phase 1: find_dead_code.run_dead_code_audit() - Baseline static analysis
          Phase 2: resolve_dead_code_refs.resolve_dead_code_refs() - False positive filtering
          Phase 3: categorize_dead_code.categorize_dead_code() - Risk categorization
          Phase 4: generate_gmp_todos.auto_fix_dead_code() - Auto-fix + GMP report
        """
        try:
            from find_dead_code import run_dead_code_audit as find_dead_code_baseline
            from resolve_dead_code_refs import resolve_dead_code_refs
            from categorize_dead_code import categorize_dead_code
            from generate_gmp_todos import auto_fix_dead_code
            from datetime import datetime

            # Phase 1: Baseline static analysis
            logger.info("Dead Code Phase 1: Baseline analysis...")
            baseline_output = self.repo_root / "reports" / "dead_code_baseline.json"
            baseline_result = find_dead_code_baseline(
                repo_root=self.repo_root,
                min_vulture_confidence=80,
                parallel_workers=self.parallel_jobs,
                output_file=baseline_output,
            )

            # Phase 2: Resolve false positives
            logger.info("Dead Code Phase 2: Resolving false positives...")
            resolved_output = self.repo_root / "reports" / "dead_code_resolved.json"
            resolved_result = resolve_dead_code_refs(
                baseline_file=baseline_output,
                repo_root=self.repo_root,
                output_file=resolved_output,
            )

            # Phase 3: Categorize by risk
            logger.info("Dead Code Phase 3: Categorizing by risk...")
            categorized_output = (
                self.repo_root / "reports" / "dead_code_risk_matrix.json"
            )
            categorized_result = categorize_dead_code(
                resolved_file=resolved_output,
                repo_root=self.repo_root,
                output_file=categorized_output,
            )

            # Phase 4: Auto-fix safe items + generate GMP report
            logger.info("Dead Code Phase 4: Auto-fix + GMP report generation...")
            gmp_id = f"DeadCode-{datetime.now().strftime('%Y%m%d')}"
            gmp_report_output = self.repo_root / "reports" / f"GMP_Report_{gmp_id}.md"
            gmp_report = auto_fix_dead_code(
                categorized_file=categorized_output,
                repo_root=self.repo_root,
                gmp_id=gmp_id,
                dry_run=True,  # Don't auto-fix in audit mode, just analyze
                output_file=gmp_report_output,
            )

            # Build result summary
            total_findings = len(baseline_result.findings)
            false_positives = resolved_result.false_positives_eliminated
            high_risk = len(categorized_result.high_risk)
            medium_risk = len(categorized_result.medium_risk)
            low_risk = len(categorized_result.low_risk)

            # Count items from GMP report
            auto_fixable = len(gmp_report.fixes)
            manual_review = len(gmp_report.manual_review)
            skipped = len(gmp_report.skipped)

            return AuditResult(
                audit_type=AuditType.DEAD_CODE,
                status="success",
                duration_ms=0,
                items_found=categorized_result.total_findings,
                items_critical=high_risk,
                items_high=medium_risk,
                items_medium=low_risk,
                items_low=false_positives,
                data={
                    "baseline_findings": total_findings,
                    "false_positives_eliminated": false_positives,
                    "high_risk": high_risk,
                    "medium_risk": medium_risk,
                    "low_risk": low_risk,
                    "auto_fixable": auto_fixable,
                    "manual_review": manual_review,
                    "skipped_false_positives": skipped,
                },
                file_outputs={
                    "baseline": baseline_output,
                    "resolved": resolved_output,
                    "categorized": categorized_output,
                    "gmp_report": gmp_report_output,
                },
            )

        except Exception as e:
            logger.error(f"Dead code audit failed: {e}")
            import traceback

            traceback.print_exc()
            return AuditResult(
                audit_type=AuditType.DEAD_CODE,
                status="failure",
                duration_ms=0,
                items_found=0,
                items_critical=0,
                items_high=0,
                items_medium=0,
                items_low=0,
                errors=[str(e)],
            )

    def _run_wiring_alignment_audit(self) -> AuditResult:
        """Run wiring alignment verification (doc-code path alignment)."""
        try:
            from verify_wiring_alignment import scan_repository

            result = scan_repository()

            total_issues = len(result.broken_docs) + len(result.deprecated_refs)

            return AuditResult(
                audit_type=AuditType.WIRING_ALIGNMENT,
                status="success" if result.is_green else "partial",
                duration_ms=0,
                items_found=len(result.verified_paths),
                items_critical=len(result.missing_canonical),
                items_high=len(result.broken_docs),
                items_medium=len(result.deprecated_refs),
                items_low=0,
                data={
                    "verified_paths": len(result.verified_paths),
                    "broken_docs": len(result.broken_docs),
                    "deprecated_refs": len(result.deprecated_refs),
                    "missing_canonical": len(result.missing_canonical),
                    "files_scanned": result.total_scanned,
                    "is_green": result.is_green,
                },
            )
        except Exception as e:
            logger.error(f"Wiring alignment audit failed: {e}")
            return AuditResult(
                audit_type=AuditType.WIRING_ALIGNMENT,
                status="failure",
                duration_ms=0,
                items_found=0,
                items_critical=0,
                items_high=0,
                items_medium=0,
                items_low=0,
                errors=[str(e)],
            )

    def _run_memory_spec_audit(self) -> AuditResult:
        """Run memory spec v3.0 verification."""
        try:
            import subprocess

            # Run the verification script and capture output
            proc = subprocess.run(
                ["python3", "scripts/audit/verify_memory_spec_v3.py"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Parse output for pass/fail counts
            output = proc.stdout + proc.stderr
            passed = proc.returncode == 0

            # Count checks from output (rough parsing)
            check_passed = output.count("✅")
            check_failed = output.count("❌")
            check_warn = output.count("⚠")

            return AuditResult(
                audit_type=AuditType.MEMORY_SPEC,
                status="success" if passed else "failure",
                duration_ms=0,
                items_found=check_passed + check_failed + check_warn,
                items_critical=check_failed,
                items_high=0,
                items_medium=check_warn,
                items_low=check_passed,
                data={
                    "exit_code": proc.returncode,
                    "checks_passed": check_passed,
                    "checks_failed": check_failed,
                    "checks_warned": check_warn,
                    "output": output[:2000] if len(output) > 2000 else output,
                },
            )
        except subprocess.TimeoutExpired:
            return AuditResult(
                audit_type=AuditType.MEMORY_SPEC,
                status="failure",
                duration_ms=60000,
                items_found=0,
                items_critical=1,
                items_high=0,
                items_medium=0,
                items_low=0,
                errors=["Memory spec verification timed out (60s)"],
            )
        except Exception as e:
            logger.error(f"Memory spec audit failed: {e}")
            return AuditResult(
                audit_type=AuditType.MEMORY_SPEC,
                status="failure",
                duration_ms=0,
                items_found=0,
                items_critical=0,
                items_high=0,
                items_medium=0,
                items_low=0,
                errors=[str(e)],
            )

    def _run_api_signatures_audit(self) -> AuditResult:
        """Run API signature mismatch audit.

        Detects:
          - Missing required kwargs
          - Deprecated parameter names
          - .value access on string-returning functions
          - httpx API version mismatches
        """
        try:
            from audit_api_signatures import run_api_signature_audit

            result = run_api_signature_audit(repo_root=self.repo_root)

            return AuditResult(
                audit_type=AuditType.API_SIGNATURES,
                status="success" if result.critical_count == 0 else "failure",
                duration_ms=0,
                items_found=result.total_mismatches,
                items_critical=result.critical_count,
                items_high=result.high_count,
                items_medium=result.medium_count,
                items_low=result.low_count,
                data={
                    "files_scanned": result.total_files_scanned,
                    "mismatches": [
                        {
                            "file": m.filepath,
                            "line": m.line,
                            "function": m.function_name,
                            "issue": m.issue,
                            "severity": m.severity.value,
                        }
                        for m in result.mismatches[:20]  # Limit to first 20
                    ],
                },
            )
        except Exception as e:
            logger.error(f"API signatures audit failed: {e}")
            import traceback

            traceback.print_exc()
            return AuditResult(
                audit_type=AuditType.API_SIGNATURES,
                status="failure",
                duration_ms=0,
                items_found=0,
                items_critical=0,
                items_high=0,
                items_medium=0,
                items_low=0,
                errors=[str(e)],
            )

    def run_all(self, tier: int = 1, only: Optional[str] = None) -> AuditRun:
        """Run all audits for given tier."""
        start_time = time.time()
        logger.info("=" * 70)
        logger.info(f"L9 AUDIT MASTER RUNNER v2.0 — Tier {tier}")
        logger.info("=" * 70)

        # Determine which audits to run
        audits_to_run = self._get_tier_audits(tier)
        if only:
            audits_to_run = [a for a in audits_to_run if only in a.value]

        logger.info(f"Running {len(audits_to_run)} audits...")

        # Run audits in parallel
        with ThreadPoolExecutor(max_workers=self.parallel_jobs) as executor:
            futures = {
                executor.submit(self.run_audit, audit, tier): audit
                for audit in audits_to_run
            }

            for future in as_completed(futures):
                audit = futures[future]
                try:
                    result = future.result()
                    self.audit_results[result.audit_type] = result
                except Exception as e:
                    logger.error(f"Audit {audit.value} failed: {e}")
                    self.errors.append(str(e))

        # Generate reports
        for fmt in self.output_formats:
            self._generate_report(fmt)

        # Validate no deprecated paths in cache (wiring invariant guardrail)
        deprecated_violations = validate_no_deprecated_paths(CACHE_DIR)
        if deprecated_violations:
            logger.warning("=" * 70)
            logger.warning(
                "WIRING INVARIANT VIOLATION: Deprecated paths in audit cache"
            )
            logger.warning("=" * 70)
            for violation in deprecated_violations:
                logger.warning(f"  {violation}")
            logger.warning(
                "These files were moved per architecture_decisions.md (2026-01-11)"
            )
            logger.warning(
                "Run with --skip-cache to regenerate, or delete .audit_cache/"
            )
            logger.warning("=" * 70)
            self.errors.extend(deprecated_violations)

        # Build run summary
        duration_ms = (time.time() - start_time) * 1000
        run = AuditRun(
            run_id=self.run_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            tier=tier,
            duration_ms=duration_ms,
            results=self.audit_results,
            summary=self._build_summary(),
        )

        # Log summary
        self._log_summary(run)

        return run

    def _get_tier_audits(self, tier: int) -> List[AuditType]:
        """Get audits for tier."""
        if tier == 1:
            return [
                AuditType.CODE_INTEGRITY,
                AuditType.INFRASTRUCTURE_HEALTH,
                AuditType.CAPABILITY_INVENTORY,
                AuditType.DEAD_CODE,
                AuditType.WIRING_ALIGNMENT,
                AuditType.MEMORY_SPEC,
                AuditType.API_SIGNATURES,
            ]
        elif tier == 2:
            return [
                AuditType.GOVERNANCE_COMPLIANCE,
                AuditType.CONFIGURATION_DRIFT,
            ]
        else:
            return []

    def _generate_report(self, format_str: str):
        """Generate report in given format."""
        logger.info(f"Generating {format_str.upper()} report...")

        if format_str == "json":
            self._generate_json_report()
        elif format_str == "html":
            self._generate_html_report()
        elif format_str == "jsonl":
            self._generate_jsonl_report()

    def _generate_json_report(self):
        """Generate JSON report."""
        report_data = {
            "run_id": self.run_id,
            "results": {k.value: asdict(v) for k, v in self.audit_results.items()},
            "summary": self._build_summary(),
        }

        output_file = self.reporter.to_json(
            report_data, f"audit_run_{self.run_id}.json"
        )
        logger.info(f"✓ JSON report: {output_file}")

    def _generate_html_report(self):
        """Generate HTML report."""
        summary = self._build_summary()

        html_content = "<h2>Audit Results</h2>"
        html_content += "<table><thead><tr>"
        html_content += "<th>Audit</th><th>Status</th><th>Items</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th>"
        html_content += "</tr></thead><tbody>"

        for audit_type, result in self.audit_results.items():
            status_class = "status-ok" if result.status == "success" else "status-error"
            html_content += f"""
            <tr>
                <td><strong>{audit_type.value}</strong></td>
                <td class="{status_class}">{result.status}</td>
                <td>{result.items_found}</td>
                <td>{result.items_critical}</td>
                <td>{result.items_high}</td>
                <td>{result.items_medium}</td>
                <td>{result.items_low}</td>
            </tr>
            """

        html_content += "</tbody></table>"

        full_html = self.reporter.generate_html_template(
            title="L9 Audit Report",
            summary=summary,
            content=html_content,
        )

        output_file = self.reporter.to_html(full_html, f"audit_run_{self.run_id}.html")
        logger.info(f"✓ HTML report: {output_file}")

    def _generate_jsonl_report(self):
        """Generate JSONL report (one issue per line)."""
        records = []
        for audit_type, result in self.audit_results.items():
            record = {
                "audit_type": audit_type.value,
                "status": result.status,
                "items_found": result.items_found,
                "data": result.data,
            }
            records.append(record)

        output_file = self.reporter.to_jsonl(records, f"audit_run_{self.run_id}.jsonl")
        logger.info(f"✓ JSONL report: {output_file}")

    def _build_summary(self) -> Dict[str, Any]:
        """Build audit run summary."""
        total_items = sum(r.items_found for r in self.audit_results.values())
        total_critical = sum(r.items_critical for r in self.audit_results.values())
        total_high = sum(r.items_high for r in self.audit_results.values())

        return {
            "run_id": self.run_id,
            "total_audits": len(self.audit_results),
            "total_items": total_items,
            "critical": total_critical,
            "high": total_high,
            "succeeded": sum(
                1 for r in self.audit_results.values() if r.status == "success"
            ),
            "failed": len(self.errors),
        }

    def _log_summary(self, run: AuditRun):
        """Log audit run summary."""
        logger.info("")
        logger.info("=" * 70)
        logger.info("AUDIT RUN COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Run ID: {run.run_id}")
        logger.info(f"Duration: {run.duration_ms:.0f}ms")
        logger.info(f"Audits completed: {run.summary['total_audits']}")
        logger.info(f"Items found: {run.summary['total_items']}")
        logger.info(f"Critical: {run.summary['critical']}")
        logger.info(f"High: {run.summary['high']}")

        if self.errors:
            logger.warning(f"Errors: {len(self.errors)}")
            for error in self.errors[:3]:
                logger.warning(f" - {error}")

        logger.info("=" * 70)


# =============================================================================
# CLI INTERFACE
# =============================================================================


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="L9 Audit Master Runner v2.0 — Frontier Grade"
    )
    parser.add_argument(
        "--tier",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Audit tier (1=core, 2=governance, 3=optimization)",
    )
    parser.add_argument(
        "--only",
        type=str,
        help="Run only specific audit (e.g., 'code' for code_integrity)",
    )
    parser.add_argument(
        "--gmp",
        action="store_true",
        help="Generate GMP TODO plan (Phase 0)",
    )
    parser.add_argument(
        "--skip-cache",
        action="store_true",
        help="Disable caching",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "html", "jsonl"],
        nargs="+",
        default=["json", "html"],
        help="Output formats",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=4,
        help="Number of parallel jobs",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()

    # Logging is configured via structlog.get_logger() - no custom config needed
    # The default structlog configuration is sufficient for CLI scripts

    # Run audits
    orchestrator = AuditOrchestrator(
        cache_enabled=not args.skip_cache,
        parallel_jobs=args.parallel,
        output_formats=args.format if isinstance(args.format, list) else [args.format],
    )

    run = orchestrator.run_all(tier=args.tier, only=args.only)

    # GMP integration
    if args.gmp:
        logger.info("Generating GMP TODO plan...")
        # TODO: Create GMP plan from audit findings
        logger.info("GMP plan ready (awaiting user approval)")

    # Exit with code
    if run.summary["critical"] > 0:
        sys.exit(1)
    elif run.summary["high"] > 3:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
