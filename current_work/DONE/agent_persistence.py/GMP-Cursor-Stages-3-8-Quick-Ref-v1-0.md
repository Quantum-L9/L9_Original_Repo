# GMP STAGE 3-8: Quick Reference Files

## STAGE 3: Integration Wiring v1.0
**Purpose**: Wire AgentPersistence to 6 integration points  
**Dependencies**: Stage 2 (core methods complete)  
**Produces**: Wired hooks in executor, server, approval_manager, ingestion  

Phase 0 TODOs: Wire 6 methods → 6 files (executor, server startup, server shutdown, ingestion, approval, instance)  

## STAGE 4: Retention & Lifecycle v1.0
**Purpose**: Add retention policies, cleanup automation  
**Dependencies**: Stage 3 (integration wired)  
**Produces**: RetentionPolicyEngine, lifecycle coordinator  

Phase 0 TODOs: Implement retention rules engine, add scheduler for cleanup, lifecycle hooks  

## STAGE 5: Integrity & Security v1.0
**Purpose**: Add checksums, schema versioning, encryption  
**Dependencies**: Stage 4 (retention complete)  
**Produces**: Checksum validation, schema versioning layer  

Phase 0 TODOs: Add SHA-256 validation, versioning detector, encrypted storage support  

## STAGE 6: Observability & Metrics v1.0
**Purpose**: Add Prometheus metrics, audit logging  
**Dependencies**: Stage 5 (security complete)  
**Produces**: Metrics definitions, audit schema  

Phase 0 TODOs: Add 8-10 key metrics (create latency, restore success rate, size, corruption), audit log table  

## STAGE 7: Testing & Validation v1.0
**Purpose**: Comprehensive unit, integration, chaos tests  
**Dependencies**: Stage 6 (observability complete)  
**Produces**: Test suite covering all paths  

Phase 0 TODOs: Unit tests (all 7 methods), integration tests (all 6 wiring points), chaos tests (failures, recovery)  

## STAGE 8: Deployment & Runbook v1.0
**Purpose**: Migration guide, ops runbook, final validation  
**Dependencies**: Stage 7 (tests pass)  
**Produces**: Migration guide, ops checklist  

Phase 0 TODOs: Migration script, ops playbook, pre-production validation checklist, final audit
