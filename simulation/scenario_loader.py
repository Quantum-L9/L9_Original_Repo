"""
L9 Simulation - Scenario Loader
===============================

Loads and defines simulation scenarios.

Scenario types:
- Normal: Standard execution conditions
- Stress: High load conditions
- Failure: Induced failure scenarios
- Edge: Edge case scenarios
"""

from __future__ import annotations

# ============================================================================
__dora_meta__ = {
    "component_name": "Scenario Loader",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "learning",
    "domain": "data_models",
    "module_name": "scenario_loader",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["simulation.__init__"],
    },
}
# ============================================================================

import json
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

logger = structlog.get_logger(__name__)


class ScenarioType(str, Enum):
    """Types of simulation scenarios."""

    NORMAL = "normal"
    STRESS = "stress"
    FAILURE = "failure"
    EDGE = "edge"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


@dataclass
class ScenarioCondition:
    """A condition within a scenario."""

    name: str
    type: str  # resource, timing, failure, constraint
    parameters: dict[str, Any] = field(default_factory=dict)
    probability: float = 1.0  # Probability this condition applies

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "parameters": self.parameters,
            "probability": self.probability,
        }


@dataclass
class Scenario:
    """A complete simulation scenario."""

    scenario_id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    scenario_type: ScenarioType = ScenarioType.NORMAL
    conditions: list[ScenarioCondition] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    expected_outcomes: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": str(self.scenario_id),
            "name": self.name,
            "description": self.description,
            "scenario_type": self.scenario_type.value,
            "conditions": [c.to_dict() for c in self.conditions],
            "parameters": self.parameters,
            "expected_outcomes": self.expected_outcomes,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scenario:
        """Create scenario from dictionary."""
        conditions = [
            ScenarioCondition(
                name=c.get("name", ""),
                type=c.get("type", ""),
                parameters=c.get("parameters", {}),
                probability=c.get("probability", 1.0),
            )
            for c in data.get("conditions", [])
        ]

        return cls(
            scenario_id=UUID(data["scenario_id"]) if "scenario_id" in data else uuid4(),
            name=data.get("name", ""),
            description=data.get("description", ""),
            scenario_type=ScenarioType(data.get("scenario_type", "normal")),
            conditions=conditions,
            parameters=data.get("parameters", {}),
            expected_outcomes=data.get("expected_outcomes", {}),
            tags=data.get("tags", []),
        )


class ScenarioLoader:
    """
    Loads and manages simulation scenarios.

    Supports:
    - Built-in scenarios
    - Custom scenario definitions
    - Scenario loading from files
    - Dynamic scenario generation
    """

    def __init__(self, scenario_dir: Optional[Path] = None):
        """
        Initialize the scenario loader.

        Args:
            scenario_dir: Optional directory for scenario files
        """
        self._scenario_dir = scenario_dir
        self._scenarios: dict[str, Scenario] = {}
        self._builtin_loaded = False

        logger.info("ScenarioLoader initialized")

    # ==========================================================================
    # Built-in Scenarios
    # ==========================================================================

    def load_builtins(self) -> None:
        """Load built-in scenarios."""
        if self._builtin_loaded:
            return

        # Normal execution scenario
        self._scenarios["normal"] = Scenario(
            name="Normal Execution",
            description="Standard execution conditions",
            scenario_type=ScenarioType.NORMAL,
            conditions=[],
            parameters={
                "risk_multiplier": 1.0,
                "resource_limit": None,
                "timeout_multiplier": 1.0,
            },
            expected_outcomes={
                "success_rate_min": 0.8,
            },
        )

        # Stress test scenario
        self._scenarios["stress"] = Scenario(
            name="Stress Test",
            description="High load simulation",
            scenario_type=ScenarioType.STRESS,
            conditions=[
                ScenarioCondition(
                    name="high_load",
                    type="resource",
                    parameters={"cpu_multiplier": 2.0, "memory_multiplier": 1.5},
                ),
                ScenarioCondition(
                    name="slow_network",
                    type="timing",
                    parameters={"latency_multiplier": 3.0},
                ),
            ],
            parameters={
                "risk_multiplier": 1.5,
                "timeout_multiplier": 2.0,
            },
            expected_outcomes={
                "success_rate_min": 0.6,
                "degradation_acceptable": True,
            },
        )

        # Failure injection scenario
        self._scenarios["failure_injection"] = Scenario(
            name="Failure Injection",
            description="Inject random failures",
            scenario_type=ScenarioType.FAILURE,
            conditions=[
                ScenarioCondition(
                    name="random_failure",
                    type="failure",
                    parameters={"failure_rate": 0.3},
                    probability=0.5,
                ),
                ScenarioCondition(
                    name="dependency_failure",
                    type="failure",
                    parameters={"affected_types": ["api_call"]},
                    probability=0.3,
                ),
            ],
            parameters={
                "risk_multiplier": 2.0,
            },
            expected_outcomes={
                "graceful_degradation": True,
                "error_handling_tested": True,
            },
        )

        # Edge case scenario
        self._scenarios["edge_cases"] = Scenario(
            name="Edge Cases",
            description="Test boundary conditions",
            scenario_type=ScenarioType.EDGE,
            conditions=[
                ScenarioCondition(
                    name="empty_input",
                    type="constraint",
                    parameters={"input_size": 0},
                ),
                ScenarioCondition(
                    name="max_input",
                    type="constraint",
                    parameters={"input_size": "max"},
                ),
                ScenarioCondition(
                    name="concurrent_access",
                    type="timing",
                    parameters={"concurrent_users": 100},
                ),
            ],
            parameters={
                "risk_multiplier": 1.3,
            },
            expected_outcomes={
                "boundary_handling": True,
            },
        )

        # Security scenario
        self._scenarios["security"] = Scenario(
            name="Security Testing",
            description="Security-focused simulation",
            scenario_type=ScenarioType.SECURITY,
            conditions=[
                ScenarioCondition(
                    name="auth_failure",
                    type="failure",
                    parameters={"target": "authentication"},
                    probability=0.2,
                ),
                ScenarioCondition(
                    name="injection_attempt",
                    type="constraint",
                    parameters={"malicious_input": True},
                ),
            ],
            parameters={
                "risk_multiplier": 1.5,
            },
            expected_outcomes={
                "security_preserved": True,
            },
        )

        # Performance scenario
        self._scenarios["performance"] = Scenario(
            name="Performance Testing",
            description="Performance benchmarking",
            scenario_type=ScenarioType.PERFORMANCE,
            conditions=[
                ScenarioCondition(
                    name="high_throughput",
                    type="resource",
                    parameters={"requests_per_second": 1000},
                ),
            ],
            parameters={
                "risk_multiplier": 1.0,
                "collect_timing": True,
            },
            expected_outcomes={
                "latency_p99_ms": 500,
                "throughput_min": 100,
            },
        )

        self._builtin_loaded = True
        logger.info(f"Loaded {len(self._scenarios)} built-in scenarios")

    # ==========================================================================
    # Scenario Loading
    # ==========================================================================

    def load_from_file(self, path: Path) -> Scenario:
        """
        Load a scenario from a JSON file.

        Args:
            path: Path to scenario file

        Returns:
            Loaded Scenario
        """
        with open(path, "r") as f:
            data = json.load(f)

        scenario = Scenario.from_dict(data)
        self._scenarios[scenario.name] = scenario

        logger.info(f"Loaded scenario '{scenario.name}' from {path}")
        return scenario

    def load_from_directory(self) -> list[Scenario]:
        """
        Load all scenarios from the scenario directory.

        Returns:
            List of loaded scenarios
        """
        if not self._scenario_dir or not self._scenario_dir.exists():
            return []

        loaded = []
        for path in self._scenario_dir.glob("*.json"):
            try:
                scenario = self.load_from_file(path)
                loaded.append(scenario)
            except Exception as e:
                logger.error(f"Failed to load scenario from {path}: {e}")

        return loaded

    def save_scenario(self, scenario: Scenario, path: Optional[Path] = None) -> Path:
        """
        Save a scenario to a file.

        Args:
            scenario: Scenario to save
            path: Optional output path

        Returns:
            Path where scenario was saved
        """
        if path is None:
            if self._scenario_dir:
                path = (
                    self._scenario_dir
                    / f"{scenario.name.lower().replace(' ', '_')}.json"
                )
            else:
                path = Path(f"{scenario.name.lower().replace(' ', '_')}.json")

        with open(path, "w") as f:
            json.dump(scenario.to_dict(), f, indent=2)

        logger.info(f"Saved scenario '{scenario.name}' to {path}")
        return path

    # ==========================================================================
    # Scenario Access
    # ==========================================================================

    def get_scenario(self, name: str) -> Optional[Scenario]:
        """Get a scenario by name."""
        if not self._builtin_loaded:
            self.load_builtins()
        return self._scenarios.get(name)

    def get_scenarios_by_type(self, scenario_type: ScenarioType) -> list[Scenario]:
        """Get all scenarios of a given type."""
        if not self._builtin_loaded:
            self.load_builtins()
        return [s for s in self._scenarios.values() if s.scenario_type == scenario_type]

    def get_all_scenarios(self) -> list[Scenario]:
        """Get all loaded scenarios."""
        if not self._builtin_loaded:
            self.load_builtins()
        return list(self._scenarios.values())

    def list_scenario_names(self) -> list[str]:
        """List all scenario names."""
        if not self._builtin_loaded:
            self.load_builtins()
        return list(self._scenarios.keys())

    # ==========================================================================
    # Scenario Creation
    # ==========================================================================

    def create_scenario(
        self,
        name: str,
        scenario_type: ScenarioType,
        conditions: Optional[list[dict[str, Any]]] = None,
        parameters: Optional[dict[str, Any]] = None,
        description: str = "",
    ) -> Scenario:
        """
        Create a new scenario.

        Args:
            name: Scenario name
            scenario_type: Type of scenario
            conditions: List of condition dicts
            parameters: Scenario parameters
            description: Scenario description

        Returns:
            Created Scenario
        """
        scenario_conditions = []
        for c in conditions or []:
            scenario_conditions.append(
                ScenarioCondition(
                    name=c.get("name", ""),
                    type=c.get("type", ""),
                    parameters=c.get("parameters", {}),
                    probability=c.get("probability", 1.0),
                )
            )

        scenario = Scenario(
            name=name,
            description=description,
            scenario_type=scenario_type,
            conditions=scenario_conditions,
            parameters=parameters or {},
        )

        self._scenarios[name] = scenario
        logger.info(f"Created scenario '{name}'")

        return scenario

    def create_composite_scenario(
        self,
        name: str,
        base_scenarios: list[str],
    ) -> Scenario:
        """
        Create a scenario by combining existing scenarios.

        Args:
            name: Name for new scenario
            base_scenarios: Names of scenarios to combine

        Returns:
            Combined Scenario
        """
        combined_conditions: list[ScenarioCondition] = []
        combined_parameters: dict[str, Any] = {}

        for scenario_name in base_scenarios:
            base = self.get_scenario(scenario_name)
            if base:
                combined_conditions.extend(base.conditions)
                combined_parameters.update(base.parameters)

        scenario = Scenario(
            name=name,
            description=f"Composite: {', '.join(base_scenarios)}",
            scenario_type=ScenarioType.CUSTOM,
            conditions=combined_conditions,
            parameters=combined_parameters,
        )

        self._scenarios[name] = scenario
        return scenario


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SIM-LEAR-003",
    "governance_level": "high",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "data-models",
        "dataclass",
        "filesystem",
        "learning",
        "loader",
        "logging",
        "performance",
        "serialization",
    ],
    "keywords": [
        "all",
        "builtins",
        "composite",
        "condition",
        "conditions",
        "create",
        "directory",
        "edge",
    ],
    "business_value": "Provides scenario loader components including ScenarioType, ScenarioCondition, Scenario",
    "last_modified": "2026-01-07T13:35:58Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
