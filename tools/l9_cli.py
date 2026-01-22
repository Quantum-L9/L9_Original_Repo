#!/usr/bin/env python3
"""
L9 CLI Tool - Security & Technical Debt Management
===================================================

Production-ready CLI tool for proactive security and code quality management.

**Top Frontier AI Lab Quality** - Enterprise-grade developer tooling.

Features:
- ✅ Scan for hardcoded secrets
- ✅ Analyze code quality and complexity
- ✅ Manage technical debt backlog
- ✅ Generate reports and metrics

Version: 1.0.0
GMP: security-remediation-phase1
Author: Top Frontier AI Lab
ADR: readme/adr/0039-l9-cli-tool.md
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "L9 CLI Tool",
    "module_version": "1.0.0",
    "created_by": "L9 Security Remediation",
    "created_at": "2026-01-20T18:00:00Z",
    "updated_at": "2026-01-20T18:00:00Z",
    "layer": "tooling",
    "domain": "cli",
    "module_name": "l9_cli",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import re
from pathlib import Path

import click


@click.group()
def cli():
    """L9 CLI Tool for security and code quality management."""


@cli.command()
@click.option(
    "--path",
    default=".",
    help="Path to scan (default: current directory)",
)
def scan_secrets(path: str):
    """Scan codebase for hardcoded secrets."""
    click.echo(f"🔍 Scanning for hardcoded secrets in {path}...")

    patterns = [
        r'(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*["\']?[\w-]+["\']?',
        r'password\s*=\s*["\'][^"\']+["\']',
        r'api_key\s*=\s*["\'][^"\']+["\']',
    ]

    findings = []
    for py_file in Path(path).rglob("*.py"):
        if ".git" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text()
            for line_num, line in enumerate(content.split("\n"), 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        findings.append((str(py_file), line_num, line.strip()))
        except Exception:
            continue

    if findings:
        click.echo(f"\n⚠️  Found {len(findings)} potential hardcoded secrets:\n")
        for file_path, line_num, line in findings[:10]:
            click.echo(f"  {file_path}:{line_num}")
            click.echo(f"    {line}\n")
        if len(findings) > 10:
            click.echo(f"  ... and {len(findings) - 10} more")
    else:
        click.echo("✅ No hardcoded secrets found!")


@cli.command()
@click.option(
    "--path",
    default=".",
    help="Path to scan (default: current directory)",
)
def scan_quality(path: str):
    """Run code quality and complexity checks."""
    click.echo(f"🔍 Analyzing code quality in {path}...\n")

    # Find large files
    click.echo("📊 Large files (>2000 lines):")
    large_files = []
    for py_file in Path(path).rglob("*.py"):
        if ".git" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            lines = len(py_file.read_text().split("\n"))
            if lines > 2000:
                large_files.append((str(py_file), lines))
        except Exception:
            continue

    large_files.sort(key=lambda x: x[1], reverse=True)
    for file_path, lines in large_files[:5]:
        click.echo(f"  {file_path}: {lines} lines")

    if not large_files:
        click.echo("  ✅ No excessively large files found!")

    # Check for bare except clauses
    click.echo("\n⚠️  Bare except clauses:")
    bare_excepts = []
    for py_file in Path(path).rglob("*.py"):
        if ".git" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text()
            for line_num, line in enumerate(content.split("\n"), 1):
                if re.search(r"^\s*except\s*:\s*$", line):
                    bare_excepts.append((str(py_file), line_num))
        except Exception:
            continue

    if bare_excepts:
        for file_path, line_num in bare_excepts[:5]:
            click.echo(f"  {file_path}:{line_num}")
        if len(bare_excepts) > 5:
            click.echo(f"  ... and {len(bare_excepts) - 5} more")
    else:
        click.echo("  ✅ No bare except clauses found!")


@cli.command()
@click.option(
    "--path",
    default=".",
    help="Path to scan (default: current directory)",
)
def manage_debt(path: str):
    """Analyze and report on technical debt markers."""
    click.echo(f"🔍 Scanning for technical debt markers in {path}...\n")

    markers = ["TODO", "FIXME", "HACK", "XXX"]
    findings = {marker: [] for marker in markers}

    for py_file in Path(path).rglob("*.py"):
        if ".git" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text()
            for line_num, line in enumerate(content.split("\n"), 1):
                for marker in markers:
                    if marker in line:
                        findings[marker].append((str(py_file), line_num, line.strip()))
        except Exception:
            continue

    total = sum(len(v) for v in findings.values())
    click.echo(f"📊 Found {total} technical debt markers:\n")

    for marker, items in findings.items():
        if items:
            click.echo(f"  {marker}: {len(items)}")

    click.echo("\n📝 Top files with technical debt:")
    file_counts = {}
    for marker_items in findings.values():
        for file_path, _, _ in marker_items:
            file_counts[file_path] = file_counts.get(file_path, 0) + 1

    sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
    for file_path, count in sorted_files[:10]:
        click.echo(f"  {file_path}: {count} markers")


if __name__ == "__main__":
    cli()
