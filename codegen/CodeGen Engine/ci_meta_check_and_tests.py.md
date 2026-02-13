<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Make me the ci script that runs the test using these yamls

Below is a minimal CI helper script that:

1. Scans for the meta YAML files described earlier.
2. Checks for required docs/tests.
3. Fails if anything is missing.
4. Runs pytest if meta checks pass.

You can call it from GitHub Actions, GitLab CI, etc.

```python
#!/usr/bin/env python
"""
ci_meta_check_and_tests.py

Purpose:
- Enforce presence of docs/tests defined in *.meta.yaml.
- Run pytest only if meta contracts are satisfied.

Usage:
  python ci_meta_check_and_tests.py
"""

import sys
import subprocess
from pathlib import Path

import yaml


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_root_readme_meta(meta_path: Path, gaps: list):
    meta = load_yaml(meta_path)
    target = meta.get("location", "README.md")
    target_path = (meta_path.parent / target).resolve()
    if not target_path.is_file():
        gaps.append(
            {
                "kind": "missing_doc",
                "meta": str(meta_path),
                "target": str(target_path),
            }
        )


def check_subsystem_readme_meta(meta_path: Path, gaps: list):
    meta = load_yaml(meta_path)
    target = meta.get("location", "README.md")
    target_path = (Path(meta.get("location")).resolve()
                   if Path(meta.get("location")).is_absolute()
                   else (meta_path.parent / target).resolve())
    if not target_path.is_file():
        gaps.append(
            {
                "kind": "missing_doc",
                "meta": str(meta_path),
                "target": str(target_path),
            }
        )


def check_docs_meta(meta_path: Path, gaps: list):
    meta = load_yaml(meta_path)
    target = meta.get("location")
    if not target:
        return
    target_path = (meta_path.parent.parent / target).resolve() if target.startswith("docs/") else Path(target).resolve()
    if not target_path.is_file():
        gaps.append(
            {
                "kind": "missing_doc",
                "meta": str(meta_path),
                "target": str(target_path),
            }
        )


def check_unit_tests_meta(meta_path: Path, gaps: list):
    meta = load_yaml(meta_path)
    modules = meta.get("module_policies", [])
    for module in modules:
        test_file = module.get("file")
        if not test_file:
            continue
        test_path = Path(test_file).resolve()
        if not test_path.is_file():
            gaps.append(
                {
                    "kind": "missing_test_file",
                    "meta": str(meta_path),
                    "target": str(test_path),
                    "module": module.get("module"),
                }
            )


def check_subsystem_tests_meta(meta_path: Path, gaps: list):
    meta = load_yaml(meta_path)
    unit_modules = meta.get("unit_tests", {}).get("modules", [])
    for module in unit_modules:
        test_file = module.get("file")
        if not test_file:
            continue
        test_path = Path(test_file).resolve()
        if not test_path.is_file():
            gaps.append(
                {
                    "kind": "missing_test_file",
                    "meta": str(meta_path),
                    "target": str(test_path),
                    "module": module.get("path"),
                }
            )


def scan_meta_files(repo_root: Path):
    return sorted(repo_root.rglob("*.meta.yaml"))


def main():
    repo_root = Path(__file__).resolve().parent
    gaps = []

    meta_files = scan_meta_files(repo_root)

    for meta_path in meta_files:
        # Decide handler based on type field
        try:
            meta = load_yaml(meta_path)
        except Exception as exc:
            gaps.append(
                {
                    "kind": "invalid_meta_yaml",
                    "meta": str(meta_path),
                    "error": str(exc),
                }
            )
            continue

        meta_type = meta.get("type")

        if meta_type == "root_readme":
            check_root_readme_meta(meta_path, gaps)
        elif meta_type in {"subsystem_readme", "component_readme"}:
            check_subsystem_readme_meta(meta_path, gaps)
        elif meta_type in {"doc_architecture", "doc_ai_collaboration", "test_strategy",
                           "test_unit_spec", "test_integration_spec", "test_e2e_spec"}:
            check_docs_meta(meta_path, gaps)
        elif meta_type == "test_unit_spec":
            # Optional: enforce unit test files from global unit spec
            check_unit_tests_meta(meta_path, gaps)
        elif meta_type == "subsystem_test_spec":
            check_subsystem_tests_meta(meta_path, gaps)
        # Unknown meta types are ignored by default; you can tighten this later.

    if gaps:
        print("META CONTRACT VIOLATIONS DETECTED:")
        for gap in gaps:
            print(f"- {gap['kind']}: meta={gap['meta']} target={gap.get('target')} module={gap.get('module')}")
        # Optionally write a machine-readable gap report for Cursor:
        gap_report_path = repo_root / "meta-gaps.yaml"
        with gap_report_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump({"gaps": gaps}, f, sort_keys=False)
        print(f"\nGap report written to: {gap_report_path}")
        sys.exit(1)

    # If no gaps: run tests
    print("Meta contracts satisfied. Running pytest...")
    result = subprocess.run(["pytest"], check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
```

Use this script by:

- Adding it to your repo, e.g. `ci_meta_check_and_tests.py`.
- Ensuring `pyyaml` is installed in your CI environment.
- Wiring it into CI, for example in GitHub Actions:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt pyyaml
      - run: python ci_meta_check_and_tests.py
```

This way:

- If any meta-defined README or test file is missing, CI fails and writes `meta-gaps.yaml` for your Cursor codegen job to consume.
- If all meta contracts are satisfied, CI proceeds to run pytest.
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_28a5acba-b23e-4b01-9740-de9323d1c6c6/c3ad8924-7fa9-4b7f-afea-1b63dc9e1b8e/can-u-act-as-a-tutor-and-expla-kGNhGCDyQDWqsE9k2ujtjw.md

