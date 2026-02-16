# Implementation Checklist

- [ ] REL-P001: Missing transaction boundaries around multi-node DAG operations (`memory/substrate_dag.py`)
- [ ] REL-P002: PacketEnvelope.parent_ids access without length validation (`memory/substrate_dag.py`)
- [ ] REL-P003: Missing error recovery and state cleanup on DAG node failures (`memory/substrate_dag.py`)
- [ ] REL-P004: Validation logic in intake_node violates ADR-0012 (`memory/substrate_dag.py`)