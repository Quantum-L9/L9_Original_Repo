#!/usr/bin/env python3
"""
L9 Perplexity Audit Agent — Automated Tech Debt Pipeline Orchestrator.

Production-grade orchestrator that coordinates Perplexity API calls across
12 audit categories, parses findings, generates reports, and creates
GitHub issues for critical gaps.

Usage:
    python scripts/perplexity_audit_agent.py --mode full
    python scripts/perplexity_audit_agent.py --category security --scope api/
    python scripts/perplexity_audit_agent.py --mode incremental --changed-files api/server.py

Deploy to: scripts/perplexity_audit_agent.py
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

import httpx
import structlog
import yaml

from core.decorators import must_stay_async
from core.observability.instrumentation import trace_span
from scripts.cga_spec_generator import CGASpecGenerator

# ---------------------------------------------------------------------------
# DORA Metadata Block (ADR-0014)
# ---------------------------------------------------------------------------
__dora_meta__ = {
    "component_name": "perplexity_audit_agent",
    "version": "1.0.0",
    "status": "active",
    "owner": "l9-platform",
    "description": "Automated tech debt detection via Perplexity API research agent",
}

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_CONFIG_PATH = "config/perplexity_audit.yaml"
DEFAULT_REPORTS_DIR = "reports/perplexity_audit"


class Severity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Category(str, Enum):
    RELIABILITY = "reliability"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    OBSERVABILITY = "observability"
    DOCUMENTATION = "documentation"
    ADR_COMPLIANCE = "adr_compliance"
    DEPENDENCIES = "dependencies"
    MIGRATIONS = "migrations"
    CI_CD = "ci_cd"
    RUNTIME_SAFETY = "runtime_safety"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    id: str
    category: str
    subcategory: str
    severity: str
    title: str
    file: str
    line_start: int
    line_end: int
    description: str
    impact: str
    adr_violations: list[str] = field(default_factory=list)
    fix_effort_hours: int = 1
    blast_radius: list[str] = field(default_factory=list)
    fix_strategy: str = ""
    code_before: str = ""
    code_after: str = ""
    test_snippet: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuditReport:
    audit_id: str
    timestamp: str
    mode: str
    categories_scanned: list[str]
    total_findings: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    estimated_fix_hours: int
    findings: list[Finding]
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are L9-AUDITOR, a frontier-grade autonomous code quality research agent
operating inside the L9 Secure AI OS repository. Your mission: systematically
identify, classify, and generate actionable remediation plans for ALL technical
debt, security vulnerabilities, architectural anti-patterns, and compliance gaps.

CONSTRAINTS:
- You are bound by 56 Architecture Decision Records (ADRs)
- structlog exclusively (ADR-0019) — standard logging is BANNED
- PacketEnvelope audit trails (ADR-0006) on all data operations
- DORA metadata blocks (ADR-0014) on every Python module
- TYPE_CHECKING imports (ADR-0002) for circular import prevention
- DAG pipeline rules (ADR-0012): validation in intake_node ONLY
- ZERO ambiguous language: no "likely", "probably", "should", "might"
- Output machine-parseable JSON

OUTPUT FORMAT:
Respond with ONLY a JSON array of findings. Each finding object:
{
  "id": "CAT-NNN",
  "category": "string",
  "subcategory": "string",
  "severity": "P0|P1|P2|P3",
  "title": "string",
  "file": "path/to/file.py",
  "line_start": 0,
  "line_end": 0,
  "description": "string",
  "impact": "string",
  "adr_violations": ["ADR-NNNN"],
  "fix_effort_hours": 1,
  "blast_radius": ["file1.py", "file2.py"],
  "fix_strategy": "string",
  "code_before": "string",
  "code_after": "string",
  "test_snippet": "string"
}

SEVERITY MATRIX:
P0: Data loss, security breach, production crash, ADR-0006/0019 violation
P1: Functionality degradation, missing audit trails, ADR violations
P2: Tech debt, code smells, missing tests, documentation gaps
P3: Nice-to-have improvements, style issues
"""

# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

CATEGORY_PROMPTS: dict[str, str] = {
    "reliability": (
        "SCAN: reliability\n"
        "Detect: missing transaction boundaries (ADR-0028), race conditions, "
        "unhandled edge cases, missing error recovery (ADR-0009), resource leaks "
        "(ADR-0033), DAG pipeline violations (ADR-0012).\n"
        "L9 patterns: PacketEnvelope.parent_ids access without length check, "
        "SubstrateService missing transaction context, memory ingestion missing "
        "rollback on partial failure, kernel YAML parsing without schema validation."
    ),
    "security": (
        "SCAN: security\n"
        "Detect: hardcoded secrets (ADR-0038), SQL injection, missing auth "
        "(ADR-0025), insufficient input validation, insecure deserialization, "
        "missing RBAC (ADR-0013), path traversal (ADR-0001).\n"
        "L9 patterns: API routes missing Depends(verify_api_key), Neo4j Cypher "
        "with string interpolation (ADR-0032), unsafe yaml.load, MCP memory "
        "without tenant isolation (ADR-0005)."
    ),
    "performance": (
        "SCAN: performance\n"
        "Detect: N+1 queries, missing DB indexes, O(n^2) algorithms, unbounded "
        "caches (ADR-0027), blocking I/O in async, missing connection pooling, "
        "embedding batch inefficiency (ADR-0029).\n"
        "L9 patterns: sequential embedding lookups, new Neo4j sessions per query, "
        "sequential LLM calls that could be parallel, Redis without pipeline batching."
    ),
    "architecture": (
        "SCAN: architecture\n"
        "Detect: god classes (>500 lines), circular deps (ADR-0002), SOLID "
        "violations, missing abstractions, tight coupling, Protocol violations "
        "(ADR-0026), registry pattern violations (ADR-0004/0022).\n"
        "L9 patterns: memory/ importing api/ (layer violation), services not using "
        "DI (ADR-0025), tool defs not following ADR-0017, kernel configs not "
        "externalized (ADR-0053)."
    ),
    "testing": (
        "SCAN: testing\n"
        "Detect: coverage gaps, missing integration tests, fixture violations "
        "(ADR-0020), missing negative tests, flaky tests, missing property-based "
        "tests for PacketEnvelope.\n"
        "L9 patterns: no tests for substrate_dag.py, missing governance gate tests, "
        "kernel loader not tested with malformed YAML, no circuit breaker tests "
        "(ADR-0009), no WebSocket tests (ADR-0031)."
    ),
    "observability": (
        "SCAN: observability\n"
        "Detect: silent failures (bare except), missing structlog calls (ADR-0019), "
        "standard logging usage (BANNED), missing DORA metadata (ADR-0014), "
        "missing health checks, missing metrics, missing tracing.\n"
        "L9 patterns: five-tier observability completeness, Grafana coverage, "
        "PacketEnvelope operations missing audit emission, DAG nodes missing spans."
    ),
    "documentation": (
        "SCAN: documentation\n"
        "Detect: missing docstrings (ADR-0003), outdated READMEs, missing ADR "
        "compliance, missing API docs, missing runbooks, missing architecture "
        "diagrams.\n"
        "L9 patterns: ADR catalog vs actual files, kernel YAML without inline docs, "
        "tool definitions without usage examples, memory operations without data "
        "flow documentation."
    ),
    "adr_compliance": (
        "SCAN: adr_compliance\n"
        "For EACH of the 56 L9 ADRs (0000-0055), verify: Is the pattern "
        "implemented? Are there violations? Are there files that should follow "
        "the ADR but do not?\n"
        "Priority: ADR-0002 (TYPE_CHECKING), ADR-0006 (PacketEnvelope), "
        "ADR-0012 (DAG validation), ADR-0014 (DORA metadata), ADR-0019 "
        "(structlog), ADR-0028 (transactions), ADR-0038 (secrets)."
    ),
    "dependencies": (
        "SCAN: dependencies\n"
        "Detect: unpinned deps, known CVEs, unused deps, missing deps, "
        "incompatible versions, license compliance issues.\n"
        "Scope: requirements.txt, requirements-docker.txt, pyproject.toml"
    ),
    "migrations": (
        "SCAN: migrations\n"
        "Detect: missing down migrations, data loss risk, sequential apply "
        "violations (ADR-0015), missing indexes, schema drift, missing RLS "
        "policies (ADR-0005).\n"
        "Scope: migrations/"
    ),
    "ci_cd": (
        "SCAN: ci_cd\n"
        "Detect: missing SAST/DAST (ADR-0040), missing test gates, missing "
        "lint gates, secrets in CI, missing smoke tests, missing audit trail.\n"
        "L9 patterns: pre-commit for ADR-0019, bandit config, semgrep rules, "
        "gitleaks config completeness."
    ),
    "runtime_safety": (
        "SCAN: runtime_safety\n"
        "Detect: missing approval gates (ADR-0013), missing circuit breakers "
        "(ADR-0009), missing rate limiting, kernel isolation violations, "
        "feature flag gaps (ADR-0008), missing graceful degradation (ADR-0055).\n"
        "L9 patterns: tool execution without capability scoping (ADR-0034), "
        "missing must_stay_async (ADR-0010), missing lazy init (ADR-0011), "
        "WebSocket lifecycle (ADR-0031)."
    ),
}


# ---------------------------------------------------------------------------
# Pipeline Configuration Loader
# ---------------------------------------------------------------------------


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Load pipeline configuration from YAML."""
    path = Path(config_path)
    if not path.exists():
        log.warning("config_not_found", path=config_path, action="using_defaults")
        return _default_config()
    with open(path) as f:
        config = yaml.safe_load(f)
    log.info("config_loaded", path=config_path)
    return config


def _default_config() -> dict:
    return {
        "perplexity": {
            "model": "sonar-pro",
            "temperature": 0.1,
            "max_tokens": 4096,
            "rate_limit_rpm": 20,
            "retry_max_attempts": 3,
            "timeout_seconds": 120,
        },
        "output": {
            "reports_dir": DEFAULT_REPORTS_DIR,
            "format": ["json", "markdown"],
        },
    }


# ---------------------------------------------------------------------------
# File Scanner
# ---------------------------------------------------------------------------


def scan_files(directories: list[str], repo_root: str = ".") -> list[Path]:
    """Collect Python files from specified directories."""
    root = Path(repo_root)
    python_files: list[Path] = []
    for dir_path in directories:
        target = root / dir_path
        if target.is_file() and target.suffix == ".py":
            python_files.append(target)
        elif target.is_dir():
            python_files.extend(sorted(target.rglob("*.py")))
    log.info("files_scanned", count=len(python_files), directories=directories)
    return python_files


def read_file_content(file_path: Path, max_chars: int = 8000) -> str:
    """Read file content, truncating if necessary."""
    try:
        content = file_path.read_text(encoding="utf-8")
        if len(content) > max_chars:
            content = content[:max_chars] + "\n# ... truncated ..."
        return content
    except (OSError, UnicodeDecodeError) as exc:
        log.error("file_read_error", path=str(file_path), error=str(exc))
        return ""


# ---------------------------------------------------------------------------
# Perplexity API Client
# ---------------------------------------------------------------------------


class PerplexityClient:
    """Async client for Perplexity API with rate limiting, retry, and circuit breaker."""

    def __init__(self, config: dict) -> None:
        self.api_key = os.environ.get("PERPLEXITY_API_KEY", "")
        if not self.api_key:
            msg = "PERPLEXITY_API_KEY environment variable is required"
            raise RuntimeError(msg)

        pplx_config = config.get("perplexity", {})
        self.model = pplx_config.get("model", "sonar-pro")
        self.temperature = pplx_config.get("temperature", 0.1)
        self.max_tokens = pplx_config.get("max_tokens", 4096)
        self.timeout = pplx_config.get("timeout_seconds", 120)
        self.max_retries = pplx_config.get("retry_max_attempts", 3)
        self.rpm_limit = pplx_config.get("rate_limit_rpm", 20)

        # Circuit Breaker state
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0
        self._failure_threshold = 5
        self._recovery_timeout = 60.0

        self._request_times: list[float] = []

        log.info(
            "perplexity_client_init",
            model=self.model,
            temperature=self.temperature,
            rpm_limit=self.rpm_limit,
            failure_threshold=self._failure_threshold,
        )

    @must_stay_async("callers use await")
    async def _check_circuit(self) -> None:
        """Check if circuit is open."""
        if self._circuit_open_until > time.monotonic():
            wait_time = self._circuit_open_until - time.monotonic()
            log.warning("circuit_breaker_open", wait_seconds=round(wait_time, 1))
            raise RuntimeError(f"Circuit breaker open. Retry in {round(wait_time, 1)}s")

        # If it was open but timeout passed, we enter "half-open" state implicitly
        # by allowing the next request.

    def _record_success(self) -> None:
        """Reset failure count on success."""
        if self._consecutive_failures > 0:
            log.info(
                "circuit_breaker_reset", previous_failures=self._consecutive_failures
            )
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0

    def _record_failure(self) -> None:
        """Increment failure count and open circuit if threshold reached."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold:
            self._circuit_open_until = time.monotonic() + self._recovery_timeout
            log.error(
                "circuit_breaker_opened",
                threshold=self._failure_threshold,
                recovery_timeout=self._recovery_timeout,
            )

    async def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        now = time.monotonic()
        self._request_times = [t for t in self._request_times if now - t < 60]
        if len(self._request_times) >= self.rpm_limit:
            wait = 60 - (now - self._request_times[0])
            log.info("rate_limit_wait", seconds=round(wait, 1))
            await asyncio.sleep(wait)
        self._request_times.append(time.monotonic())

    @trace_span("audit_agent.query")
    async def query(
        self, category: str, file_content: str, file_path: str
    ) -> list[dict]:
        """Send audit query to Perplexity and parse findings."""
        await self._check_circuit()
        await self._rate_limit()

        category_prompt = CATEGORY_PROMPTS.get(category, "")
        user_prompt = (
            f"{category_prompt}\n\n"
            f"SCOPE: {file_path}\n"
            f"DEPTH: targeted\n\n"
            f"FILE CONTENT:\n```python\n{file_content}\n```\n\n"
            f"Report ALL {category} gaps. Output ONLY a JSON array of finding objects."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        PERPLEXITY_API_URL,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                content = data["choices"][0]["message"]["content"]
                findings = _parse_findings_json(content)

                self._record_success()

                log.info(
                    "query_success",
                    category=category,
                    file=file_path,
                    findings_count=len(findings),
                    attempt=attempt,
                )
                return findings

            except (httpx.HTTPStatusError, httpx.TimeoutException, KeyError) as exc:
                self._record_failure()
                error_msg = str(exc)
                log.warning(
                    "query_retry",
                    category=category,
                    file=file_path,
                    attempt=attempt,
                    error=error_msg,
                )

                # Emit failure packet to memory substrate
                try:
                    from memory.substrate_service import get_service

                    service = await get_service()
                    await service.record_audit_failure(
                        category=category, error=error_msg, file_path=file_path
                    )
                except Exception as e:
                    log.debug("failed_to_emit_failure_packet", error=str(e))

                if attempt < self.max_retries:
                    # Exponential backoff with jitter
                    wait = (2**attempt) + (time.monotonic() % 1)
                    await asyncio.sleep(wait)

        log.error("query_failed", category=category, file=file_path)
        return []


def _parse_findings_json(content: str) -> list[dict]:
    """Extract JSON array from Perplexity response content."""
    content = content.strip()
    # Handle markdown code blocks
    if "```json" in content:
        try:
            start = content.index("```json") + 7
            end = content.index("```", start)
            content = content[start:end].strip()
        except ValueError:
            # Fallback: if closing backticks missing, take everything from start
            content = content[start:].strip()
    elif "```" in content:
        try:
            start = content.index("```") + 3
            end = content.index("```", start)
            content = content[start:end].strip()
        except ValueError:
            content = content[start:].strip()

    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "findings" in parsed:
            return parsed["findings"]
        return [parsed]
    except json.JSONDecodeError:
        log.warning("json_parse_failed", content_length=len(content))
        return []


# ---------------------------------------------------------------------------
# Report Generator
# ---------------------------------------------------------------------------


class ReportGenerator:
    """Generates JSON and Markdown audit reports."""

    def __init__(self, output_dir: str = DEFAULT_REPORTS_DIR) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, report: AuditReport) -> tuple[Path, Path]:
        """Generate JSON and Markdown reports. Returns (json_path, md_path)."""
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")

        json_path = self.output_dir / f"audit_{timestamp}.json"
        md_path = self.output_dir / f"audit_{timestamp}.md"

        # JSON report
        with open(json_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)

        # Markdown report
        md_content = self._render_markdown(report)
        with open(md_path, "w") as f:
            f.write(md_content)

        log.info("reports_generated", json=str(json_path), markdown=str(md_path))
        return json_path, md_path

    def _render_markdown(self, report: AuditReport) -> str:
        lines = [
            f"# L9 Audit Report — {report.timestamp}",
            "",
            f"**Audit ID:** {report.audit_id}",
            f"**Mode:** {report.mode}",
            f"**Categories:** {', '.join(report.categories_scanned)}",
            f"**Total Findings:** {report.total_findings}",
            f"**Estimated Fix Hours:** {report.estimated_fix_hours}",
            "",
            "## Severity Breakdown",
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ]
        for sev in ["P0", "P1", "P2", "P3"]:
            lines.append(f"| {sev} | {report.by_severity.get(sev, 0)} |")

        lines.extend(
            [
                "",
                "## Category Breakdown",
                "",
                "| Category | Count |",
                "|----------|-------|",
            ]
        )
        for cat, count in sorted(report.by_category.items()):
            lines.append(f"| {cat} | {count} |")

        lines.extend(["", "## Findings", ""])
        for finding in report.findings:
            sev_emoji = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}.get(
                finding.severity, "⚪"
            )
            lines.extend(
                [
                    f"### {sev_emoji} {finding.id}: {finding.title}",
                    "",
                    f"- **Severity:** {finding.severity}",
                    f"- **Category:** {finding.category}/{finding.subcategory}",
                    f"- **File:** `{finding.file}` (L{finding.line_start}-{finding.line_end})",
                    f"- **Fix Effort:** {finding.fix_effort_hours}h",
                    f"- **ADR Violations:** {', '.join(finding.adr_violations) or 'None'}",
                    "",
                    finding.description,
                    "",
                ]
            )
            if finding.code_before:
                lines.extend(
                    [
                        "**Before:**",
                        f"```python\n{finding.code_before}\n```",
                        "",
                        "**After:**",
                        f"```python\n{finding.code_after}\n```",
                        "",
                    ]
                )

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase Pack Generator
# ---------------------------------------------------------------------------


class PhasePackGenerator:
    """Groups findings into implementation phase packs."""

    def __init__(
        self, output_dir: str = "reports/perplexity_audit/phase_packs"
    ) -> None:
        self.output_dir = Path(output_dir)

    def generate(self, findings: list[Finding], min_severity: str = "P1") -> list[Path]:
        """Generate phase packs grouped by category and severity."""
        severity_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        min_rank = severity_order.get(min_severity, 1)

        eligible = [
            f for f in findings if severity_order.get(f.severity, 3) <= min_rank
        ]

        # Group by category
        groups: dict[str, list[Finding]] = {}
        for f in eligible:
            groups.setdefault(f.category, []).append(f)

        pack_dirs: list[Path] = []
        phase_num = 1
        for category in sorted(
            groups,
            key=lambda c: min(severity_order.get(f.severity, 3) for f in groups[c]),
        ):
            pack_dir = self.output_dir / f"phase-{phase_num:02d}-{category}"
            pack_dir.mkdir(parents=True, exist_ok=True)

            # README
            readme = self._build_pack_readme(category, groups[category], phase_num)
            (pack_dir / "README.md").write_text(readme)

            # Findings JSON
            findings_json = [f.to_dict() for f in groups[category]]
            (pack_dir / "findings.json").write_text(json.dumps(findings_json, indent=2))

            # Checklist
            checklist = self._build_checklist(groups[category])
            (pack_dir / "IMPLEMENTATION_CHECKLIST.md").write_text(checklist)

            pack_dirs.append(pack_dir)
            phase_num += 1

        log.info("phase_packs_generated", count=len(pack_dirs))
        return pack_dirs

    def _build_pack_readme(
        self, category: str, findings: list[Finding], phase: int
    ) -> str:
        lines = [
            f"# Phase {phase}: {category.replace('_', ' ').title()} Remediation",
            "",
            f"**Findings:** {len(findings)}",
            f"**Total Fix Effort:** {sum(f.fix_effort_hours for f in findings)}h",
            "",
            "## Findings",
            "",
        ]
        for f in findings:
            lines.extend(
                [
                    f"### {f.id}: {f.title}",
                    f"- Severity: {f.severity}",
                    f"- File: `{f.file}`",
                    f"- Strategy: {f.fix_strategy}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _build_checklist(self, findings: list[Finding]) -> str:
        lines = ["# Implementation Checklist", ""]
        for f in findings:
            lines.append(f"- [ ] {f.id}: {f.title} (`{f.file}`)")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main Pipeline Orchestrator
# ---------------------------------------------------------------------------


class AuditPipeline:
    """Main orchestrator for the Perplexity audit pipeline."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.client = PerplexityClient(config)
        self.reporter = ReportGenerator(
            config.get("output", {}).get("reports_dir", DEFAULT_REPORTS_DIR)
        )
        self.pack_generator = PhasePackGenerator()
        log.info("pipeline_initialized")

    @trace_span("audit_agent.run_full_audit")
    @must_stay_async("callers use await")
    async def run_full_audit(
        self, categories: list[str] | None = None, scope: str | None = None
    ) -> AuditReport:
        """Run full audit across all enabled categories."""
        scan_config = self.config.get("scanning", {}).get("categories", [])
        if categories:
            scan_config = [c for c in scan_config if c.get("name") in categories]
        else:
            scan_config = [c for c in scan_config if c.get("enabled", True)]

        all_findings: list[Finding] = []

        for cat_config in scan_config:
            category = cat_config["name"]
            directories = [scope] if scope else cat_config.get("directories", ["."])

            log.info("scanning_category", category=category, directories=directories)
            files = scan_files(directories)

            for file_path in files:
                content = read_file_content(file_path)
                if not content:
                    continue

                raw_findings = await self.client.query(
                    category=category,
                    file_content=content,
                    file_path=str(file_path),
                )

                for raw in raw_findings:
                    try:
                        finding = Finding(
                            id=raw.get(
                                "id",
                                f"{category[:3].upper()}-{len(all_findings) + 1:03d}",
                            ),
                            category=raw.get("category", category),
                            subcategory=raw.get("subcategory", "general"),
                            severity=raw.get("severity", "P2"),
                            title=raw.get("title", "Untitled finding"),
                            file=raw.get("file", str(file_path)),
                            line_start=raw.get("line_start", 0),
                            line_end=raw.get("line_end", 0),
                            description=raw.get("description", ""),
                            impact=raw.get("impact", ""),
                            adr_violations=raw.get("adr_violations", []),
                            fix_effort_hours=raw.get("fix_effort_hours", 1),
                            blast_radius=raw.get("blast_radius", []),
                            fix_strategy=raw.get("fix_strategy", ""),
                            code_before=raw.get("code_before", ""),
                            code_after=raw.get("code_after", ""),
                            test_snippet=raw.get("test_snippet", ""),
                        )
                        all_findings.append(finding)

                        # Record metric
                        from core.observability.prometheus_exporter import get_exporter

                        exporter = get_exporter()
                        if exporter:
                            exporter.record_tech_debt_finding(
                                severity=finding.severity, category=finding.category
                            )
                    except (KeyError, TypeError) as exc:
                        log.warning("finding_parse_error", error=str(exc), raw=raw)

        # Build report
        audit_id = hashlib.sha256(
            f"{datetime.now(tz=UTC).isoformat()}".encode()
        ).hexdigest()[:12]

        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for f in all_findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
            by_category[f.category] = by_category.get(f.category, 0) + 1

        report = AuditReport(
            audit_id=audit_id,
            timestamp=datetime.now(tz=UTC).isoformat(),
            mode="full",
            categories_scanned=[c["name"] for c in scan_config],
            total_findings=len(all_findings),
            by_severity=by_severity,
            by_category=by_category,
            estimated_fix_hours=sum(f.fix_effort_hours for f in all_findings),
            findings=all_findings,
        )

        # Generate outputs
        json_path, _ = self.reporter.generate(report)
        self.pack_generator.generate(all_findings)

        # Generate CGA Specs for P0/P1 findings
        generated_specs = []
        try:
            cga_gen = CGASpecGenerator()
            generated_specs = cga_gen.process_report(str(json_path))
            log.info(
                "cga_specs_auto_generated",
                report=str(json_path),
                count=len(generated_specs),
            )
        except Exception as e:
            log.error("cga_spec_generation_failed", error=str(e))

        # Programmatic CGA Ingestion (if enabled in config)
        if generated_specs and self.config.get("pipeline", {}).get("auto_fix", False):
            await self.run_codegen(generated_specs)

        log.info(
            "audit_complete",
            audit_id=audit_id,
            total_findings=len(all_findings),
            p0_count=by_severity.get("P0", 0),
            p1_count=by_severity.get("P1", 0),
        )

        return report

    @trace_span("audit_agent.run_codegen")
    async def run_codegen(self, spec_paths: list[Path]) -> None:
        """Invoke CodeGenAgent programmatically on generated specs."""
        from core.agents.codegenagent.codegen_agent import CodeGenAgent

        agent = CodeGenAgent()
        successful = 0
        failed = 0

        for spec_path in spec_paths:
            try:
                log.info("running_codegen_on_spec", path=str(spec_path))
                result = await agent.generate_from_meta(str(spec_path))
                if result.success:
                    successful += 1
                    log.info("codegen_success", spec=str(spec_path))
                else:
                    failed += 1
                    log.error(
                        "codegen_failed", spec=str(spec_path), errors=result.errors
                    )
            except Exception as e:
                failed += 1
                log.error("codegen_exception", spec=str(spec_path), error=str(e))

        log.info(
            "batch_codegen_complete",
            total=len(spec_paths),
            successful=successful,
            failed=failed,
        )

    async def run_incremental_audit(self, changed_files: list[str]) -> AuditReport:
        """Run audit on changed files only (for CI/PR integration)."""
        incremental_categories = ["reliability", "security", "adr_compliance"]

        all_findings: list[Finding] = []
        for file_str in changed_files:
            file_path = Path(file_str)
            if not file_path.exists() or file_path.suffix != ".py":
                continue

            content = read_file_content(file_path)
            if not content:
                continue

            for category in incremental_categories:
                raw_findings = await self.client.query(
                    category=category,
                    file_content=content,
                    file_path=str(file_path),
                )
                for raw in raw_findings:
                    finding = Finding(
                        id=raw.get(
                            "id", f"{category[:3].upper()}-{len(all_findings) + 1:03d}"
                        ),
                        category=raw.get("category", category),
                        subcategory=raw.get("subcategory", "general"),
                        severity=raw.get("severity", "P2"),
                        title=raw.get("title", "Untitled"),
                        file=raw.get("file", str(file_path)),
                        line_start=raw.get("line_start", 0),
                        line_end=raw.get("line_end", 0),
                        description=raw.get("description", ""),
                        impact=raw.get("impact", ""),
                        adr_violations=raw.get("adr_violations", []),
                        fix_effort_hours=raw.get("fix_effort_hours", 1),
                        blast_radius=raw.get("blast_radius", []),
                        fix_strategy=raw.get("fix_strategy", ""),
                        code_before=raw.get("code_before", ""),
                        code_after=raw.get("code_after", ""),
                        test_snippet=raw.get("test_snippet", ""),
                    )
                    all_findings.append(finding)

        audit_id = hashlib.sha256(
            f"inc-{datetime.now(tz=UTC).isoformat()}".encode()
        ).hexdigest()[:12]

        by_severity: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for f in all_findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
            by_category[f.category] = by_category.get(f.category, 0) + 1

        report = AuditReport(
            audit_id=audit_id,
            timestamp=datetime.now(tz=UTC).isoformat(),
            mode="incremental",
            categories_scanned=incremental_categories,
            total_findings=len(all_findings),
            by_severity=by_severity,
            by_category=by_category,
            estimated_fix_hours=sum(f.fix_effort_hours for f in all_findings),
            findings=all_findings,
        )

        self.reporter.generate(report)
        log.info(
            "incremental_audit_complete", audit_id=audit_id, findings=len(all_findings)
        )
        return report


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="L9 Perplexity Audit Agent")
    parser.add_argument(
        "--mode",
        choices=["full", "incremental", "category"],
        default="full",
        help="Audit mode",
    )
    parser.add_argument("--category", type=str, help="Single category to scan")
    parser.add_argument("--scope", type=str, help="Directory or file to scan")
    parser.add_argument(
        "--changed-files", nargs="*", help="Files changed (for incremental mode)"
    )
    parser.add_argument(
        "--config", type=str, default=DEFAULT_CONFIG_PATH, help="Config file path"
    )
    return parser


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    pipeline = AuditPipeline(config)

    if args.mode == "incremental" and args.changed_files:
        report = await pipeline.run_incremental_audit(args.changed_files)
    elif args.mode == "category" and args.category:
        report = await pipeline.run_full_audit(
            categories=[args.category], scope=args.scope
        )
    else:
        report = await pipeline.run_full_audit(scope=args.scope)

    # Exit with error code if P0 findings exist
    p0_count = report.by_severity.get("P0", 0)
    if p0_count > 0:
        log.error("p0_findings_detected", count=p0_count)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
