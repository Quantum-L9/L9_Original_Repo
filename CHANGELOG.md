# Changelog

All notable changes to L9 Secure AI OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Enterprise-grade Dependabot configuration with daily security updates
- Automated dependency testing and auto-merge workflow
- Semantic versioning system with version manager utility
- Automated GitHub release creation from version tags
- Comprehensive exception hierarchy (L9Error and 20+ specific types)
- Exception handling refactoring guide

### Changed
- Enhanced Dependabot with intelligent dependency grouping
- Optimized Ruff configuration for Python 3.12
- Improved Mypy, Pytest, and coverage configurations
- Updated EditorConfig for consistent code formatting

### Fixed
- 10 representative exception catches across critical files
- Timeout configuration (300s → 30s)
- Mypy strictness settings (reverted to permissive)

## [1.1.0] - 2026-01-22

### Added
- Memory routing fixes with native LangGraph execution
- Conditional routing for memory packets
- Duplicate packet detection
- Improved error handling in memory substrate

### Changed
- SubstrateDAG now uses native LangGraph execution
- Memory ingestion pipeline optimized

### Fixed
- Manual DAG execution replaced with proper LangGraph orchestration
- Memory routing issues resolved

## [1.0.0] - 2025-12-09

### Added
- Initial release of L9 Secure AI OS
- 10-Kernel Identity Stack architecture
- FastAPI-based REST API
- LangGraph agent execution engine
- Memory substrate with PostgreSQL + pgvector
- Neo4j world model integration
- Comprehensive testing suite

### Security
- Gitleaks secret scanning
- Bandit security analysis
- Pre-commit hooks for security checks

---

## Version Numbering

L9 follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes (breaking changes)
- **MINOR** version: New features (backward-compatible)
- **PATCH** version: Bug fixes (backward-compatible)

### Version Management

Use the version manager utility:

```bash
# Show current version
python scripts/version_manager.py current

# Bump patch version (bug fixes)
python scripts/version_manager.py bump patch

# Bump minor version (new features)
python scripts/version_manager.py bump minor

# Bump major version (breaking changes)
python scripts/version_manager.py bump major --tag

# Validate version consistency
python scripts/version_manager.py validate
```

## Release Process

1. **Bump version**: `python scripts/version_manager.py bump [major|minor|patch] --tag`
2. **Review changelog**: Edit this file to add detailed release notes
3. **Commit changes**: `git add VERSION pyproject.toml CHANGELOG.md && git commit -m "chore: release vX.Y.Z"`
4. **Push with tags**: `git push && git push --tags`
5. **GitHub Release**: Automatically created by CI/CD workflow

## Categories

### Added
New features or capabilities

### Changed
Changes to existing functionality

### Deprecated
Features that will be removed in future versions

### Removed
Features that have been removed

### Fixed
Bug fixes

### Security
Security-related changes or fixes
