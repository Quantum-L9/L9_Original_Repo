#!/usr/bin/env python3
"""
Codebase Health Dashboard Generator

Aggregates metrics from multiple sources to generate unified health dashboard.

Sources:
- Type coverage (reports/type_coverage/coverage.json)
- ADR compliance (reports/adr-compliance.json)
- Spec drift (reports/spec_drift/drift_report.json)
- Test coverage (if available)

Usage:
    python tools/health_dashboard/generate_dashboard.py
    python tools/health_dashboard/generate_dashboard.py --output readme/HEALTH.md
    python tools/health_dashboard/generate_dashboard.py --help

Part of GMP Phase 2 - Enhancement 5
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import structlog

logger = structlog.get_logger()


@dataclass
class HealthMetric:
    """Single health metric."""

    name: str
    value: float
    status: Literal["healthy", "warning", "critical"]
    trend: Literal["improving", "stable", "declining"]
    target: float
    unit: str


def load_json_report(path: Path) -> dict:
    """Load JSON report file safely.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON or empty dict
    """
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        logger.warning("report_load_failed", path=str(path), error=str(e))
    return {}


def calculate_type_coverage_metric(repo_root: Path) -> HealthMetric:
    """Calculate type coverage health metric.

    Args:
        repo_root: Repository root

    Returns:
        Type coverage metric
    """
    report = load_json_report(repo_root / "reports" / "type_coverage" / "coverage.json")

    coverage = report.get("overall_coverage", 0)

    if coverage >= 80:
        status = "healthy"
    elif coverage >= 50:
        status = "warning"
    else:
        status = "critical"

    return HealthMetric(
        name="Type Coverage",
        value=coverage,
        status=status,
        trend="stable",  # Would need historical data
        target=95.0,
        unit="%",
    )


def calculate_adr_compliance_metric(repo_root: Path) -> HealthMetric:
    """Calculate ADR compliance health metric.

    Args:
        repo_root: Repository root

    Returns:
        ADR compliance metric
    """
    report = load_json_report(repo_root / "reports" / "adr-compliance.json")

    compliance = report.get("overall_compliance", 0)

    if compliance >= 90:
        status = "healthy"
    elif compliance >= 70:
        status = "warning"
    else:
        status = "critical"

    return HealthMetric(
        name="ADR Compliance",
        value=compliance,
        status=status,
        trend="stable",
        target=100.0,
        unit="%",
    )


def calculate_spec_drift_metric(repo_root: Path) -> HealthMetric:
    """Calculate spec-code drift metric.

    Args:
        repo_root: Repository root

    Returns:
        Spec drift metric
    """
    report = load_json_report(
        repo_root / "reports" / "spec_drift" / "drift_report.json"
    )

    critical = report.get("by_severity", {}).get("critical", 0)
    total = report.get("total_discrepancies", 0)

    if critical == 0:
        status = "healthy"
    elif critical <= 3:
        status = "warning"
    else:
        status = "critical"

    return HealthMetric(
        name="Spec Drift",
        value=float(total),
        status=status,
        trend="stable",
        target=0.0,
        unit="issues",
    )


def generate_badge_url(metric: HealthMetric) -> str:
    """Generate shields.io badge URL for metric.

    Args:
        metric: Health metric

    Returns:
        Badge URL
    """
    color_map = {"healthy": "brightgreen", "warning": "yellow", "critical": "red"}
    color = color_map[metric.status]

    label = metric.name.replace(" ", "_")
    value = f"{metric.value:.1f}{metric.unit}"

    return f"https://img.shields.io/badge/{label}-{value}-{color}?style=flat"


def generate_dashboard_markdown(metrics: list[HealthMetric], repo_root: Path) -> str:
    """Generate Markdown dashboard.

    Args:
        metrics: List of health metrics
        repo_root: Repository root

    Returns:
        Formatted Markdown
    """
    lines = [
        "# L9 Codebase Health Dashboard",
        "",
        f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Overall Health",
        "",
    ]

    # Badges
    for metric in metrics:
        badge_url = generate_badge_url(metric)
        lines.append(f"![{metric.name}]({badge_url})")
    lines.append("")

    # Status summary
    healthy_count = sum(1 for m in metrics if m.status == "healthy")
    total_count = len(metrics)
    health_pct = (healthy_count / total_count * 100) if total_count > 0 else 0

    if health_pct >= 80:
        overall_emoji = "🟢"
        overall_status = "HEALTHY"
    elif health_pct >= 50:
        overall_emoji = "🟡"
        overall_status = "NEEDS ATTENTION"
    else:
        overall_emoji = "🔴"
        overall_status = "CRITICAL"

    lines.extend(
        [
            f"## {overall_emoji} Overall Status: {overall_status}",
            "",
            f"**Healthy Metrics:** {healthy_count}/{total_count} ({health_pct:.0f}%)",
            "",
        ]
    )

    # Detailed metrics
    lines.extend(
        [
            "## Metrics Breakdown",
            "",
            "| Metric | Current | Target | Status | Trend |",
            "|--------|---------|--------|--------|-------|",
        ]
    )

    for metric in metrics:
        status_emoji = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}[
            metric.status
        ]

        trend_emoji = {"improving": "📈", "stable": "➡️", "declining": "📉"}[
            metric.trend
        ]

        lines.append(
            f"| **{metric.name}** | {metric.value:.1f}{metric.unit} | "
            f"{metric.target:.0f}{metric.unit} | {status_emoji} {metric.status.upper()} | "
            f"{trend_emoji} {metric.trend.capitalize()} |"
        )

    lines.append("")

    # Action items
    critical_metrics = [m for m in metrics if m.status == "critical"]
    warning_metrics = [m for m in metrics if m.status == "warning"]

    if critical_metrics:
        lines.extend(["## 🔴 Critical Action Items", ""])
        for metric in critical_metrics:
            gap = metric.target - metric.value if metric.unit == "%" else metric.value
            lines.append(
                f"- **{metric.name}:** Gap of {abs(gap):.1f}{metric.unit} from target"
            )
        lines.append("")

    if warning_metrics:
        lines.extend(["## 🟡 Improvement Opportunities", ""])
        for metric in warning_metrics:
            gap = metric.target - metric.value if metric.unit == "%" else metric.value
            lines.append(
                f"- **{metric.name}:** {abs(gap):.1f}{metric.unit} from target"
            )
        lines.append("")

    # Quick commands
    lines.extend(
        [
            "## Quick Commands",
            "",
            "```bash",
            "# Update all metrics",
            "make health-dashboard",
            "",
            "# Individual reports",
            "make type-coverage          # Update type coverage",
            "make adr-compliance         # Check ADR compliance",
            "make spec-drift             # Check spec-code drift",
            "",
            "# Fix specific issues",
            "make type-coverage-update-precommit  # Enable mypy on clean modules",
            "python ci/check_adr_compliance.py    # See ADR violations",
            "python tools/spec_validator/diff_spec_code.py  # See spec drift",
            "```",
            "",
        ]
    )

    # Historical note
    lines.extend(
        [
            "## About This Dashboard",
            "",
            "This dashboard aggregates health metrics from multiple automated checks:",
            "",
            "- **Type Coverage:** Percentage of codebase with full mypy type annotations",
            "- **ADR Compliance:** Adherence to Architecture Decision Records",
            "- **Spec Drift:** Alignment between Module-Spec YAML and actual code",
            "",
            "All metrics update automatically via CI/CD pipeline and `make` targets.",
            "",
        ]
    )

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate codebase health dashboard")
    parser.add_argument(
        "--repo-root", type=Path, default=Path("."), help="Repository root directory"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file (default: readme/HEALTH.md)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output_path = args.output or (repo_root / "readme" / "HEALTH.md")

    logger.info("generating_health_dashboard", repo=str(repo_root))

    # Calculate metrics
    metrics = [
        calculate_type_coverage_metric(repo_root),
        calculate_adr_compliance_metric(repo_root),
        calculate_spec_drift_metric(repo_root),
    ]

    # Generate dashboard
    markdown = generate_dashboard_markdown(metrics, repo_root)

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown)

    logger.info("dashboard_written", path=str(output_path))

    # Print summary
    critical = sum(1 for m in metrics if m.status == "critical")
    warning = sum(1 for m in metrics if m.status == "warning")
    healthy = sum(1 for m in metrics if m.status == "healthy")

    print("\n✅ Health Dashboard Generated")
    print(f"   Output: {output_path}")
    print(f"   Status: {healthy} healthy, {warning} warning, {critical} critical")

    if critical > 0:
        print(f"\n⚠️  Action required on {critical} critical metric(s)")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
