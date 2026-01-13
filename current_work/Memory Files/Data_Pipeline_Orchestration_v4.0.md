---
title: Data_Pipeline_Orchestration
version: 4.0.0
created: 2025-10-16T00:00:00Z
owner: Igor Beylin
platform: Odoo 19
source: Deliverables-AI Architecture.md
tags: [data-pipeline, orchestration, ETL, Odoo, RAG, governance, observability]
domain: data-infrastructure
type: orchestration-spec
production_ready: true
---

# Data_Pipeline_Orchestration_v4.0.md
**Author:** Igor Beylin  
**System:** Odoo 19 / AI Data Plane  
**Created:** 2025-10-16 10:22 UTC  
**Purpose:** Define end-to-end data movement between Odoo ERP, Mack RAG indices, and AI agents; ensure validated, auditable, idempotent operations.  
**Tags:** data-pipeline, orchestration, ETL, Odoo, RAG, governance, observability  

---

## 1. Scope and Guarantees
- Scope: Intake -> Normalization -> Buyer Match -> Offer -> Buyer Response -> Decision Ledger.
- SLOs: P95 end-to-end under 3.0 s for read paths; P95 under 8.0 s for write paths with validation.
- Guarantees: At-least-once ingestion; exactly-once writes via idempotency keys; full audit trail.

## 2. Canonical Streams
| Stream ID | From | To | Trigger | Payload Root | Idempotency Key |
|-----------|------|----|---------|--------------|-----------------|
| S-INTAKE-01 | ui.form.upload | bus.intake.normalized | file_submit | intake_form | sha256(intake_uuid) |
| S-NORM-02 | bus.intake.normalized | db.intake_records | agent.normalize | intake_record_v4 | sha256(source_uuid+ts_floor) |
| S-MATCH-03 | db.intake_records | agent.match | record_change(status=ready_for_match) | intake_id | sha256(intake_id+ver) |
| S-OFFER-04 | agent.match | agent.offer | match_ready | candidate_list_v4 | sha256(intake_id+buyer_id+ver) |
| S-RESP-05 | imap.odoo.mail | agent.response | inbound_email | message_rfc822 | message_id |
| S-LEDGER-06 | any.agent | db.decision_ledger | action_commit | decision_event_v4 | sha256(action_uuid) |

Notes:
- All bus topics are Odoo 19 bus channels; all db targets are Odoo models listed in Section 6.

## 3. Data Contracts (Schemas, v4.0)
### 3.1 intake_record_v4
- intake_id: str (UUID)
- supplier_id: str
- polymer: enum[HDPE, LDPE, LLDPE, PP, PET, PVC, PC, PA, ABS, Mixed, Unknown]
- form: enum[Bales, Regrind, Flake, Pellets, Parts, Film, Sheet, Scrap]
- type: enum[Post-Industrial, Post-Consumer, Mixed]
- color: enum[Natural, Mixed, Black, Color]
- contamination: str (free text)
- packaging: enum[Gaylords, Supersacks, Palletized, Loose, None]
- location_city: str
- location_state: str
- quantity_lbs: int
- weight_per_load_lbs: int
- loads_per_month: int
- ongoing: bool
- load_ready: bool
- processing_method: enum[Injection, Extrusion, BlowMolding, Thermoforming, Sheet, Film, Unknown]
- source: enum[Supplier, WebLead, SalesRep]
- confidence: float [0..1]
- location_confidence: float [0..1]
- attachments: array[str] (attachment_ids)
- created_at: datetime (UTC)
- version: str (e.g., v4.0)

### 3.2 candidate_list_v4
- intake_id: str
- top10: array[candidate_v4]
- next10: array[candidate_v4]
- rank_algo_version: str
- notes: str

candidate_v4:
- buyer_id: str
- score: float [0..100]
- reason_codes: array[str]
- gates_passed: array[str]
- risks: array[str]
- requires_doc: array[str]
- offer_band: object {floor_cents, target_cents, stretch_cents}
- freight_est_cents_per_lb: int
- risk_light: enum[green, yellow, red]

### 3.3 decision_event_v4
- action_uuid: str
- actor: enum[Mack, Human]
- action_type: enum[offer_sent, counter_sent, ack_received, price_override_request, error, pause, resume]
- ref_ids: object {intake_id?, offer_id?, buyer_id?, thread_id?}
- summary: str
- context_hash: str (sha256 of key fields)
- governance_flags: array[str]
- result: enum[ok, warn, error]
- created_at: datetime (UTC)
- version: str

## 4. Orchestration Logic
### 4.1 Triggers
- Record-level triggers in Odoo: model write() hooks emit bus events with minimal payload and idempotency key.
- Email triggers: Odoo mail gateway posts inbound RFC822 to bus with message_id as key.

### 4.2 Validation Pipeline
Order: structural -> referential -> semantic -> governance.
- Structural: JSON schema verification (v4.0 contracts).
- Referential: foreign keys to res.partner (supplier/buyer), product.polymer table.
- Semantic: confidence rules (polymer >= 0.80 else clarification task).
- Governance: price band, tone rules, override routing.

On failure:
- Write to ai_error_log with error_code, pointer(model, record_id, field), and remediation_hint.
- Auto-create followup task when error is recoverable; otherwise mark as require_human.

### 4.3 Idempotency
- For each write, compute idempotency_key. Store in ai_idem_registry(key, target_model, target_id, ts).
- If key exists, skip and return stored target_id. All agents must use this contract.

## 5. RAG Indexing for Mack
- Sources: approved KB markdowns, schemas, SOPs.
- Chunking: 800 tokens with 120 token overlap; hierarchical titles preserved.
- Metadata: {doc_id, title, version, created, tags, section_path, odoo_model_refs}
- Refresh: event-driven (any commit to kb_doc model) plus nightly rebuild.
- Retrieval: hybrid (BM25 + embeddings). K=12, rerank to 6, cite top 3.

## 6. Odoo Model Map (v4.0)
| Logical Entity | Odoo Model | Key Fields |
|----------------|------------|------------|
| Intake | sm.intake | intake_id (ext), supplier_id, status, payload_json |
| Buyer Card | sm.buyer_card | buyer_id, capability_fields, gates, risk |
| Offer | sm.offer | offer_id, intake_id, buyer_id, price_bands, attachments |
| Message Thread | mail.thread | thread_id, subject, message_ids, buyer_id |
| Decision Ledger | sm.decision_ledger | action_uuid, action_type, ref_ids, result |
| Error Log | sm.ai_error_log | error_id, error_code, pointer, severity, remediation |
| Idempotency Register | sm.ai_idem_registry | key, target_model, target_id, ts |
| KB Doc | sm.kb_doc | doc_id, title, version, body, tags, approved |

Notes:
- All sm.* models are custom Odoo modules in this project.

## 7. Bus Channels (Odoo 19)
- bus.intake.normalized
- bus.match.request
- bus.offer.request
- bus.offer.sent
- bus.response.inbound
- bus.decision.commit
- bus.kb.updated
- bus.agent.error

Message envelope (common):
- meta: {event_id, produced_at_utc, idempotency_key, producer}
- payload: one of the contracts in Section 3
- sig: HMAC of payload with server-side secret (optional, can be disabled in dev)

## 8. Error Handling and Backpressure
- Retries: exponential 1s, 2s, 4s, 8s, max 4 attempts; then dead-letter to sm.ai_error_log.
- Circuit breaker: open after 5 errors/60s per channel; auto half-open after 2 min.
- Quotas: max 50 in-flight messages per channel; reject with backpressure warning.
- Poison message resolution: quarantined payload stored; redrive after manual fix.

## 9. Observability
- Metrics: events_in, events_out, validate_fail_rate, idem_hits, latency_ms_p50/p95.
- Traces: correlation_id = action_uuid or message_id; spans across validator, writer, notifier.
- Logs: structured JSON, ASCII-only; severity tokens [INFO], [WARN], [ERROR]; no emojis.

## 10. Security and Access
- Role-bound API keys within Odoo for agents; field-level ACLs for sensitive data.
- PII minimization: only necessary fields in bus payload; attachments referenced by id.
- Audit: every state-changing operation mirrored to sm.decision_ledger with context_hash.

## 11. Deployment Profiles
- Dev: validation soft-fail, HMAC disabled, sample mail inbox.
- Staging: full validation, HMAC enabled, rate limits enforced.
- Prod: same as staging plus circuit breakers, alerts to WhatsApp per env vars.

## 12. Test Matrix (Excerpt)
| Case | Input | Expectation |
|------|-------|-------------|
| T-001 | valid intake_record_v4 | db write, bus.match.request emitted |
| T-009 | low polymer confidence 0.62 | clarification task created, no match event |
| T-014 | duplicate offer send | idem hit; no new record; ledger append only |
| T-021 | inbound email with same thread_id | routed to correct buyer conversation |

## 13. Change Control
- Versioning: semantic (v4.x). Any schema change requires bump and migration script.
- Changelog: sm.kb_doc and sm.decision_ledger note releases with diff pointer.
- Rollback: feature flags per stream; disable emitters without data loss.

---

**End of File**
