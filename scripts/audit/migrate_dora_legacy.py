#!/usr/bin/env python3
"""
DORA Legacy Migration Script
============================
Migrates files with legacy `__dora_block__` to contract-compliant three-block format:
  - __dora_block__ → __dora_meta__ (header) + __dora_footer__ + __l9_trace__

Usage:
    python scripts/audit/migrate_dora_legacy.py --repo /path/to/L9 --dry-run
    python scripts/audit/migrate_dora_legacy.py --repo /path/to/L9 --execute
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Migrate Dora Legacy",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-18T02:10:54Z",
    "updated_at": "2026-01-24T13:02:53Z",
    "layer": "operations",
    "domain": "scripts",
    "module_name": "migrate_dora_legacy",
    "type": "cli",
    "status": "deprecated",
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
import sys
from datetime import datetime, timezone
from pathlib import Path

# ============================================================================
# MIGRATION ENGINE


class DoraLegacyMigrator:
    """Migrates legacy __dora_block__ to three-block format."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.legacy_files: list[str] = []

    def scan_for_legacy(self) -> None:
        """Find all files with legacy __dora_block__."""
        print(f"🔍 Scanning for legacy DORA blocks in: {self.repo_path}")

        for py_file in self.repo_path.rglob("*.py"):
            skip_dirs = [
                "_archived",
                "__pycache__",
                ".venv",
                "venv",
                "node_modules",
                ".git",
            ]
            if any(skip in str(py_file) for skip in skip_dirs):
                continue

            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                if "__dora_block__" in content and "__dora_meta__" not in content:
                    self.legacy_files.append(str(py_file))
            except Exception:
                continue

        print(f"✅ Found {len(self.legacy_files)} files with legacy __dora_block__")

    def _extract_legacy_block(self, content: str) -> dict | None:
        """Extract legacy __dora_block__ data from file content."""
        # Pattern to match the entire  block
        pattern = r"__dora_block__\s*=\s*\{[^}]+\}"

        match = re.search(pattern, content, re.DOTALL)
        if not match:
            return None

        try:
            # Extract just the dict part
            block_str = match.group(0)
            # Extract the dict literal
            dict_start = block_str.index("{")
            dict_str = block_str[dict_start:]

            # Safely evaluate the dict using ast.literal_eval (safer than eval)
            import ast

            return ast.literal_eval(dict_str)
        except Exception as e:
            print(f"⚠️  Could not parse legacy block: {e}")
            return None

    def _remove_legacy_block(self, content: str) -> str:
        """Remove the legacy __dora_block__ section from content."""
        # Remove the entire block including comments
        patterns = [
            # Full block with comments
            r"\n*# ={10,}\n# L9 DORA BLOCK.*?# ={10,}\n# END L9 DORA BLOCK\n# ={10,}\n*",
            # Just the assignment
            r"\n*__dora_block__\s*=\s*\{[^}]+\}\n*",
        ]

        for pattern in patterns:
            content = re.sub(pattern, "\n", content, flags=re.DOTALL)

        return content

    def _format_new_header(self, legacy_data: dict) -> str:
        """Format new __dora_meta__ header from legacy data."""
        json.dumps(legacy_data.get("dependencies", []))

        return """# ============================================================================
"""

    def _format_new_footer(self, legacy_data: dict) -> str:
        """Format new __dora_footer__ from legacy data."""
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return """

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# Extended metadata referenced by header
# ============================================================================
# ============================================================================
"""

    def _format_new_trace(self) -> str:
        """Format new __l9_trace__ block (empty, runtime will populate)."""
        return """

"""

    def _find_header_insertion_point(self, content: str) -> int:
        """Find correct insertion point for header (after shebang, encoding, docstring)."""
        lines = content.split("\n")
        insert_line = 0

        # Skip shebang
        if lines and lines[0].startswith("#!"):
            insert_line = 1

        # Skip encoding
        if len(lines) > insert_line and re.match(r"^#.*coding[:=]", lines[insert_line]):
            insert_line += 1

        # Skip blank lines
        while insert_line < len(lines) and lines[insert_line].strip() == "":
            insert_line += 1

        # Skip module docstring
        if insert_line < len(lines):
            line = lines[insert_line].strip()
            if line.startswith('"""') or line.startswith("'''"):
                quote = line[:3]
                if line.count(quote) >= 2 and len(line) > 6:
                    insert_line += 1
                else:
                    insert_line += 1
                    while insert_line < len(lines) and quote not in lines[insert_line]:
                        insert_line += 1
                    insert_line += 1

        # Skip blank lines after docstring
        while insert_line < len(lines) and lines[insert_line].strip() == "":
            insert_line += 1

        return sum(len(lines[i]) + 1 for i in range(insert_line))

    def migrate_file(self, file_path: str, dry_run: bool = True) -> bool:
        """Migrate a single file from legacy to new format."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Extract legacy data
            legacy_data = self._extract_legacy_block(content)
            if not legacy_data:
                print(f"⚠️  Could not extract legacy data from {file_path}")
                return False

            # Remove legacy block
            content = self._remove_legacy_block(content)

            # Generate new blocks
            header_block = self._format_new_header(legacy_data)
            footer_block = self._format_new_footer(legacy_data)
            trace_block = self._format_new_trace()

            # Insert header at TOP
            insert_pos = self._find_header_insertion_point(content)
            content = content[:insert_pos] + header_block + "\n" + content[insert_pos:]

            # Append footer and trace at END
            content = content.rstrip() + footer_block + trace_block

            if not dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ Migrated {file_path}")
            else:
                print(f"🔍 [DRY RUN] Would migrate {file_path}")

            return True

        except Exception as e:
            print(f"❌ Error migrating {file_path}: {e}")
            return False

    def migrate_all(self, dry_run: bool = True) -> dict:
        """Migrate all legacy files."""
        print(f"\n{'🔍 DRY RUN MODE' if dry_run else '🚀 EXECUTION MODE'}")
        print("=" * 80)

        results = {
            "total_legacy": len(self.legacy_files),
            "migrated": 0,
            "failed": 0,
            "files": [],
        }

        for file_path in self.legacy_files:
            success = self.migrate_file(file_path, dry_run)
            if success:
                results["migrated"] += 1
                results["files"].append({"file": file_path, "status": "migrated"})
            else:
                results["failed"] += 1
                results["files"].append({"file": file_path, "status": "failed"})

        return results

    def generate_report(self, results: dict, output_path: str) -> None:
        """Generate migration report."""
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print("\n📊 MIGRATION REPORT")
        print("=" * 80)
        print(f"Total legacy files: {results['total_legacy']}")
        print(f"✅ Successfully migrated: {results['migrated']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"\n📄 Full report saved to: {output_path}")


# ============================================================================
# YAML/JSON/MD LEGACY MIGRATION


class DoraMultiFormatMigrator:
    """Migrates legacy l9_dora to three-block format in YAML/JSON/MD files."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.legacy_files: dict[str, str] = {}  # file_path -> file_type

    def scan_for_legacy(self) -> None:
        """Find files with legacy DORA format."""
        print("🔍 Scanning for legacy multi-format DORA blocks...")

        # Check YAML files
        for yaml_file in self.repo_path.rglob("*.yaml"):
            if self._is_legacy_yaml(yaml_file):
                self.legacy_files[str(yaml_file)] = "yaml"

        for yml_file in self.repo_path.rglob("*.yml"):
            if self._is_legacy_yaml(yml_file):
                self.legacy_files[str(yml_file)] = "yml"

        # Check JSON files
        for json_file in self.repo_path.rglob("*.json"):
            if self._is_legacy_json(json_file):
                self.legacy_files[str(json_file)] = "json"

        print(
            f"✅ Found {len(self.legacy_files)} multi-format files with legacy blocks"
        )

    def _is_legacy_yaml(self, file_path: Path) -> bool:
        """Check if YAML file has legacy l9_dora format."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            return "l9_dora:" in content and "dora_meta:" not in content
        except Exception:
            return False

    def _is_legacy_json(self, file_path: Path) -> bool:
        """Check if JSON file has legacy _l9_dora format."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            return '"_l9_dora"' in content and '"_dora_meta"' not in content
        except Exception:
            return False

    def migrate_yaml(self, file_path: str, dry_run: bool) -> bool:
        """Migrate YAML file from legacy to new format."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Extract l9_dora section
            legacy_match = re.search(r"l9_dora:\n((?:  .*\n)+)", content)
            if not legacy_match:
                return False

            # Remove old block
            content = re.sub(
                r"\n*# ={10,}\n# L9 DORA BLOCK.*?# ={10,}\n# END L9 DORA BLOCK\n# ={10,}\n*",
                "\n",
                content,
                flags=re.DOTALL,
            )
            content = re.sub(r"\n*l9_dora:\n(?:  .*\n)+# ={10,}\n*", "\n", content)

            # Parse legacy data (simplified - actual implementation would use yaml.safe_load)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Add new three-block format
            new_header = f"""dora_meta:
  component_id: "MIGRATED"
  component_name: "{Path(file_path).stem}"
  module_version: "1.0.0"
  created_at: "{timestamp}"
  created_by: "L9_DORA_Migrator"
  layer: "operations"
  domain: "configuration"
  type: "config"
  status: "active"
  governance_level: "medium"
  compliance_required: true
  audit_trail: true
  purpose: "Migrated configuration"
  dependencies: []

"""

            new_footer = f"""
dora_footer:
  component_id: "MIGRATED"
  security_classification: "internal"
  execution_mode: "on-demand"
  timeout_seconds: 30
  performance_tier: "batch"
  last_modified: "{timestamp}"
  modified_by: "L9_DORA_Migrator"
  change_summary: "Migrated from legacy l9_dora"
# ============================================================================
"""

            new_trace = """

l9_trace:
  trace_id: ""
  task: ""
  timestamp: ""
  patterns_used: []
  graph:
    nodes: []
    edges: []
  inputs: {}
  outputs: {}
  metrics:
    confidence: ""
    errors_detected: []
    stability_score: ""
# ============================================================================
"""

            content = new_header + content.strip() + new_footer + new_trace

            if not dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"✅ Migrated {file_path}")
            else:
                print(f"🔍 [DRY RUN] Would migrate {file_path}")

            return True

        except Exception as e:
            print(f"❌ Error migrating {file_path}: {e}")
            return False

    def migrate_all(self, dry_run: bool = True) -> dict:
        """Migrate all legacy multi-format files."""
        results = {"total": len(self.legacy_files), "migrated": 0, "failed": 0}

        for file_path, file_type in self.legacy_files.items():
            if file_type in ["yaml", "yml"]:
                success = self.migrate_yaml(file_path, dry_run)
            else:
                success = False  # JSON migration would go here

            if success:
                results["migrated"] += 1
            else:
                results["failed"] += 1

        return results


# ============================================================================
# MAIN


def main():
    parser = argparse.ArgumentParser(
        description="Migrate legacy DORA blocks to contract-compliant three-block format"
    )
    parser.add_argument("--repo", required=True, help="Path to L9 repository")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--execute", action="store_true", help="Execute migration")
    parser.add_argument(
        "--python-only", action="store_true", help="Only migrate Python files"
    )
    parser.add_argument(
        "--report", default="dora_migration_report.json", help="Output report path"
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("❌ Error: Must specify either --dry-run or --execute")
        sys.exit(1)

    # Migrate Python files
    print("\n📦 PYTHON FILE MIGRATION")
    print("=" * 80)
    py_migrator = DoraLegacyMigrator(args.repo)
    py_migrator.scan_for_legacy()

    if py_migrator.legacy_files:
        py_results = py_migrator.migrate_all(dry_run=args.dry_run)
        py_migrator.generate_report(py_results, f"python_{args.report}")
    else:
        print("✅ No legacy Python files found")

    # Migrate multi-format files
    if not args.python_only:
        print("\n📦 MULTI-FORMAT FILE MIGRATION")
        print("=" * 80)
        mf_migrator = DoraMultiFormatMigrator(args.repo)
        mf_migrator.scan_for_legacy()

        if mf_migrator.legacy_files:
            mf_results = mf_migrator.migrate_all(dry_run=args.dry_run)
            print(
                f"\n📊 Multi-format: {mf_results['migrated']} migrated, {mf_results['failed']} failed"
            )

    print("\n✅ DORA legacy migration complete!")


if __name__ == "__main__":
    main()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SCR-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "ast",
        "batch-processing",
        "caching",
        "cli",
        "filesystem",
        "metrics",
        "migration",
        "operations",
        "scripts",
        "serialization",
    ],
    "keywords": [
        "all",
        "dora",
        "format",
        "generate",
        "legacy",
        "migrate",
        "migrator",
        "multi",
    ],
    "business_value": "Provides migrate dora legacy components including DoraLegacyMigrator, DoraMultiFormatMigrator",
    "last_modified": "2026-01-24T13:02:53Z",
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
