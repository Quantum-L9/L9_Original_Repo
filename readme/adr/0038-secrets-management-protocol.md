# ADR 0038: Secrets Management Protocol

- **Status**: Proposed
- **Date**: 2026-01-20
- **Deciders**: L9 Architecture Team
- **GMP**: security-remediation-phase1

## Context and Problem Statement

The L9 codebase currently has hardcoded secrets and direct access to environment variables scattered throughout various modules. This poses a significant security risk and makes it difficult to manage secrets consistently.

We need a centralized, secure, and extensible way to manage secrets that follows the Dependency Inversion Principle.

## Decision Drivers

- **Security**: Eliminate hardcoded secrets and provide a secure way to manage them.
- **Extensibility**: Support multiple secrets backends (Vault, AWS Secrets Manager, etc.).
- **Testability**: Enable easy mocking of secrets for unit and integration tests.
- **Maintainability**: Centralize secrets management logic and provide a clear, consistent interface.

## Considered Options

1.  **Direct SDK Integration**: Each module integrates directly with the SDK of a specific secrets manager (e.g., `hvac` for Vault).
2.  **Protocol-Based Abstraction**: Define a `SecretsClient` protocol and use dependency injection to provide a concrete implementation at runtime.
3.  **Configuration-Based Approach**: Use a configuration library to load secrets from various sources.

## Decision Outcome

Chosen option: **Protocol-Based Abstraction**, because it provides the best balance of security, extensibility, and testability. It decouples the application logic from the specific secrets management implementation, allowing for easy swapping of backends and simplified testing.

We will create a `SecretsClient` protocol in `core/abstractions` and provide an initial `EnvSecretsClient` implementation for local development.

### Positive Consequences

- Improved security by eliminating hardcoded secrets.
- Increased flexibility to support different secrets management backends.
- Simplified testing by allowing for easy mocking of the `SecretsClient`.
- Centralized and consistent approach to secrets management.

### Negative Consequences

- Requires a one-time effort to refactor existing code to use the new protocol.
- Adds a layer of abstraction, which may slightly increase complexity for new developers.
