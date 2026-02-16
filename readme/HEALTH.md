# L9 Codebase Health Dashboard

**Generated:** 2026-02-13 22:42 UTC

## Overall Health

![Type Coverage](https://img.shields.io/badge/Type_Coverage-0.0%-red?style=flat)
![ADR Compliance](https://img.shields.io/badge/ADR_Compliance-0.0%-red?style=flat)
![Spec Drift](https://img.shields.io/badge/Spec_Drift-0.0issues-brightgreen?style=flat)

## 🔴 Overall Status: CRITICAL

**Healthy Metrics:** 1/3 (33%)

## Metrics Breakdown

| Metric | Current | Target | Status | Trend |
|--------|---------|--------|--------|-------|
| **Type Coverage** | 0.0% | 95% | 🔴 CRITICAL | ➡️ Stable |
| **ADR Compliance** | 0.0% | 100% | 🔴 CRITICAL | ➡️ Stable |
| **Spec Drift** | 0.0issues | 0issues | 🟢 HEALTHY | ➡️ Stable |

## 🔴 Critical Action Items

- **Type Coverage:** Gap of 95.0% from target
- **ADR Compliance:** Gap of 100.0% from target

## Quick Commands

```bash
# Update all metrics
make health-dashboard

# Individual reports
make type-coverage          # Update type coverage
make adr-compliance         # Check ADR compliance
make spec-drift             # Check spec-code drift

# Fix specific issues
make type-coverage-update-precommit  # Enable mypy on clean modules
python ci/check_adr_compliance.py    # See ADR violations
python tools/spec_validator/diff_spec_code.py  # See spec drift
```

## About This Dashboard

This dashboard aggregates health metrics from multiple automated checks:

- **Type Coverage:** Percentage of codebase with full mypy type annotations
- **ADR Compliance:** Adherence to Architecture Decision Records
- **Spec Drift:** Alignment between Module-Spec YAML and actual code

All metrics update automatically via CI/CD pipeline and `make` targets.
