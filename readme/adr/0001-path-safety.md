# ADR 0001: Sandboxed Path Resolution for Research Factory

## Status

Accepted

## Context

Research Factory endpoints and the CLI accept user-controlled output paths. This
creates path traversal and sandbox escape risk across POSIX and Windows.

## Decision

Introduce `core.security.path_safety` to normalize and resolve user paths under
a configured sandbox root. All extraction output paths are resolved via
`safe_resolve_path`, with traversal, absolute/UNC/drive prefixes, NULs, and
surrogate code points rejected. Symlink resolution is blocked by default.

## Consequences

- API and CLI outputs are constrained to `L9_RESEARCH_FACTORY_BASE_DIR` (default
  `~/.l9/generated`).
- Attempts to escape the sandbox return HTTP 400 (API) or exit with a non-zero
  status (CLI).
