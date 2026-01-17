# === DORA WORKFLOW COMMAND ===
# command: do-init
# version: 1.0.0
# purpose: Initialize DORA-aligned project structure
# prefix: do-
# created: 2025-12-07

name: do-init
description: Initialize DORA-aligned project structure with state tracking, CI/CD, and Docker setup

# `/do-init` - Initialize DORA Project Structure

**Run once at project start to create the complete DORA-aligned infrastructure.**

---

## What This Command Creates

```
project-root/
├── .dora/
│   ├── state.yaml          ← Tracks project phase, completed steps
│   ├── metrics.yaml        ← Deployment count, lead times, failures
│   └── session-log.md      ← Running log of what got done
├── .github/
│   └── workflows/
│       └── ci-cd.yaml      ← GitHub Actions pipeline
├── docker-compose.yaml     ← Local dev stack
├── Dockerfile              ← Container definition
├── pyproject.toml          ← Python config (ruff, pytest)
├── .pre-commit-config.yaml ← Auto-checks before commits
└── tests/
    └── test_example.py     ← Starter test
```

---

## Execution Instructions

When user runs `/do-init`, perform these actions:

### 1. Create `.dora/` Directory Structure

Create `.dora/state.yaml`:
```yaml
# DORA Project State
# Auto-updated by do-* commands - DO NOT EDIT MANUALLY

project:
  name: ""  # Set by init
  created: ""  # ISO timestamp
  
phase:
  current: 1  # 1-10 per DORA Checklist
  name: "Foundation and Planning"
  
progress:
  completed_items: []
  current_task: null
  blockers: []
  
session:
  last_active: null
  total_sessions: 0
```

Create `.dora/metrics.yaml`:
```yaml
# DORA Metrics Tracker
# Auto-updated by do-* commands - DO NOT EDIT MANUALLY

deployments:
  total: 0
  successful: 0
  failed: 0
  timestamps: []

lead_time:
  # commit_to_deploy times in minutes
  samples: []
  average: null

change_failure_rate:
  # failed / total
  calculated: null

mttr:
  # Mean time to recovery in minutes
  incidents: []
  average: null

last_updated: null
```

Create `.dora/session-log.md`:
```markdown
# Session Log

Auto-appended by `/do-end` command.

---

```

### 2. Create `.github/workflows/ci-cd.yaml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff pytest
          pip install -e . || true
          
      - name: Lint with ruff
        run: ruff check .
        
      - name: Run tests
        run: pytest tests/ -v
        
  build:
    needs: lint-and-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: docker build -t app:${{ github.sha }} .
        
      - name: Tag as latest
        if: github.ref == 'refs/heads/main'
        run: docker tag app:${{ github.sha }} app:latest
```

### 3. Create `docker-compose.yaml`

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - ENVIRONMENT=development
    restart: unless-stopped

  # Uncomment when ready for observability
  # mlflow:
  #   image: ghcr.io/mlflow/mlflow:v2.9.2
  #   ports:
  #     - "5000:5000"
  #   command: mlflow server --host 0.0.0.0
```

### 4. Create `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for caching
COPY pyproject.toml .
COPY README.md .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Default command
CMD ["python", "-m", "src.main"]
```

### 5. Create `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "my-project"
version = "0.1.0"
description = "DORA-aligned project"
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = [
    "ruff>=0.1.0",
    "pytest>=7.0.0",
    "pre-commit>=3.0.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
```

### 6. Create `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

### 7. Create `tests/test_example.py`

```python
"""Example test file - replace with real tests."""


def test_placeholder():
    """Placeholder test to verify pytest works."""
    assert True


def test_import_works():
    """Verify basic imports work."""
    import sys
    assert sys.version_info >= (3, 11)
```

### 8. Create `src/__init__.py` and `src/main.py`

`src/__init__.py`:
```python
"""Main source package."""
```

`src/main.py`:
```python
"""Application entry point."""


def main():
    print("Application started")


if __name__ == "__main__":
    main()
```

---

## Post-Init Actions

After creating files:

1. Update `.dora/state.yaml` with:
   - `project.name`: Ask user or derive from folder name
   - `project.created`: Current ISO timestamp
   - `session.last_active`: Current ISO timestamp
   - `session.total_sessions`: 1

2. Output confirmation:

```
✅ DORA Project Initialized

Created:
  • .dora/state.yaml (project state tracking)
  • .dora/metrics.yaml (DORA metrics)
  • .dora/session-log.md (session history)
  • .github/workflows/ci-cd.yaml (CI/CD pipeline)
  • docker-compose.yaml (local dev stack)
  • Dockerfile (container definition)
  • pyproject.toml (Python config)
  • .pre-commit-config.yaml (pre-commit hooks)
  • tests/test_example.py (starter test)
  • src/__init__.py, src/main.py (app skeleton)

Next steps:
  1. Run: pip install -e ".[dev]"
  2. Run: pre-commit install
  3. Run: /do-status to see your current state
  4. Run: /do-next to get your first task
```

---

## Usage

```
/do-init
/do-init my-project-name
```

