# Dead Code Triage: `domain_bridge`

**Date:** 2026-02-14 05:42 UTC

## Symbol Classification

**USED** (10): `AgentController`, `DecisionSynthesizer`, `GovernanceBridge`, `MemoryBridge`, `PacketRouter`, `ReasoningEngine`, `__footer_meta__`, `__l9_trace__`, `__version__`, `process_packet`

## File Classification

**WIRED** (8):
- `domain_bridge/agent_controller.py`
- `domain_bridge/context_enricher.py`
- `domain_bridge/governance_bridge.py`
- `domain_bridge/memory_bridge.py`
- `domain_bridge/packet_router.py`
- `domain_bridge/reasoning_engine.py`
- `domain_bridge/tensor_coordinator.py`
- `domain_bridge/world_model_bridge.py`
**WIP** (14):
- `domain_bridge/analogical_reasoner.py`
- `domain_bridge/anomaly_handler.py`
- `domain_bridge/causal_reasoner.py`
- `domain_bridge/compliance_checker.py`
- `domain_bridge/decision_synthesizer.py`
- `domain_bridge/domain_context_builder.py`
- `domain_bridge/domain_packet_handler.py`
- `domain_bridge/embedding_processor.py`
- `domain_bridge/escalation_handler.py`
- `domain_bridge/packet_formatter.py`
- `domain_bridge/packet_validator.py`
- `domain_bridge/reflective_auditor.py`
- `domain_bridge/symbolic_reasoner.py`
- `domain_bridge/tensoraios_bridge.py`

## Recommended Actions

### Wire 14 WIP files
Recently created but not yet integrated.
