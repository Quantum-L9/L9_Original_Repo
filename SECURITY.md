# Security Policy

## Path Sandbox Policy (Research Factory)

The Research Factory API and CLI restrict filesystem writes to a configured
sandbox root. User-controlled `output_dir` values are resolved under this root,
with traversal, absolute path, and symlink escapes rejected.

### Configuration

- `L9_RESEARCH_FACTORY_BASE_DIR`: absolute path to the sandbox root.
- Default (if unset): `~/.l9/generated`.

### Migration Notes

- `output_dir` values for `/factory/extract` and `/factory/extract-file`, and
  `--output` for the CLI, are now interpreted relative to the sandbox root.
- To preserve an existing absolute output path, set
  `L9_RESEARCH_FACTORY_BASE_DIR` to that root and pass a relative `output_dir`.

### Guarantees

- Denies `..`, absolute paths, UNC/drive prefixes, mixed separators, and
  URL-encoded traversal attempts.
- Normalizes Unicode (NFC), strips zero-width characters, and rejects NULs or
  surrogate code points.
- Blocks symlink-based escapes by default and verifies resolved paths remain
  under the sandbox root.

### Limitations

- If operators set `L9_RESEARCH_FACTORY_BASE_DIR` to a path containing symlinks,
  the root will resolve to the symlink target; ensure the root is trusted.
- Sandboxing guards path resolution, not arbitrary file content; apply
  additional validation for schema contents where needed.

## Governance Superpack

The L9 authority model and governance policy enforcement are defined in the **Governance & Authority Superpack**:

- **File:** `reports/governance_superpack.md`
- **Authority Roles:** L=CTO (strategic), Cursor=IDE (code gen), Igor=Boss (ops)
- **Protected Invariants:**
  - PacketEnvelope schema changes require ADR-0097 approval
  - Governance policy checks cannot be bypassed
  - Authority role reassignments require L-CTO approval

**Before making changes to `core/governance/` or `core/packet_envelope/`:**

1. Read `reports/governance_superpack.md`
2. Verify no protected invariants are violated
3. If schema changes are needed, follow ADR-0097 process
4. Update governance enforcement tests

See also: `architecture_decisions.md` (ADR-0097)
