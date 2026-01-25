## ADR-0066: Governance & Authority Superpack (2026-01-25)

**Decision:** Implement comprehensive governance superpack documenting L9 authority model, PacketEnvelope protocol, policy enforcement, and protected surfaces.

**Rationale:**
- Central hub for governance rules and protected invariants
- Reduces governance bypass attempts by making rules explicit
- Enables governance-aware PR reviews and CI gates
- Aligns with frontier AI lab standards (anthropic, openai)

**Scope:**
- Authority roles (L-CTO, Cursor, Igor) and their permissions
- PacketEnvelope schema (immutable without ADR approval)
- Policy enforcement gates (4-stage validation)
- Protected files (websocket_orchestrator.py, docker-compose.yml)

**Implementation:**
- `reports/governance_superpack.md` (8.5 KB detailed doc)
- `reports/governance_invariants.txt` (checklist)
- Integration in pr.md checklist and SECURITY.md

**See:** `reports/superpack_index.md` (cross-links to all related superpacks)
