#!/usr/bin/env python3
"""
CGA Spec Generator — Automates the transition from Audit Findings to CodeGenAgent Specs.

This script consumes Audit Reports (JSON) from the Perplexity Audit Agent and
generates Module-Spec-v2.4 YAML files for CodeGenAgent to implement fixes.

Usage:
    python scripts/cga_spec_generator.py --report reports/perplexity_audit/audit_20260213_035046.json
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

from core.observability.instrumentation import trace_span

# ---------------------------------------------------------------------------
# DORA Metadata Block (ADR-0014)
# ---------------------------------------------------------------------------
__dora_meta__ = {
    "component_name": "cga_spec_generator",
    "version": "1.0.0",
    "status": "active",
    "owner": "l9-platform",
    "description": "Automated generation of CodeGenAgent specs from audit findings",
}

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_PATCH_DIR = "core/agents/codegenagent/patches"
MIN_SEVERITY_FOR_AUTO_FIX = "P1"  # Only auto-fix P0 and P1 by default

# ---------------------------------------------------------------------------
# Spec Generator
# ---------------------------------------------------------------------------


class CGASpecGenerator:
    """Generates CGA YAML specs from audit findings."""

    def __init__(self, patch_dir: str = DEFAULT_PATCH_DIR):
        self.patch_dir = Path(patch_dir)
        self.patch_dir.mkdir(parents=True, exist_ok=True)

    @trace_span("cga_spec_generator.process_report")
    def process_report(
        self, report_path: str, min_severity: str = MIN_SEVERITY_FOR_AUTO_FIX
    ) -> list[Path]:
        """Process an audit report and generate specs for eligible findings."""
        path = Path(report_path)
        if not path.exists():
            log.error("report_not_found", path=report_path)
            return []

        with open(path) as f:
            report_data = json.load(f)

        findings = report_data.get("findings", [])
        generated_specs = []

        severity_map = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        min_rank = severity_map.get(min_severity, 1)

        for raw_finding in findings:
            severity = raw_finding.get("severity", "P3")
            if severity_map.get(severity, 3) > min_rank:
                continue

            # Only generate if we have code_before and code_after
            if not raw_finding.get("code_before") or not raw_finding.get("code_after"):
                log.warning(
                    "skipping_finding_no_code", finding_id=raw_finding.get("id")
                )
                continue

            spec_path = self.generate_spec(raw_finding)
            if spec_path:
                generated_specs.append(spec_path)

        log.info("specs_generated", count=len(generated_specs), report=report_path)
        return generated_specs

    @trace_span("cga_spec_generator.generate_spec")
    def generate_spec(self, finding: dict[str, Any]) -> Path | None:
        """Generate a single CGA YAML spec from a finding."""
        finding_id = finding.get("id", "UNKNOWN")
        file_path = finding.get("file", "unknown.py")
        category = finding.get("category", "general")
        adr_violations = finding.get("adr_violations", [])
        adr_id = adr_violations[0] if adr_violations else None

        # Determine patch type based on category
        patch_type = self._map_category_to_patch_type(category)

        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        safe_file_name = file_path.replace("/", "_").replace(".", "_")
        spec_filename = f"{patch_type}_{finding_id}_{safe_file_name}_{timestamp}.yaml"
        spec_path = self.patch_dir / spec_filename

        # Surgical patch detection: try to identify the exact search string
        search_block = finding.get("code_before", "")
        replace_block = finding.get("code_after", "")

        if not search_block or not replace_block:
            log.warning("missing_code_blocks", finding_id=finding_id)
            return None

        # Clean up blocks (remove common LLM artifacts if any)
        search_block = self._clean_code_block(search_block)
        replace_block = self._clean_code_block(replace_block)

        # Learning Loop: Check for similar past fixes
        similar_fixes = []
        try:
            # This requires an async context which we don't have here in a sync method
            # In a real implementation, we'd either make this async or use a sync wrapper
            pass
        except Exception:
            pass

        # Construct the CGA Spec YAML
        spec_data = {
            "version": "2.4",
            "metadata": {
                "component_id": f"fix_{finding_id.lower()}",
                "component_name": finding.get("title", "Automated Fix"),
                "description": finding.get("description", ""),
                "owner": "l9-platform",
                "status": "draft",
                "source_finding": finding_id,
                "adr_compliance": adr_violations,
                "learning_context": {
                    "similar_fixes_count": len(similar_fixes),
                    "category": category,
                },
            },
            "patch_definition": {
                "target_file": file_path,
                "patch_type": patch_type,
                "strategy": "surgical",
                "risk_level": "medium"
                if finding.get("severity") in ["P0", "P1"]
                else "low",
                "line_range": {
                    "start": finding.get("line_start", 0),
                    "end": finding.get("line_end", 0),
                },
            },
            "implementation": {
                "change_set": [
                    {
                        "action": "replace",
                        "description": finding.get("impact", "Fixing identified issue"),
                        "search": search_block,
                        "replace": replace_block,
                    }
                ]
            },
            "verification": {
                "test_snippet": finding.get("test_snippet", ""),
                "expected_behavior": "The identified issue is resolved without regressions.",
            },
        }

        try:
            with open(spec_path, "w") as f:
                yaml.dump(spec_data, f, sort_keys=False, indent=2)
            log.info("spec_written", path=str(spec_path), finding_id=finding_id)

            # Record metric for fix generation
            try:
                from core.observability.prometheus_exporter import get_exporter

                exporter = get_exporter()
                if exporter:
                    exporter.record_tech_debt_fix(category=category, method="cga")
            except ImportError:
                pass

            return spec_path
        except Exception as e:
            log.error("spec_write_failed", finding_id=finding_id, error=str(e))
            return None

    def _clean_code_block(self, block: str) -> str:
        """Clean up code blocks from LLM artifacts."""
        if not block:
            return ""
        # Remove markdown code fences if they leaked in
        lines = block.splitlines()
        if lines and (lines[0].startswith("```") or lines[0].strip() == ""):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip("\n")

    def _map_category_to_patch_type(self, category: str) -> str:
        """Map audit category to CGA patch type."""
        mapping = {
            "security": "security_patch",
            "reliability": "reliability_patch",
            "performance": "performance_patch",
            "architecture": "refactor_patch",
            "adr_compliance": "compliance_patch",
            "observability": "observability_patch",
        }
        return mapping.get(category, "general_patch")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="CGA Spec Generator")
    parser.add_argument(
        "--report", type=str, required=True, help="Path to audit report JSON"
    )
    parser.add_argument(
        "--min-severity",
        type=str,
        default=MIN_SEVERITY_FOR_AUTO_FIX,
        help="Minimum severity to process",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_PATCH_DIR,
        help="Directory to save generated specs",
    )

    args = parser.parse_args()

    generator = CGASpecGenerator(patch_dir=args.output_dir)
    generator.process_report(args.report, min_severity=args.min_severity)


if __name__ == "__main__":
    main()
