#!/usr/bin/env python3
"""
Noqa Debt Eliminator — Tracks and systematically removes # noqa: ADR-XXXX comments.

This script:
1. Scans the codebase for # noqa: ADR-XXXX comments.
2. Categorizes them by ADR type and severity.
3. Generates a "Noqa Debt Report".
4. (Optional) Generates CGA Specs to fix the underlying issues.

Usage:
    python scripts/noqa_debt_eliminator.py --report
    python scripts/noqa_debt_eliminator.py --generate-specs
"""

import argparse
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import structlog
import yaml

# ---------------------------------------------------------------------------
# DORA Metadata Block (ADR-0014)
# ---------------------------------------------------------------------------
__dora_meta__ = {
    "component_name": "noqa_debt_eliminator",
    "version": "1.0.0",
    "status": "active",
    "owner": "l9-platform",
    "description": "Systematic tracking and elimination of ADR noqa debt",
}

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class NoqaItem:
    file: str
    line_number: int
    adr_id: str
    content: str
    reason: str = ""
    severity: str = "P2"  # Default severity


# ---------------------------------------------------------------------------
# Eliminator
# ---------------------------------------------------------------------------


class NoqaDebtEliminator:
    """Tracks and manages noqa debt."""

    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.noqa_pattern = re.compile(r"# noqa: (ADR-\d+)(?:\s*-\s*(.*))?")
        self.severity_map = {
            "ADR-0087": "P0",  # SQL Injection
            "ADR-0038": "P0",  # Secrets
            "ADR-0006": "P1",  # PacketEnvelope
            "ADR-0019": "P2",  # Logging
            "ADR-0014": "P2",  # DORA
            "ADR-0002": "P1",  # Circular imports
            "ADR-0026": "P2",  # Protocols
        }

    def scan(self) -> list[NoqaItem]:
        """Scan codebase for noqa: ADR comments."""
        noqa_items = []
        # We'll use rg if available, otherwise fallback to manual scan
        # For simplicity in this script, we'll do a manual walk
        for py_file in self.repo_root.rglob("*.py"):
            if "node_modules" in str(py_file) or ".venv" in str(py_file):
                continue

            try:
                lines = py_file.read_text(encoding="utf-8").splitlines()
                for i, line in enumerate(lines):
                    match = self.noqa_pattern.search(line)
                    if match:
                        adr_id = match.group(1)
                        reason = match.group(2) or ""
                        severity = self.severity_map.get(adr_id, "P2")

                        noqa_items.append(
                            NoqaItem(
                                file=str(py_file.relative_to(self.repo_root)),
                                line_number=i + 1,
                                adr_id=adr_id,
                                content=line.strip(),
                                reason=reason.strip(),
                                severity=severity,
                            )
                        )
            except Exception as e:
                log.error("file_scan_failed", file=str(py_file), error=str(e))

        log.info("scan_complete", count=len(noqa_items))
        return noqa_items

    def generate_report(
        self, items: list[NoqaItem], output_path: str = "reports/noqa_debt_report.md"
    ):
        """Generate a markdown report of noqa debt."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M EST")

        # Record metrics
        try:
            from core.observability.prometheus_exporter import get_exporter

            exporter = get_exporter()
            if exporter:
                adr_counts = {}
                for item in items:
                    adr_counts[item.adr_id] = adr_counts.get(item.adr_id, 0) + 1
                for adr_id, count in adr_counts.items():
                    exporter.update_noqa_debt(adr_id, count)
        except ImportError:
            pass

        lines = [
            f"# Noqa Debt Report — {timestamp}",
            "",
            f"**Total Noqa Items:** {len(items)}",
            "",
            "## Severity Breakdown",
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ]

        sev_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        for item in items:
            sev_counts[item.severity] = sev_counts.get(item.severity, 0) + 1

        for sev in ["P0", "P1", "P2", "P3"]:
            lines.append(f"| {sev} | {sev_counts[sev]} |")

        lines.extend(
            [
                "",
                "## ADR Breakdown",
                "",
                "| ADR ID | Count | Description |",
                "|--------|-------|-------------|",
            ]
        )

        adr_counts = {}
        for item in items:
            adr_counts[item.adr_id] = adr_counts.get(item.adr_id, 0) + 1

        for adr_id, count in sorted(
            adr_counts.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"| {adr_id} | {count} | |")

        lines.extend(
            [
                "",
                "## Detailed Findings",
                "",
                "| Severity | ADR ID | File | Line | Content |",
                "|----------|--------|------|------|---------|",
            ]
        )

        # Sort by severity then ADR ID
        sorted_items = sorted(items, key=lambda x: (x.severity, x.adr_id))
        for item in sorted_items:
            lines.append(
                f"| {item.severity} | {item.adr_id} | `{item.file}` | {item.line_number} | `{item.content[:50]}...` |"
            )

        path.write_text("\n".join(lines))
        log.info("report_generated", path=str(path))

    def generate_cga_specs(
        self,
        items: list[NoqaItem],
        output_dir: str = "core/agents/codegenagent/patches/noqa_fixes",
    ):
        """Generate CGA Specs to fix noqa violations."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for item in items:
            spec_path = None
            if item.adr_id == "ADR-0019" and "print(" in item.content:
                spec_path = self._generate_adr0019_spec(item, out_dir)
            elif item.adr_id == "ADR-0087" and 'f"' in item.content:
                spec_path = self._generate_adr0087_spec(item, out_dir)

            if spec_path:
                count += 1

        log.info("cga_specs_generated", count=count, dir=str(out_dir))

    def _generate_adr0019_spec(self, item: NoqaItem, out_dir: Path) -> Path | None:
        """Generate a CGA Spec for ADR-0019 (print -> structlog)."""
        # Extract the print statement
        match = re.search(r"print\((.*)\)", item.content)
        if not match:
            return None

        print_args = match.group(1)
        replacement = f'log.info("manual_print_output", content={print_args})'

        return self._write_spec(
            item, replacement, "observability_patch", "ADR-0019", out_dir
        )

    def _generate_adr0087_spec(self, item: NoqaItem, out_dir: Path) -> Path | None:
        """Generate a CGA Spec for ADR-0087 (SQL Injection)."""
        # Very basic heuristic for f-string SQL
        # e.g. f"SELECT * FROM {table} WHERE id = {id}"
        # -> "SELECT * FROM {table} WHERE id = $1", id

        content = item.content
        if 'f"' not in content:
            return None

        # This is a complex transformation for a simple script,
        # so we'll generate a spec that asks CGA to do the heavy lifting
        # by providing the before/after pattern if we can guess it,
        # or just the instruction.

        # For now, let's just mark it for CGA to fix surgically.
        # We'll use a placeholder replacement that CGA should refine.
        replacement = content.replace('f"', '"').replace("{", "$").replace("}", "")
        # Note: This is just a hint for the spec, CGA's LLM will do the real work.

        return self._write_spec(
            item, replacement, "security_patch", "ADR-0087", out_dir
        )

    def _write_spec(
        self,
        item: NoqaItem,
        replacement: str,
        patch_type: str,
        adr_id: str,
        out_dir: Path,
    ) -> Path | None:
        """Helper to write a CGA spec file."""
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        safe_file = item.file.replace("/", "_").replace(".", "_")
        spec_filename = f"{adr_id.lower().replace('-', '')}_fix_{safe_file}_L{item.line_number}_{timestamp}.yaml"
        spec_path = out_dir / spec_filename

        spec_data = {
            "version": "2.4",
            "metadata": {
                "component_id": f"noqa_fix_{adr_id.lower().replace('-', '')}_{timestamp}",
                "component_name": f"Fix {adr_id} Violation",
                "description": f"Remediate {adr_id} in {item.file} at line {item.line_number}",
                "owner": "l9-platform",
                "status": "draft",
                "adr_compliance": [adr_id],
            },
            "patch_definition": {
                "target_file": item.file,
                "patch_type": patch_type,
                "strategy": "surgical",
                "line_range": {"start": item.line_number, "end": item.line_number},
            },
            "implementation": {
                "change_set": [
                    {
                        "action": "replace",
                        "search": item.content,
                        "replace": replacement,
                    }
                ]
            },
        }

        with open(spec_path, "w") as f:
            yaml.dump(spec_data, f, sort_keys=False, indent=2)

        return spec_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Noqa Debt Eliminator")
    parser.add_argument("--report", action="store_true", help="Generate debt report")
    parser.add_argument(
        "--generate-specs", action="store_true", help="Generate CGA fix specs"
    )

    args = parser.parse_args()

    eliminator = NoqaDebtEliminator()
    items = eliminator.scan()

    if args.report:
        eliminator.generate_report(items)

    if args.generate_specs:
        eliminator.generate_cga_specs(items)


if __name__ == "__main__":
    main()
