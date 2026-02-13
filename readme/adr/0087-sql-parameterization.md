# ADR-0087: SQL Parameterization Standard

**Status:** Accepted
**Date:** 2026-01-31
**Source:** Bug Audit PR #84 (CRITICAL Security Fix)

## Context

SQL injection is a critical security vulnerability. String interpolation (f-strings, .format(), %) in SQL queries allows attackers to execute arbitrary SQL commands.

## Decision

**All SQL queries MUST use parameterized queries. F-strings in SQL are FORBIDDEN.**

### Forbidden Pattern

```python
# BAD - SQL injection vulnerability (CRITICAL)
user_id = request.user_id  # Could be: "'; DROP TABLE users; --"
query = f"SELECT * FROM users WHERE id = '{user_id}'"
await conn.execute(query)
```

### Required Pattern

```python
# GOOD - parameterized query (safe)
query = "SELECT * FROM users WHERE id = $1"
await conn.fetch(query, user_id)

# asyncpg style
query = "UPDATE users SET name = $1 WHERE id = $2"
await conn.execute(query, name, user_id)
```

## Enforcement

- **Semgrep rule:** `l9-no-sql-fstring` in `.semgrep/l9-rules.yaml`
- **CI gate:** ERROR - Blocks merge
- **Scope:** All Python files

## Consequences

- No SQL injection vulnerabilities
- Database driver handles escaping correctly
- Prepared statement performance benefits
