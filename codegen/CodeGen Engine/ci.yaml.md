<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# So this CI check is wanna run through GitHub actions not locally

Yes, you’d typically run this CI check inside GitHub Actions, not manually on your machine (except when debugging).

## How it fits

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
<span style="display:none">[^1]</span>

<div align="center">⁂</div>

[^1]: https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_28a5acba-b23e-4b01-9740-de9323d1c6c6/c3ad8924-7fa9-4b7f-afea-1b63dc9e1b8e/can-u-act-as-a-tutor-and-expla-kGNhGCDyQDWqsE9k2ujtjw.md

