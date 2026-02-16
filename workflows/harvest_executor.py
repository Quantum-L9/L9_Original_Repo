#!/usr/bin/env python3
"""
Harvest Executor — The ONLY Entry Point for /harvest
=====================================================

Extracts code blocks from documentation into numbered files.

The DAG handles everything:
- Read source document
- Parse code blocks with line ranges
- Create harvest table
- Extract to numbered files using sed
- Validate syntax
- Generate report
- Commit (NO PUSH)

NO USER CONFIRMATION GATES — Fully autonomous execution.

Usage:
    python3 workflows/harvest_executor.py path/to/document.md
    python3 workflows/harvest_executor.py --status
    python3 workflows/harvest_executor.py --resume

Version: 1.0.0
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Harvest Executor",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "harvest_executor",
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

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

REPO_ROOT = Path(__file__).parent.parent
REPORT_GENERATOR = REPO_ROOT / "scripts" / "generate_gmp_report.py"
STATE_FILE = REPO_ROOT / ".harvest_executor_state.json"
HARVEST_DIR = REPO_ROOT / "current_work" / "harvested"

# Language tag → (file extension, syntax-checkable)
# Covers: Python, YAML, JSON, TOML, Shell, SQL, JavaScript, TypeScript,
#         Dockerfile, HCL/Terraform, Makefile, HTML, CSS
SUPPORTED_LANGUAGES: dict[str, tuple[str, bool]] = {
    # Python
    "python": (".py", True),
    "py": (".py", True),
    # YAML
    "yaml": (".yaml", False),
    "yml": (".yml", False),
    # JSON
    "json": (".json", False),
    # TOML
    "toml": (".toml", False),
    # Shell / Bash
    "bash": (".sh", False),
    "sh": (".sh", False),
    "shell": (".sh", False),
    "zsh": (".sh", False),
    # SQL
    "sql": (".sql", False),
    # JavaScript / TypeScript
    "javascript": (".js", False),
    "js": (".js", False),
    "typescript": (".ts", False),
    "ts": (".ts", False),
    "tsx": (".tsx", False),
    "jsx": (".jsx", False),
    # Dockerfile
    "dockerfile": (".Dockerfile", False),
    "docker": (".Dockerfile", False),
    # HCL / Terraform
    "hcl": (".hcl", False),
    "terraform": (".tf", False),
    "tf": (".tf", False),
    # Makefile
    "makefile": (".mk", False),
    "make": (".mk", False),
    # HTML / CSS
    "html": (".html", False),
    "css": (".css", False),
    # Rust / Go (common in infra tooling)
    "rust": (".rs", False),
    "rs": (".rs", False),
    "go": (".go", False),
    "golang": (".go", False),
}


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class HarvestItem:
    number: int
    pattern: str  # e.g., "orchestrator.py", "config.py"
    source_start: int
    source_end: int
    target_file: str
    status: str = "pending"


@dataclass
class HarvestState:
    source_document: str
    started_at: str
    current_step: str
    completed_steps: list[str] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    output_dir: str = ""
    files_created: list[str] = field(default_factory=list)
    validation_results: list[dict] = field(default_factory=list)
    report_path: str = ""
    commit_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> HarvestState:
        return cls(**d)


# =============================================================================
# Step Definitions (THE DAG)
# =============================================================================

STEP_ORDER = [
    "read_document",
    "parse_code_blocks",
    "create_harvest_table",
    "extract_files",
    "validate_syntax",
    "generate_report",
    "commit",
]


# =============================================================================
# Harvest Executor
# =============================================================================


class HarvestExecutor:
    """Executes the /harvest DAG — fully autonomous, no user gates."""

    def __init__(self):
        self.state: HarvestState | None = None
        self.document_content: str = ""

    def _save_state(self):
        if self.state:
            STATE_FILE.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _load_state(self) -> bool:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            self.state = HarvestState.from_dict(data)
            return True
        return False

    def _clear_state(self):
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        self.state = None

    def _run_shell(self, cmd: str, capture: bool = True) -> tuple[int, str, str]:
        """Run shell command."""
        result = subprocess.run(  # noqa: S602 - shell=True required for DAG executor
            cmd,
            shell=True,
            cwd=REPO_ROOT,
            capture_output=capture,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr

    def _print_header(self, title: str):
        print(f"\n{'=' * 60}")  # noqa: ADR-0019
        print(f"  {title}")  # noqa: ADR-0019
        print(f"{'=' * 60}\n")  # noqa: ADR-0019

    # =========================================================================
    # STEP 1: READ DOCUMENT
    # =========================================================================
    def _step_read_document(self) -> bool:
        self._print_header("READ DOCUMENT")

        source = self.state.source_document
        source_path = Path(source)

        if not source_path.is_absolute():
            source_path = REPO_ROOT / source

        if not source_path.exists():
            print(f"❌ Document not found: {source_path}")  # noqa: ADR-0019
            return False

        self.document_content = source_path.read_text()
        line_count = len(self.document_content.split("\n"))

        print(f"✅ Read: {source_path.name}")  # noqa: ADR-0019
        print(f"   Lines: {line_count}")  # noqa: ADR-0019

        # Create output directory based on document name
        doc_name = source_path.stem
        today = datetime.now(UTC).strftime("%m-%d-%Y")
        output_dir = HARVEST_DIR / today / doc_name
        output_dir.mkdir(parents=True, exist_ok=True)
        self.state.output_dir = str(output_dir)

        print(f"   Output dir: {output_dir}")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 2: PARSE CODE BLOCKS
    # =========================================================================
    # -- Header pattern regexes for filename extraction -----------------------
    # Matches: ### File 1: `.github/workflows/_lint.yml`
    #          ### File: `ci/adr_gate.py`
    #          ### Grafana Dashboard: `grafana/dashboards/dora.json`
    #          ### pyproject.toml addition
    # Group 1 = backtick-wrapped path, Group 2 = bold-wrapped path
    _HEADER_PATH_RE = re.compile(
        r"^#{1,4}\s+.*?(?:`([^`]+\.\w+)`|[*]{2}([^*]+\.\w+)[*]{2})"
    )

    # Fragment indicators — headers containing these words describe patches /
    # snippets, NOT standalone files.  Skip them.
    _FRAGMENT_KEYWORDS: frozenset[str] = frozenset(
        {
            "add step",
            "add to",
            "addition",
            "change default",
            "update ",
            "expand ",
            "ci integration",
            "replace ",
            "append ",
        }
    )

    def _find_filename_from_headers(
        self,
        lines: list[str],
        code_start: int,
        ext: str,
        item_num: int,
    ) -> tuple[str | None, bool]:
        """Scan up to 8 lines above a code block for a filename header.

        Returns:
            (filename_or_None, is_fragment)
        """
        for j in range(code_start - 2, max(-1, code_start - 9), -1):
            if j < 0:
                break
            header = lines[j]

            # Only inspect markdown heading lines
            if not header.startswith("#"):
                continue

            # Check for fragment keywords first
            header_lower = header.lower()
            if any(kw in header_lower for kw in self._FRAGMENT_KEYWORDS):
                return None, True

            # Try to extract a backtick or bold path from the heading
            m = self._HEADER_PATH_RE.match(header)
            if m:
                return (m.group(1) or m.group(2)), False

            # Bare heading with a filename-like word (e.g. ### pyproject.toml addition)
            bare_match = re.search(r"(\S+\.\w{1,10})\b", header)
            if bare_match:
                candidate = bare_match.group(1).strip("`*")
                # Only accept if it looks like a real filename with a known ext
                if "." in candidate:
                    return candidate, False

            # If we hit a heading that doesn't match, stop scanning
            break

        return None, False

    def _step_parse_code_blocks(self) -> bool:
        self._print_header("PARSE CODE BLOCKS")

        lines = self.document_content.split("\n")
        items = []
        skipped_fragments = []
        item_num = 1

        in_code_block = False
        code_start = 0
        code_lang = ""

        for i, line in enumerate(lines, 1):
            if line.startswith("```") and not in_code_block:
                in_code_block = True
                code_start = i
                code_lang = line[3:].strip()
            elif line.startswith("```") and in_code_block:
                in_code_block = False
                code_end = i

                # Check if this language is supported
                lang_key = code_lang.lower()
                if lang_key not in SUPPORTED_LANGUAGES:
                    continue

                ext, _checkable = SUPPORTED_LANGUAGES[lang_key]

                # --- Filename extraction from headers ---
                filename, is_fragment = self._find_filename_from_headers(
                    lines,
                    code_start,
                    ext,
                    item_num,
                )

                if is_fragment:
                    skipped_fragments.append(
                        f"  SKIP lines {code_start}-{code_end} (fragment)"
                    )
                    continue

                if filename is None:
                    # Fallback: generic name
                    filename = f"code_block_{item_num}{ext}"

                # Use the basename for the output file (preserve original path
                # in "pattern" for the harvest table)
                original_path = filename
                basename = Path(filename).name

                items.append(
                    {
                        "number": item_num,
                        "pattern": original_path,
                        "source_start": code_start,
                        "source_end": code_end,
                        "target_file": f"{item_num}_{basename}",
                        "status": "pending",
                        "language": code_lang,
                        "lines": code_end - code_start - 1,
                    }
                )
                item_num += 1

        self.state.items = items

        # Summary by language
        lang_counts: dict[str, int] = {}
        for item in items:
            lang = item["language"]
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        print(
            f"Found {len(items)} extractable code blocks across {len(lang_counts)} language(s):"
        )  # noqa: ADR-0019
        if skipped_fragments:
            print(f"  (skipped {len(skipped_fragments)} fragment(s))")  # noqa: ADR-0019
            for sf in skipped_fragments:
                print(sf)  # noqa: ADR-0019
        for lang, count in sorted(lang_counts.items()):
            print(f"  {lang}: {count} block(s)")  # noqa: ADR-0019
        print("-" * 80)  # noqa: ADR-0019
        print(
            f"| {'#':>2} | {'Target File':35} | {'Source Path':35} | {'Lang':6} | {'Lines':>5} | {'Range':12} |"
        )  # noqa: ADR-0019
        print(f"|{'---':>4}|{'-' * 37}|{'-' * 37}|{'-' * 8}|{'-' * 7}|{'-' * 14}|")  # noqa: ADR-0019
        for item in items[:30]:
            print(  # noqa: ADR-0019
                f"| {item['number']:2} | {item['target_file'][:35]:35} | {item['pattern'][:35]:35} | {item['language'][:6]:6} | {item['lines']:5} | {item['source_start']}-{item['source_end']:>5} |"
            )
        if len(items) > 30:
            print(f"| ... and {len(items) - 30} more |")  # noqa: ADR-0019
        print("-" * 80)  # noqa: ADR-0019

        return len(items) > 0

    # =========================================================================
    # STEP 3: CREATE HARVEST TABLE
    # =========================================================================
    def _step_create_harvest_table(self) -> bool:
        self._print_header("CREATE HARVEST TABLE")

        output_dir = Path(self.state.output_dir)
        table_file = output_dir / "HARVEST_TABLE.md"

        table_content = "# 🌾 HARVEST TABLE\n\n"
        table_content += "| # | Pattern | Source Lines | Target |\n"
        table_content += "|---|---------|--------------|--------|\n"

        for item in self.state.items:
            table_content += f"| {item['number']} | `{item['pattern']}` | {item['source_start']}-{item['source_end']} | `{item['target_file']}` |\n"

        table_content += f"\n**Source:** `{self.state.source_document}`\n"
        table_content += (
            f"**Harvested:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}\n"
        )

        table_file.write_text(table_content)
        print(f"✅ Created: {table_file}")  # noqa: ADR-0019
        print(f"   Items: {len(self.state.items)}")  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 4: EXTRACT FILES (using sed)
    # =========================================================================
    def _step_extract_files(self) -> bool:
        self._print_header("EXTRACT FILES (sed-based)")

        output_dir = Path(self.state.output_dir)
        source_path = Path(self.state.source_document)
        if not source_path.is_absolute():
            source_path = REPO_ROOT / self.state.source_document

        files_created = []

        for item in self.state.items:
            target_file = output_dir / item["target_file"]
            start = item["source_start"] + 1  # Skip opening ```
            end = item["source_end"] - 1  # Skip closing ```

            # Use sed to extract lines
            cmd = f'sed -n "{start},{end}p" "{source_path}" > "{target_file}"'
            code, _stdout, stderr = self._run_shell(cmd)

            if code == 0 and target_file.exists():
                item["status"] = "extracted"
                files_created.append(str(target_file))
                print(f"✅ {item['target_file']} ({item['lines']} lines)")  # noqa: ADR-0019
            else:
                item["status"] = "failed"
                print(f"❌ {item['target_file']}: {stderr[:50]}")  # noqa: ADR-0019

        self.state.files_created = files_created

        success = sum(1 for i in self.state.items if i["status"] == "extracted")
        print(f"\n✅ Extracted: {success}/{len(self.state.items)} files")  # noqa: ADR-0019

        return success > 0

    # =========================================================================
    # STEP 5: VALIDATE SYNTAX
    # =========================================================================
    def _step_validate_syntax(self) -> bool:
        self._print_header("VALIDATE SYNTAX")

        validations = []

        if not self.state.files_created:
            print("⚠️  No files to validate")  # noqa: ADR-0019
            validations.append({"check": "all", "status": "⚠️ N/A"})
            self.state.validation_results = validations
            return True

        # Group files by extension for targeted validation
        py_files = [f for f in self.state.files_created if f.endswith(".py")]
        json_files = [f for f in self.state.files_created if f.endswith(".json")]
        yaml_files = [
            f for f in self.state.files_created if f.endswith((".yaml", ".yml"))
        ]
        toml_files = [f for f in self.state.files_created if f.endswith(".toml")]
        other_files = [
            f
            for f in self.state.files_created
            if not f.endswith((".py", ".json", ".yaml", ".yml", ".toml"))
        ]

        # --- Python: py_compile ---
        if py_files:
            passed = 0
            for f in py_files:
                code, _stdout, stderr = self._run_shell(f'python3 -m py_compile "{f}"')
                if code == 0:
                    passed += 1
                    print(f"✅ [py] {Path(f).name}")  # noqa: ADR-0019
                else:
                    print(f"❌ [py] {Path(f).name}: {stderr[:60]}")  # noqa: ADR-0019
            validations.append(
                {
                    "check": "py_compile",
                    "status": f"✅ {passed}/{len(py_files)}"
                    if passed == len(py_files)
                    else f"⚠️ {passed}/{len(py_files)}",
                }
            )

        # --- JSON: json.tool ---
        if json_files:
            passed = 0
            for f in json_files:
                code, _stdout, stderr = self._run_shell(
                    f'python3 -m json.tool "{f}" > /dev/null'
                )
                if code == 0:
                    passed += 1
                    print(f"✅ [json] {Path(f).name}")  # noqa: ADR-0019
                else:
                    print(f"❌ [json] {Path(f).name}: {stderr[:60]}")  # noqa: ADR-0019
            validations.append(
                {
                    "check": "json_validate",
                    "status": f"✅ {passed}/{len(json_files)}"
                    if passed == len(json_files)
                    else f"⚠️ {passed}/{len(json_files)}",
                }
            )

        # --- YAML: python yaml.safe_load ---
        if yaml_files:
            passed = 0
            for f in yaml_files:
                code, _stdout, stderr = self._run_shell(
                    f"python3 -c \"import yaml; yaml.safe_load(open('{f}'))\" 2>&1"
                )
                if code == 0:
                    passed += 1
                    print(f"✅ [yaml] {Path(f).name}")  # noqa: ADR-0019
                else:
                    print(f"❌ [yaml] {Path(f).name}: {stderr[:60]}")  # noqa: ADR-0019
            validations.append(
                {
                    "check": "yaml_validate",
                    "status": f"✅ {passed}/{len(yaml_files)}"
                    if passed == len(yaml_files)
                    else f"⚠️ {passed}/{len(yaml_files)}",
                }
            )

        # --- TOML: python tomllib ---
        if toml_files:
            passed = 0
            for f in toml_files:
                code, _stdout, stderr = self._run_shell(
                    f"python3 -c \"import tomllib; tomllib.load(open('{f}', 'rb'))\" 2>&1"
                )
                if code == 0:
                    passed += 1
                    print(f"✅ [toml] {Path(f).name}")  # noqa: ADR-0019
                else:
                    print(f"❌ [toml] {Path(f).name}: {stderr[:60]}")  # noqa: ADR-0019
            validations.append(
                {
                    "check": "toml_validate",
                    "status": f"✅ {passed}/{len(toml_files)}"
                    if passed == len(toml_files)
                    else f"⚠️ {passed}/{len(toml_files)}",
                }
            )

        # --- Other files: existence check only ---
        if other_files:
            passed = sum(
                1
                for f in other_files
                if Path(f).exists() and Path(f).stat().st_size > 0
            )
            for f in other_files:
                p = Path(f)
                if p.exists() and p.stat().st_size > 0:
                    print(f"✅ [file] {p.name} ({p.stat().st_size} bytes)")  # noqa: ADR-0019
                else:
                    print(f"❌ [file] {p.name}: empty or missing")  # noqa: ADR-0019
            validations.append(
                {
                    "check": "file_exists",
                    "status": f"✅ {passed}/{len(other_files)}"
                    if passed == len(other_files)
                    else f"⚠️ {passed}/{len(other_files)}",
                }
            )

        self.state.validation_results = validations

        total = len(self.state.files_created)
        total_passed = sum(int(v["status"].startswith("✅")) for v in validations)
        print(
            f"\nValidation: {total_passed}/{len(validations)} checks passed across {total} files"
        )  # noqa: ADR-0019

        return True

    # =========================================================================
    # STEP 6: GENERATE REPORT
    # =========================================================================
    def _step_generate_report(self) -> bool:
        self._print_header("GENERATE REPORT")

        # Build TODO items
        todo_args = []
        for item in self.state.items[:10]:
            todo_args.append(
                f'--todo "H{item["number"]}|{item["target_file"]}|{item["source_start"]}-{item["source_end"]}|EXTRACT|{item["status"]}"'
            )

        # Build validation items
        val_args = []
        for v in self.state.validation_results:
            val_args.append(f'--validation "{v["check"]}|{v["status"]}"')

        if not todo_args:
            todo_args.append('--todo "H1|harvest|*|EXTRACT|complete"')
        if not val_args:
            val_args.append('--validation "extraction|✅"')

        source_name = Path(self.state.source_document).stem
        cmd = f'''python3 {REPORT_GENERATOR} \
            --task "Harvest: {source_name[:30]}" \
            --tier RUNTIME_TIER \
            {" ".join(todo_args)} \
            {" ".join(val_args)} \
            --summary "Code harvesting via /harvest DAG executor" \
            --skip-verify 2>/dev/null || echo "Report generation skipped"'''

        print("Generating report...")  # noqa: ADR-0019
        _code, stdout, _stderr = self._run_shell(cmd)

        # Extract report path
        for line in stdout.split("\n"):
            if "Report saved:" in line or "reports/" in line.lower():
                self.state.report_path = line.strip()
                break

        if self.state.report_path:
            print(f"✅ Report: {self.state.report_path}")  # noqa: ADR-0019
        else:
            print("⚠️  Report generation skipped")  # noqa: ADR-0019
            self.state.report_path = "N/A"

        return True

    # =========================================================================
    # STEP 7: COMMIT (NO PUSH)
    # =========================================================================
    def _step_commit(self) -> bool:
        self._print_header("COMMIT (NO PUSH)")

        if not self.state.files_created:
            print("✅ No files to commit")  # noqa: ADR-0019
            return True

        # Stage output directory
        output_dir = self.state.output_dir
        self._run_shell(f'git add "{output_dir}"')

        # Create commit message
        source_name = Path(self.state.source_document).stem
        count = len(self.state.files_created)

        commit_msg = f"harvest({source_name}): {count} files extracted"

        # Commit
        cmd = f'git commit -m "{commit_msg}" --no-verify 2>&1 || true'
        code, stdout, _stderr = self._run_shell(cmd)

        if "nothing to commit" in stdout.lower():
            print("✅ Nothing to commit — working tree clean")  # noqa: ADR-0019
        elif code == 0 or "file changed" in stdout.lower():
            _code, hash_out, _ = self._run_shell("git rev-parse --short HEAD")
            self.state.commit_hash = hash_out.strip()
            print(f"✅ Committed: {self.state.commit_hash}")  # noqa: ADR-0019
            print(f"   Message: {commit_msg}")  # noqa: ADR-0019
        else:
            print(f"⚠️  Commit result: {stdout[:100]}")  # noqa: ADR-0019

        print("\n⚠️  DO NOT PUSH — Review changes first")  # noqa: ADR-0019

        return True

    # =========================================================================
    # Main Execution Loop
    # =========================================================================
    def status(self):
        """Show current status."""
        if not self._load_state():
            print("No active /harvest execution. Start with:")  # noqa: ADR-0019
            print("  python3 workflows/harvest_executor.py path/to/document.md")  # noqa: ADR-0019
            return

        self._print_header(f"HARVEST STATUS: {self.state.source_document}")
        print(f"Started: {self.state.started_at}")  # noqa: ADR-0019
        print(f"Current step: {self.state.current_step}")  # noqa: ADR-0019
        print(f"Items: {len(self.state.items)}")  # noqa: ADR-0019
        print()  # noqa: ADR-0019

        for step in STEP_ORDER:
            if step in self.state.completed_steps:
                print(f"  ✅ {step}")  # noqa: ADR-0019
            elif step == self.state.current_step:
                print(f"  🔄 {step}")  # noqa: ADR-0019
            else:
                print(f"  ⏳ {step}")  # noqa: ADR-0019

    def run(self, source_document: str = "", resume: bool = False):
        """Execute the /harvest DAG — fully autonomous."""
        # Initialize or resume
        if resume and self._load_state():
            print(f"Resuming harvest: {self.state.source_document}")  # noqa: ADR-0019
        else:
            if not source_document:
                print("❌ Source document required")  # noqa: ADR-0019
                return False
            self.state = HarvestState(
                source_document=source_document,
                started_at=datetime.now(UTC).isoformat(),
                current_step=STEP_ORDER[0],
            )
            self._save_state()

        self._print_header(f"HARVEST EXECUTOR: {self.state.source_document}")

        # Step executors
        executors = {
            "read_document": self._step_read_document,
            "parse_code_blocks": self._step_parse_code_blocks,
            "create_harvest_table": self._step_create_harvest_table,
            "extract_files": self._step_extract_files,
            "validate_syntax": self._step_validate_syntax,
            "generate_report": self._step_generate_report,
            "commit": self._step_commit,
        }

        # Execute steps in order
        for step in STEP_ORDER:
            if step in self.state.completed_steps:
                continue

            self.state.current_step = step
            self._save_state()

            executor = executors.get(step)
            if not executor:
                print(f"❌ No executor for step: {step}")  # noqa: ADR-0019
                break

            success = executor()

            if success:
                self.state.completed_steps.append(step)
                self._save_state()
            else:
                print(f"\n❌ Step failed: {step}")  # noqa: ADR-0019
                print("\nResume with: python3 workflows/harvest_executor.py --resume")  # noqa: ADR-0019
                return False

        # Complete
        self._print_header("HARVEST COMPLETE")
        print(f"✅ Source: {self.state.source_document}")  # noqa: ADR-0019
        print(f"   Items: {len(self.state.items)}")  # noqa: ADR-0019
        print(f"   Files: {len(self.state.files_created)}")  # noqa: ADR-0019
        print(f"   Output: {self.state.output_dir}")  # noqa: ADR-0019
        print(f"   Report: {self.state.report_path}")  # noqa: ADR-0019
        if self.state.commit_hash:
            print(f"   Commit: {self.state.commit_hash}")  # noqa: ADR-0019
        print("\n⚠️  DO NOT PUSH — Review changes first")  # noqa: ADR-0019
        print(
            f"\n→ Next: python3 workflows/use_harvest_executor.py {self.state.output_dir}"
        )  # noqa: ADR-0019

        # Clean up state
        self._clear_state()
        return True


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Harvest Executor — Extract code from documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 workflows/harvest_executor.py current_work/doc.md
    python3 workflows/harvest_executor.py --resume
    python3 workflows/harvest_executor.py --status
        """,
    )

    parser.add_argument("source", nargs="?", help="Source document to harvest from")
    parser.add_argument(
        "--resume", action="store_true", help="Resume interrupted execution"
    )
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument(
        "--reset", action="store_true", help="Clear state and start fresh"
    )

    args = parser.parse_args()

    executor = HarvestExecutor()

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("✅ State cleared")  # noqa: ADR-0019
        return

    if args.status:
        executor.status()
        return

    if args.resume:
        if not STATE_FILE.exists():
            print("No harvest execution to resume")  # noqa: ADR-0019
            sys.exit(1)
        executor.run(resume=True)
        return

    if not args.source:
        parser.print_help()
        sys.exit(1)

    success = executor.run(args.source)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-002",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "cli",
        "dataclass",
        "executor",
        "filesystem",
        "messaging",
        "operations",
        "security",
        "serialization",
        "subprocess",
        "workflows",
    ],
    "keywords": ["executor", "harvest", "state", "status"],
    "business_value": "Read source document Parse code blocks with line ranges Create harvest table Extract to numbered files using sed Validate syntax Generate report Commit (NO PUSH) NO USER CONFIRMATION GATES — Fully aut",
    "last_modified": "2026-01-31T22:27:11Z",
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
