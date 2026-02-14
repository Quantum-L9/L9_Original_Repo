# Package Wiring Audit: domain_tensor_bridge

**Date:** 2026-02-14 05:36 UTC

## Level B: File Wiring — `domain_tensor_bridge`

Files checked: 22
- WIRED: 0
- PARTIAL: 8
- ORPHAN: 14
- ENTRYPOINT: 0
- TEST_ONLY: 0

| File | Ext Consumers | Test Consumers | Test File | Re-exported | Status |
|------|-------------:|---------------:|-----------|-------------|--------|
| `domain_tensor_bridge/agent_controller.py` | 2 | 0 | - | - | PARTIAL |
| `domain_tensor_bridge/analogical_reasoner.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/anomaly_handler.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/causal_reasoner.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/compliance_checker.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/context_enricher.py` | 1 | 0 | - | - | PARTIAL |
| `domain_tensor_bridge/decision_synthesizer.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/domain_context_builder.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/domain_packet_handler.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/embedding_processor.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/escalation_handler.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/governance_bridge.py` | 1 | 0 | - | - | PARTIAL |
| `domain_tensor_bridge/memory_bridge.py` | 2 | 0 | - | - | PARTIAL |
| `domain_tensor_bridge/packet_formatter.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/packet_router.py` | 1 | 0 | - | - | PARTIAL |
| `domain_tensor_bridge/packet_validator.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/reasoning_engine.py` | 1 | 0 | - | - | PARTIAL |
| `domain_tensor_bridge/reflective_auditor.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/symbolic_reasoner.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/tensor_coordinator.py` | 1 | 0 | - | - | PARTIAL |
| `domain_tensor_bridge/tensoraios_bridge.py` | 0 | 0 | - | - | ORPHAN |
| `domain_tensor_bridge/world_model_bridge.py` | 1 | 0 | - | - | PARTIAL |

## Level C: API Instantiation — `domain_tensor_bridge`

API Status: **HAS_API**
Symbols checked: 10
- USED: 10
- TEST_ONLY: 0
- UNUSED: 0
