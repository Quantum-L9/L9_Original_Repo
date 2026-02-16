# Phase 1: Reliability Remediation

**Findings:** 4
**Total Fix Effort:** 17h

## Findings

### REL-P001: Missing transaction boundaries around multi-node DAG operations
- Severity: P0
- File: `memory/substrate_dag.py`
- Strategy: Wrap entire DAG execution in PacketEnvelope transaction context with rollback on any node failure. Use substrate_service.begin_transaction() / commit_transaction() around graph.invoke().

### REL-P002: PacketEnvelope.parent_ids access without length validation
- Severity: P1
- File: `memory/substrate_dag.py`
- Strategy: Add MAX_HIERARCHY_DEPTH=10 validation in intake_node before downstream processing.

### REL-P003: Missing error recovery and state cleanup on DAG node failures
- Severity: P1
- File: `memory/substrate_dag.py`
- Strategy: Implement structured error handling with PacketEnvelope.rejected() state transition and cleanup callbacks.

### REL-P004: Validation logic in intake_node violates ADR-0012
- Severity: P1
- File: `memory/substrate_dag.py`
- Strategy: Move ALL validation to canonical intake_node. substrate_service calls validated intake_node exclusively.
