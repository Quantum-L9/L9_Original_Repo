

- The script `ci_meta_check_and_tests.py` lives in your repo.
- GitHub Actions runs it automatically on events like `push` and `pull_request`.
- If meta contracts fail, the Action fails, and you then use Cursor/codegen to fix the gaps.


## Minimal GitHub Actions workflow for this

Create `.github/workflows/ci.yaml`:

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest  # GitHub-hosted runner
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyyaml

      - name: Meta contract check + tests
        run: |
          python ci_meta_check_and_tests.py
```

Behavior:

- On each PR/push, GitHub Actions spins up a runner and executes this job.
- If required READMEs/tests (from your meta YAMLs) are missing:
    - `ci_meta_check_and_tests.py` writes `meta-gaps.yaml` and exits non‑zero.
    - The GitHub Action turns red and blocks merging.
- After you or Cursor generate the missing files, the next run passes.
