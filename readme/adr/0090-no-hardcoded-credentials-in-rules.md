# ADR 0090: No Hardcoded Credentials in Cursor Rules

- **Status**: Accepted
- **Date**: 2026-01-31
- **Deciders**: Igor
- **GMP**: Immediate enforcement

## Context and Problem Statement

Cursor rule files (`.cursor/rules/*.mdc`) are documentation that AI agents read to understand the codebase. These files were containing **hardcoded credentials** including:

- Database passwords in connection strings
- API keys
- Service credentials

This violates fundamental security principles:

1. Credentials become stale and cause auth failures
2. Credentials are visible in git history
3. AI agents may leak credentials in responses
4. Rules are synced across machines, spreading credentials

## Decision Drivers

- **Security**: Never store credentials in documentation or rule files
- **Maintainability**: Credentials change; documentation should not
- **Consistency**: Aligns with ADR-0038 (Secrets Management Protocol)
- **CI Enforcement**: Must be automatically checked

## Decision Outcome

**MANDATORY**: All cursor rule files MUST use environment variable references instead of hardcoded values.

### Prohibited Patterns

```bash
# ❌ NEVER - Hardcoded credentials (DO NOT DO THIS)
C1_POSTGRES_DSN=postgresql://user:password@host:5432/db  # hardcoded password!
NEO4J_PASSWORD=myS3cretP@ss  # hardcoded!
API_KEY=sk_live_abc123...  # hardcoded!
```

### Required Patterns

```bash
# ✅ CORRECT - Environment variable references
C1_POSTGRES_DSN=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${C1_HOST}:30432/l9_memory
NEO4J_PASSWORD=${NEO4J_PASSWORD}
API_KEY=${L9_API_KEY}

# ✅ CORRECT - Instructions to use .env
# Credentials loaded from .env file - see .env.example
```

### CI Enforcement

`ci/check_no_hardcoded_credentials.py` runs on every PR and blocks merge if:

- Password patterns found in `.cursor/rules/`
- Connection strings with literal passwords
- API key patterns (sk*, pk*, api_key=literal)

### Exceptions

None. Rule files NEVER contain real credentials.

## Consequences

### Positive

- Credentials cannot leak through rule files
- Rules remain accurate across credential rotations
- AI agents cannot accidentally expose secrets
- Consistent with secrets management protocol

### Negative

- Developers must check .env for actual values
- Slightly more work to document connection examples

## Compliance

- **ADR-0038**: Secrets Management Protocol (extends to documentation)
- **GMP-129**: Memory Pipeline Governance (credentials in substrate configs)

## References

- `.env.example` - Template with placeholder values
- `config/secrets.py` - Runtime secrets loading
- `ci/check_no_hardcoded_credentials.py` - CI enforcement
