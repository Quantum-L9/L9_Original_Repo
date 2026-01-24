# ============================================================================
# L9 Secure AI OS - Versioning & Dependency Policy
# ============================================================================
# Enterprise-grade policies for versioning, releases, and dependencies
#
# Version: 1.0.0
# Last Updated: 2026-01-22
# Compliance: SOC 2, NIST, OWASP
#
# Contents:
# 1. Semantic Versioning (SemVer)
# 2. Release Process
# 3. Dependency Management
# 4. Security Policy
# 5. Branching Strategy
# ============================================================================

# L9 Versioning & Dependency Policy

This document outlines the policies for versioning, releases, and dependency management for the L9 Secure AI OS. These policies are designed to ensure stability, security, and predictability in our development and release process.

## 1. Semantic Versioning (SemVer)

L9 follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html). The version number is `MAJOR.MINOR.PATCH`.

| Component | Description |
|---|---|
| **MAJOR** | Incompatible API changes (breaking changes) |
| **MINOR** | New features (backward-compatible) |
| **PATCH** | Bug fixes (backward-compatible) |

### Version Management

All version changes are managed through the `scripts/version_manager.py` utility. This ensures consistency across all files (`VERSION`, `pyproject.toml`, `CHANGELOG.md`).

```bash
# Show current version
python scripts/version_manager.py current

# Bump patch version (bug fixes)
python scripts/version_manager.py bump patch

# Bump minor version (new features)
python scripts/version_manager.py bump minor

# Bump major version (breaking changes)
python scripts/version_manager.py bump major --tag
```

## 2. Release Process

Our release process is automated through GitHub Actions to ensure consistency and reliability.

### Release Workflow

1. **Bump Version**: Use the version manager to bump the version and create a git tag.
   ```bash
   python scripts/version_manager.py bump [major|minor|patch] --tag
   ```
2. **Update Changelog**: The version manager automatically creates a new entry in `CHANGELOG.md`. Manually add detailed release notes to this entry.
3. **Commit & Push**: Commit the updated `VERSION`, `pyproject.toml`, and `CHANGELOG.md` files.
   ```bash
   git add VERSION pyproject.toml CHANGELOG.md
   git commit -m "chore: release vX.Y.Z"
   git push && git push --tags
   ```
4. **Automated Release**: The `release.yml` GitHub Actions workflow automatically creates a GitHub release from the pushed tag, using the changelog entry as release notes.

### Release Types

- **Stable Releases**: `v1.0.0`, `v2.1.3`
- **Pre-releases**: `v1.0.0-alpha`, `v1.0.0-beta.1`, `v1.0.0-rc.1`

## 3. Dependency Management

We use [Dependabot](https://docs.github.com/en/code-security/dependabot) for automated dependency management, configured for enterprise-grade security and stability.

### Dependabot Configuration

- **Security Updates**: Daily checks for critical vulnerabilities. PRs are created automatically.
- **Feature Updates**: Weekly checks for minor and patch updates, grouped by ecosystem to reduce noise.
- **Ecosystems Covered**: `pip`, `github-actions`, `docker`, `npm`.

### Auto-Merge Policy

Our `dependabot-auto-merge.yml` workflow automatically merges Dependabot PRs that meet the following criteria:

- **Auto-merged**:
  - Patch updates (if tests pass)
  - Minor updates for dev dependencies (pytest, ruff, etc.)
  - GitHub Actions updates (non-major)
- **Manual Review Required**:
  - Major version updates
  - Updates to security-critical packages (cryptography, sqlalchemy, etc.)

### Required Checks

All Dependabot PRs must pass the following checks before merging:

- **Tests**: `pytest` with 70% minimum coverage
- **Security Scan**: `bandit`
- **Linting**: `ruff` + `mypy`

## 4. Security Policy

Our security policy is designed to be proactive and automated.

| Tool | Purpose |
|---|---|
| **Dependabot** | Automated security patching (daily) |
| **Bandit** | Static security analysis (on every commit) |
| **Gitleaks** | Secret scanning (on every commit) |
| **Ruff** | Security linting (on every commit) |

### Vulnerability Management

- **Critical CVEs**: Patched within 24 hours via Dependabot
- **High CVEs**: Patched within 7 days
- **Medium/Low CVEs**: Patched within 30 days

## 5. Branching Strategy

We follow a simplified GitFlow branching strategy.

| Branch | Purpose |
|---|---|
| `main` | Production-ready code. All PRs are merged into main. |
| `feature/*` | New features or improvements. Branched from main. |
| `fix/*` | Bug fixes. Branched from main. |
| `hotfix/*` | Urgent production fixes. Branched from main. |

### Pull Requests

- All changes must be submitted via pull request.
- All PRs must pass all CI checks before merging.
- All PRs must be reviewed and approved by at least one team member.

---

This policy ensures that L9 remains a secure, stable, and enterprise-grade AI OS.
