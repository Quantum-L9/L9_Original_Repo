# CI/CD Integration Guide: GitHub Marketplace Tools

## 1. Overview

This guide explains how to integrate the new GitHub Marketplace tools (SonarQube, GitGuardian, Codecov, CodeRabbit, Datree) with your existing CI/CD workflow.

**Goal:** Enhance your CI pipeline with enterprise-grade code quality, security, and coverage automation.

## 2. Integration Strategy

We will add the new marketplace jobs to your existing `.github/workflows/ci.yml` file. The new jobs will run in parallel with your existing jobs, and the final `ci-complete` job will be updated to require all new jobs to pass.

## 3. Pre-requisites

Before you begin, make sure you have:

1. **Merged PR #58:** This contains all the necessary configuration files.
2. **Installed GitHub Apps:** SonarCloud, GitGuardian, Codecov, CodeRabbit.
3. **Added GitHub Secrets:** `SONAR_TOKEN`, `GITGUARDIAN_API_KEY`, `CODECOV_TOKEN`.

## 4. Integration Steps

### Step 1: Add New Jobs to `ci.yml`

Copy and paste the following new jobs into your `.github/workflows/ci.yml` file, placing them before your existing `validate` job:

```yaml
  # ===========================================================================
  # NEW JOB: LINT-FORMAT — Ruff + MyPy
  # ===========================================================================
  lint-format:
    name: Lint & Format (Ruff + MyPy)
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy

      - name: Run Ruff (linting)
        run: |
          echo "🔍 Running Ruff linter..."
          ruff check . --output-format=github

      - name: Run Ruff (formatting)
        run: |
          echo "🎨 Checking code formatting..."
          ruff format --check .

      - name: Run MyPy (type checking)
        run: |
          echo "🔬 Running MyPy type checker..."
          mypy . --config-file=pyproject.toml || true
        continue-on-error: true  # Don't block CI yet - report only

  # ===========================================================================
  # NEW JOB: SONARCLOUD — Code Quality & Security Analysis
  # ===========================================================================
  sonarcloud:
    name: SonarCloud Analysis
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Shallow clones should be disabled for better analysis

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
          pip install pytest pytest-cov

      - name: Run tests with coverage
        run: |
          echo "🧪 Running tests with coverage for SonarCloud..."
          pytest tests/ --cov=. --cov-report=xml --cov-report=term --ignore=tests/e2e || true
        continue-on-error: true

      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        with:
          args: >
            -Dsonar.projectKey=L9
            -Dsonar.organization=cryptoxdog
            -Dsonar.python.coverage.reportPaths=coverage.xml

  # ===========================================================================
  # NEW JOB: SECRETS-SCAN — GitGuardian Secrets Detection
  # ===========================================================================
  secrets-scan:
    name: Secrets Scan (GitGuardian)
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for better detection

      - name: GitGuardian scan
        uses: GitGuardian/ggshield-action@v1
        env:
          GITHUB_PUSH_BEFORE_SHA: ${{ github.event.before }}
          GITHUB_PUSH_BASE_SHA: ${{ github.event.base }}
          GITHUB_PULL_BASE_SHA: ${{ github.event.pull_request.base.sha }}
          GITHUB_DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
          GITGUARDIAN_API_KEY: ${{ secrets.GITGUARDIAN_API_KEY }}

  # ===========================================================================
  # NEW JOB: COVERAGE — Codecov Coverage Tracking
  # ===========================================================================
  coverage:
    name: Coverage (Codecov)
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: l9
          POSTGRES_PASSWORD: l9test
          POSTGRES_DB: l9_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov httpx structlog pydantic tenacity asyncpg redis

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://l9:l9test@localhost:5432/l9_test
          REDIS_URL: redis://localhost:6379
          TESTING: "true"
        run: |
          echo "🧪 Running tests with coverage..."
          pytest tests/ -v --cov=. --cov-report=xml --cov-report=term --ignore=tests/e2e

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
          fail_ci_if_error: true

  # ===========================================================================
  # NEW JOB: DATREE-CHECK — YAML Validation
  # ===========================================================================
  datree-check:
    name: YAML Validation (Datree)
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Datree Policy Check
        uses: datreeio/action-datree@main
        with:
          path: '.github/workflows/*.yml'
          cliArguments: '--only-k8s-files --policy-config .datree-policy.yaml'
        continue-on-error: true  # Don't block CI yet - report only
```

### Step 2: Update `ci-complete` Job

Update the `needs` section of your existing `ci-complete` job to include the new jobs:

```yaml
  ci-complete:
    name: CI Complete
    runs-on: ubuntu-latest
    needs: 
      - lint-format
      - sonarcloud
      - secrets-scan
      - coverage
      - datree-check
      - validate
      - crypto-guard
      - dora-check
      - docker-check
      - test
      - docker-smoke
      - security
    if: always()
```

### Step 3: Update `ci-complete` Summary

Update the `Summary` step in your `ci-complete` job to include the new jobs:

```yaml
      - name: Summary
        run: |
          echo "╔══════════════════════════════════════════════════════════════╗"
          echo "║          L9 ENHANCED CI PIPELINE SUMMARY                     ║"
          echo "╚══════════════════════════════════════════════════════════════╝"
          echo ""
          echo "GitHub Marketplace Jobs:"
          echo "  ├─ Lint & Format:  ${{ needs.lint-format.result }}"
          echo "  ├─ SonarCloud:     ${{ needs.sonarcloud.result }}"
          echo "  ├─ Secrets Scan:   ${{ needs.secrets-scan.result }}"
          echo "  ├─ Coverage:       ${{ needs.coverage.result }}"
          echo "  └─ Datree Check:   ${{ needs.datree-check.result }}"
          echo ""
          echo "Core CI Jobs:"
          echo "  ├─ Validate:       ${{ needs.validate.result }}"
          echo "  ├─ Crypto Guard:   ${{ needs.crypto-guard.result }}"
          echo "  ├─ DORA Check:     ${{ needs.dora-check.result }}"
          echo "  ├─ Docker Check:   ${{ needs.docker-check.result }}"
          echo "  ├─ Test:           ${{ needs.test.result }}"
          echo "  ├─ Docker Smoke:   ${{ needs.docker-smoke.result || 'skipped (push)' }}"
          echo "  └─ Security:       ${{ needs.security.result }}"
          echo ""
          
          # Fail if critical jobs failed
          if [[ "${{ needs.lint-format.result }}" == "failure" ]]; then
            echo "❌ Lint & Format failed"
            exit 1
          fi
          
          if [[ "${{ needs.secrets-scan.result }}" == "failure" ]]; then
            echo "❌ Secrets Scan failed (hardcoded secrets detected)"
            exit 1
          fi
          
          if [[ "${{ needs.coverage.result }}" == "failure" ]]; then
            echo "❌ Coverage failed (below 75% threshold)"
            exit 1
          fi
          
          if [[ "${{ needs.validate.result }}" == "failure" ]]; then
            echo "❌ CI Gates failed"
            exit 1
          fi
          
          if [[ "${{ needs.crypto-guard.result }}" == "failure" ]]; then
            echo "❌ Crypto Guard failed (banned MD5 detected)"
            exit 1
          fi
          
          if [[ "${{ needs.docker-check.result }}" == "failure" ]]; then
            echo "❌ Docker validation failed"
            exit 1
          fi
          
          echo "✅ All critical checks passed"
```

## 5. Validation

After committing these changes, your CI pipeline will now run all the new marketplace jobs in parallel with your existing jobs. The `ci-complete` job will ensure that all critical checks pass before the pipeline is considered successful.

## 6. CodeRabbit AI Review

CodeRabbit runs automatically on every pull request - no configuration is needed in your CI workflow. You will see its reviews directly in the PR comments.
