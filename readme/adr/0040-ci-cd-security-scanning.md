# ADR 0040: CI/CD Security Scanning

- **Status**: Proposed
- **Date**: 2026-01-20
- **Deciders**: L9 Architecture Team
- **GMP**: security-remediation-phase2

## Context and Problem Statement

The current CI/CD pipeline lacks automated security and code quality scanning. This means that vulnerabilities and code quality issues are often discovered late in the development cycle, leading to rework and increased risk.

We need to integrate automated security and code quality scanning into the CI/CD pipeline to provide early feedback and prevent issues from reaching production.

## Decision Drivers

- **Security**: Proactively identify and remediate security vulnerabilities.
- **Code Quality**: Enforce consistent code quality standards and prevent technical debt.
- **Developer Productivity**: Provide fast feedback to developers and reduce rework.
- **Automation**: Automate security and code quality checks to ensure consistency and repeatability.

## Considered Options

1.  **Third-Party SaaS**: Use a third-party SaaS solution for security and code quality scanning.
2.  **Open-Source Tools**: Integrate open-source tools like Bandit and Radon into the CI/CD pipeline.
3.  **Manual Code Reviews**: Rely on manual code reviews to identify security and code quality issues.

## Decision Outcome

Chosen option: **Open-Source Tools**, because it provides a cost-effective, flexible, and customizable solution that can be easily integrated into our existing CI/CD pipeline.

We will add two new jobs to the `ci.yml` workflow:
- **`sast`**: Runs Bandit for Static Application Security Testing.
- **`code-quality`**: Runs Radon for code complexity and maintainability analysis.

### Positive Consequences

- Early detection of security vulnerabilities and code quality issues.
- Improved code quality and maintainability.
- Increased developer productivity and reduced rework.
- Consistent application of security and code quality standards.

### Negative Consequences

- Requires initial effort to integrate and configure the tools.
- May produce false positives that need to be triaged and managed.
- Adds to the overall CI/CD pipeline execution time.
