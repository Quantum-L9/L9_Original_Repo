# ADR 0065: Cursor ADR Enforcement Rules

- **Status**: Accepted
- **Date**: 2026-01-24
- **Deciders**: L9 Architecture Team
- **GMP**: governance-hardening

## Context and Problem Statement

Cursor IDE agents need consistent enforcement of ADR decisions during code generation and modification. Without explicit rules, agents may generate code that violates established patterns.

## Decision Drivers

- **Consistency**: Ensure all generated code follows ADR patterns
- **Automation**: Enable automatic enforcement without manual review
- **Clarity**: Provide clear, actionable rules for each ADR

## Decision Outcome

Define explicit enforcement rules for each accepted ADR that Cursor agents must follow.

## Enforcement Rules

### Bootstrap (ADR-0035)
- ALWAYS read `readme/adr/README.md` and all **Status: Accepted** ADRs at session start.
- ALWAYS apply ADR constraints to any code you propose.

### ADR-0001: Sandboxed Path Resolution
- ❌ NEVER use `os.path` or absolute paths like `/tmp/...`.
- ✅ ALWAYS use `pathlib.Path` and relatives from `Path(__file__).parent`.

### ADR-0002: Circular Import Prevention
- ❌ NEVER create circular imports between modules.
- ✅ Use `typing.TYPE_CHECKING` for type-only imports.
- ✅ Use lazy imports inside functions for cross-module dependencies.

### ADR-0003: Documentation Standards
- ✅ Add module-level docstrings to every non-test module.
- ✅ Add Google-style docstrings to all public classes and functions.

### ADR-0006: PacketEnvelope Audit Trail
- ✅ When constructing `PacketEnvelope`, ALWAYS pass `audit_context` with:
  - `user_id`, `session_id`, `request_id`.

### ADR-0010: must_stay_async Decorator
- ❌ NEVER call blocking I/O (e.g., `requests`, `time.sleep`, sync DB drivers) inside `async` functions.
- ✅ Use async equivalents (aiohttp, aiofiles, async DB drivers, `asyncio.sleep`).

### ADR-0022: Registry Pattern
- ❌ NEVER implement manual singletons with `__new__` and `_instance`.
- ✅ Use the central Registry pattern instead.

### ADR-0026: Protocol-Based Abstractions
- ✅ Prefer `typing.Protocol` for structural interfaces.
- When using `abc.ABC`, consider whether Protocol is more appropriate.

### ADR-0055: Fail-Loudly vs Silent Failure
- ❌ NEVER swallow exceptions with `except Exception: pass` or bare `except:`.
- ✅ Log with structlog (`logger.exception`) and either re-raise or return error packets.

## Positive Consequences

- Consistent code generation across all Cursor sessions
- Reduced need for manual ADR compliance review
- Faster development with built-in guardrails

## Negative Consequences

- Cursor agents must load additional context at session start
- May slow down initial response time
