# Dead Code Triage: `simulation`

**Date:** 2026-02-14 05:43 UTC

## Symbol Classification

**USED** (6): `EvaluationCriteria`, `EvaluationResult`, `Scenario`, `SimulationConfig`, `SimulationEngine`, `SimulationRun`
**ZERO_REF** (4): `OutcomeEvaluator`, `ScenarioLoader`, `ScenarioType`, `SimulationMetrics`

## File Classification

**WIRED** (1):
- `simulation/simulation_engine.py`
**ASPIRATIONAL** (2):
- `simulation/outcome_evaluator.py`
- `simulation/scenario_loader.py`

## Recommended Actions

### Review 4 zero-reference symbols
These have no references anywhere (not even internal). Either wire them or remove from `__all__`.
