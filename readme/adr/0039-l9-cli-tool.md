# ADR 0039: L9 CLI Tool

- **Status**: Proposed
- **Date**: 2026-01-20
- **Deciders**: L9 Architecture Team
- **GMP**: security-remediation-phase1

## Context and Problem Statement

Developers currently lack a standardized, easy-to-use tool for proactively identifying security vulnerabilities and code quality issues on their local machines. This leads to issues being discovered late in the development cycle, often in CI/CD pipelines.

We need a command-line tool that empowers developers to run these checks locally, improving code quality and security from the start.

## Decision Drivers

- **Developer Experience**: Provide a simple, intuitive tool for local development.
- **Proactive Prevention**: Catch issues early, before they are committed or pushed.
- **Consistency**: Ensure all developers are using the same set of checks and standards.
- **Automation**: Automate common security and code quality tasks.

## Considered Options

1.  **Shell Scripts**: Create a collection of shell scripts to run the various checks.
2.  **Makefile**: Use a Makefile to define targets for running the checks.
3.  **Dedicated CLI Tool**: Build a dedicated CLI tool using a framework like Click or Typer.

## Decision Outcome

Chosen option: **Dedicated CLI Tool**, because it provides the best developer experience and is the most extensible. A CLI tool can provide a more user-friendly interface, better help and documentation, and can be easily extended with new commands and features.

We will create a `l9-cli` tool using Click that provides commands for scanning secrets, analyzing code quality, and managing technical debt.

### Positive Consequences

- Improved developer productivity and experience.
- Early detection of security and code quality issues.
- Consistent application of standards across the team.
- Easy to extend with new commands and features.

### Negative Consequences

- Requires initial effort to build and maintain the CLI tool.
- Adds another tool for developers to learn and use.
