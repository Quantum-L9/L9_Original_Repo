# CI Workflow Changes for Security Scanning

This document contains the changes to be applied to `.github/workflows/ci.yml` to enable SAST and code quality scanning.

## Changes Required

### 1. Update Metadata (Lines 8, 20-22, 29-31)

```yaml
# updated_at: "2026-01-20T18:30:00Z"

# Version: 1.2.0
# Created: 2026-01-06
# Updated: 2026-01-20 — Add SAST and code quality scanning

#   5. security      - Dependency vulnerability scan
#   6. sast          - Static Application Security Testing (Bandit)
#   7. code-quality  - Code quality and complexity analysis (Radon)
```

### 2. Add Two New Jobs (Append to end of file)

```yaml

  # ===========================================================================
  # JOB 6: SAST — Static Application Security Testing
  # ===========================================================================
  sast:
    name: Security Scan (SAST)
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install Bandit
        run: |
          python -m pip install --upgrade pip
          pip install bandit[toml]

      - name: Run Bandit SAST Scan
        run: |
          echo "🔍 Running SAST scan with Bandit..."
          bandit -r . -f json -o bandit-report.json -ll || true
          bandit -r . -f screen -ll

      - name: Upload Bandit Report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: bandit-security-report
          path: bandit-report.json

  # ===========================================================================
  # JOB 7: CODE QUALITY — Complexity and Quality Analysis
  # ===========================================================================
  code-quality:
    name: Code Quality Analysis
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install Radon
        run: |
          python -m pip install --upgrade pip
          pip install radon

      - name: Run Complexity Analysis
        run: |
          echo "📊 Running code complexity analysis..."
          radon cc . -a -s -i venv --json > radon-cc-report.json || true
          radon cc . -a -s -i venv

      - name: Run Maintainability Index
        run: |
          echo "📊 Running maintainability index..."
          radon mi . -s -i venv --json > radon-mi-report.json || true
          radon mi . -s -i venv

      - name: Upload Radon Reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: radon-quality-reports
          path: |
            radon-cc-report.json
            radon-mi-report.json
```

## Manual Application Instructions

1. Open `.github/workflows/ci.yml` in your editor
2. Update the metadata lines as shown in section 1
3. Append the two new jobs to the end of the file as shown in section 2
4. Commit and push the changes

## Benefits

- **SAST Job**: Runs Bandit to detect security vulnerabilities in Python code
- **Code Quality Job**: Runs Radon to analyze code complexity and maintainability
- **Artifacts**: Both jobs upload JSON reports for historical tracking
- **Non-Blocking**: Both jobs use `|| true` to prevent CI failures on warnings
