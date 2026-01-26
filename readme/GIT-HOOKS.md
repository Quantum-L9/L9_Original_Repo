# L9 Git Hooks

Production-ready git hooks for frontier AI lab-grade code quality.

## Quick Start

```bash
# Install hooks (one-time, auto-run by deploy.sh)
bash scripts/install_git_hooks.sh
```

## Hooks Overview

| Hook         | Trigger       | Purpose                         |
| ------------ | ------------- | ------------------------------- |
| `pre-commit` | Before commit | Secret scan, format, lint       |
| `post-merge` | After pull    | Deps, migrations, kernel reload |
| `pre-push`   | Before push   | Smoke tests, large file block   |

## Pre-Commit (5 Checks)

Runs before every `git commit`:

1. **Secret Scanning** — gitleaks blocks API keys, tokens, passwords
2. **Auto-Format** — `ruff format` (auto-stages formatted files)
3. **Lint** — `ruff check --fix` (auto-fixes, re-stages)
4. **Type Check** — `mypy` (optional, non-blocking)
5. **Forbidden Patterns** — Blocks `breakpoint()`, `import pdb`, etc.

## Post-Merge (8 Checks)

Runs after every `git pull`:

1. **Env Sync** — Detects `.env.example` changes, shows missing vars
2. **Dependencies** — Auto `pip install` if requirements.txt changed
3. **Migrations** — Auto-runs via `memory.migration_runner` if new .sql
4. **Docker** — Prompts rebuild if docker-compose.yml changed
5. **Kernel Reload** — Triggers `/api/kernels/reload` if kernels/ changed
6. **Audit Cache** — Clears `.audit_cache/` if audit scripts changed
7. **Pre-commit Config** — Reinstalls hooks if `.pre-commit-config.yaml` changed
8. **Repo Index** — Regenerates index in background

## Pre-Push (4 Checks)

Runs before every `git push`:

1. **Smoke Tests** — Runs `tests/smoke_test.py`, blocks on failure
2. **Large File Block** — Rejects files >10MB (suggests Git LFS)
3. **Schema Validation** — Validates `memory/memory_spec_v3.0.yaml`
4. **Breaking Changes** — Detects `substrate_models.py` changes

## Dependencies

```bash
# Python (in requirements.txt)
pip install ruff mypy pytest

# Secret scanning (optional, macOS)
brew install gitleaks

# Secret scanning (optional, Linux)
wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.21.2_linux_x64.tar.gz
tar -xzf gitleaks_*.tar.gz && sudo mv gitleaks /usr/local/bin/
```

## Bypass (Emergency Only)

```bash
git commit --no-verify  # Skip pre-commit
git push --no-verify    # Skip pre-push
```

## Files

```
scripts/
├── hooks/
│   ├── pre-commit     # 147 lines
│   ├── post-merge     # 196 lines
│   └── pre-push       # 121 lines
└── install_git_hooks.sh  # Installer
```

## Auto-Install on Deploy

The `scripts/deployment/10X_Deploy_Script.sh` automatically installs hooks on VPS at **Phase 3.5** (after git pull, before docker rebuild).

```bash
# Deploy (hooks auto-installed)
./scripts/deployment/10X_Deploy_Script.sh "commit message"
```

**VPS needs:**

- Python tools: Installed via `requirements.txt`
- gitleaks: NOT needed (VPS only pulls, doesn't commit)

## Related

- `scripts/deployment/10X_Deploy_Script.sh` — Main deployment script
- `ops/setup-git-hooks.sh` — Wrapper that calls installer
- `reports/GMP_Report_GMP-72-Git-Hooks-Integration.md` — Implementation report
