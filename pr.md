## Superpack Review Checklist

Before merging, ensure you've consulted the relevant superpack(s):

- [ ] I have identified which superpacks my changes affect (use [reports/superpack_index.md](reports/superpack_index.md) dependency graph)
- [ ] I have read the relevant superpack docs (e.g., `reports/governance_superpack.md` if touching `core/governance/`)
- [ ] I have reviewed the \"Change Checklist\" section for each affected superpack
- [ ] I have verified no protected invariants are violated:
  - [ ] No changes to `websocket_orchestrator.py` without ops approval
  - [ ] No changes to `docker-compose.yml` without ops approval
  - [ ] No governance policy checks bypassed or mocked
  - [ ] No PacketEnvelope schema changes without ADR-0066 approval
  - [ ] No authority role assignments changed without L-CTO approval
- [ ] I have updated relevant documentation (ADRs, workflow state, superpack files) if behavior changed
