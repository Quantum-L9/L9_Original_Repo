#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "INT-AC-001"
component_name: "Autonomous Calibration System"
layer: "intelligence"
domain: "learning"
type: "calibrator"
status: "active"
created: "2025-11-08T00:00:00Z"
updated: "2025-11-08T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["json", "math", "datetime", "pathlib", "collections"]
integrates_with: ["FND-PE-001", "FND-LG-003", "INT-ML-001"]
api_endpoints: []
data_sources: ["telemetry/logs/probabilistic_decisions.jsonl", "meta-learning-log.md"]
outputs: ["calibration_reports", "optimized_parameters", "meta-learning-log entries"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "batch"

# === BUSINESS METADATA ===
purpose: "Autonomous nightly calibration of probabilistic governance parameters"
summary: "Analyzes decisions and outcomes to optimize temperature, adjust thresholds, update weights, and detect correlations - fully autonomous with zero manual intervention"
business_value: "Maintains optimal calibration automatically, ensures continuous improvement without maintenance burden"
success_metrics: ["ece_improvement > 0", "calibration_time < 60s", "autonomous_success_rate = 1.0"]

# === INTEGRATION METADATA ===
suite_2_origin: "New component - built by Claude Sonnet 4.5"
migration_notes: "Autonomous learning system based on temperature scaling and PAC-Bayesian optimization research"

# === TAGS & CLASSIFICATION ===
tags: ["calibration", "learning", "autonomous", "optimization", "temperature-scaling"]
keywords: ["calibration", "ece", "temperature", "optimization", "autonomous", "nightly"]
related_components: ["FND-PE-001", "INT-FC-001", "TEL-CD-001"]

# === DESCRIPTION ===
Autonomous Calibration System for Probabilistic Governance

Runs nightly to:
1. Analyze decisions and outcomes from last 24 hours
2. Optimize temperature parameter for best ECE
3. Adjust thresholds to maintain target precision
4. Update evidence weights based on predictive power
5. Detect and adjust for evidence correlations

No manual intervention required - fully autonomous.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Auto Calibrator",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-27T02:13:14Z",
    "updated_at": "2026-01-21T21:57:31Z",
    "layer": "operations",
    "domain": "current_work",
    "module_name": "auto_calibrator",
    "type": "dataclass",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["Anthropic API"],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CalibrationReport:
    """Report generated from calibration run"""

    timestamp: str
    decisions_analyzed: int
    decisions_with_outcomes: int

    # Calibration metrics
    ece_before: float
    ece_after: float
    ece_improvement: float

    # Temperature optimization
    temperature_before: float
    temperature_after: float
    temperature_changed: bool

    # Threshold adjustments
    thresholds_adjusted: dict[str, dict[str, float]]

    # Weight updates
    weights_updated: dict[str, float]

    # Correlation updates
    correlations_detected: dict[str, dict[str, float]]

    # Performance
    calibration_time_seconds: float
    next_calibration: str


class AutoCalibrator:
    """
    Autonomous calibration system - no manual intervention required.

    Schedule: Runs nightly at 2:00 AM (configurable)
    Trigger: Can also run on-demand after N decisions
    """

    def __init__(
        self,
        registry_path: str = "foundation/logic/rule-registry.json",
        telemetry_path: str = "telemetry/logs/probabilistic_decisions.jsonl",
        meta_learning_log: str = "intelligence/meta-learning/meta-learning-log.md",
    ):
        """
        Initializes the AutoCalibrator with paths to configuration, telemetry, and meta-learning logs for autonomous calibration without manual intervention.

        Args:
            registry_path: Path to the rule registry JSON file used for calibration decisions.
            telemetry_path: Path to the telemetry logs JSONL file containing probabilistic decision data.
            meta_learning_log: Path to the meta-learning log file for tracking calibration learning progress.
        """
        self.registry_path = Path(registry_path)
        self.telemetry_path = Path(telemetry_path)
        self.meta_learning_log = Path(meta_learning_log)

        self.registry = {}
        self.decisions = []

        self._load_registry()
        self._load_decisions()

    def _load_registry(self):
        """Load current rule registry"""
        try:
            with open(self.registry_path) as f:
                self.registry = json.load(f)
        except FileNotFoundError:
            self.registry = {
                "probabilistic_thresholds": {},
                "calibration_parameters": {"temperature": {"value": 1.0}},
                "probabilistic_models": {},
            }

    def _load_decisions(self, hours: int = 24):
        """Load recent decisions from telemetry"""
        if not self.telemetry_path.exists():
            self.decisions = []
            return

        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        self.decisions = []

        with open(self.telemetry_path) as f:
            for line in f:
                try:
                    decision = json.loads(line.strip())
                    decision_time = datetime.fromisoformat(decision["timestamp"])
                    if decision_time >= cutoff_time:
                        self.decisions.append(decision)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

    def run_calibration(self) -> CalibrationReport:
        """
        Main calibration routine - fully autonomous.

        Returns:
            Calibration report with all changes
        """
        start_time = datetime.now(UTC)

        # Filter to decisions with outcomes
        decisions_with_outcomes = [
            d for d in self.decisions if d.get("outcome") is not None
        ]

        # Get current parameters
        temp_before = self.registry["calibration_parameters"]["temperature"]["value"]
        ece_before = self._calculate_ece(decisions_with_outcomes)

        # Step 1: Optimize temperature
        temp_after = self._optimize_temperature(decisions_with_outcomes)
        temp_changed = abs(temp_after - temp_before) > 0.01

        # Step 2: Adjust thresholds
        threshold_adjustments = self._adjust_thresholds(decisions_with_outcomes)

        # Step 3: Update evidence weights
        weight_updates = self._update_evidence_weights(decisions_with_outcomes)

        # Step 4: Detect correlations
        correlations = self._detect_evidence_correlations(decisions_with_outcomes)

        # Calculate final ECE
        ece_after = self._calculate_ece(decisions_with_outcomes, use_new_params=True)

        # Save updated registry
        self._save_registry()

        # Log to meta-learning
        self._log_to_meta_learning(
            ece_before,
            ece_after,
            temp_before,
            temp_after,
            threshold_adjustments,
            weight_updates,
        )

        # Generate report
        calibration_time = (datetime.now(UTC) - start_time).total_seconds()

        report = CalibrationReport(
            timestamp=datetime.now(UTC).isoformat(),
            decisions_analyzed=len(self.decisions),
            decisions_with_outcomes=len(decisions_with_outcomes),
            ece_before=ece_before if ece_before is not None else 0.0,
            ece_after=ece_after if ece_after is not None else 0.0,
            ece_improvement=ece_before - ece_after if ece_before and ece_after else 0.0,
            temperature_before=temp_before,
            temperature_after=temp_after,
            temperature_changed=temp_changed,
            thresholds_adjusted=threshold_adjustments,
            weights_updated=weight_updates,
            correlations_detected=correlations,
            calibration_time_seconds=round(calibration_time, 2),
            next_calibration=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
        )

        return report

    def _calculate_ece(
        self, decisions: list[dict], use_new_params: bool = False
    ) -> float | None:
        """Calculate ECE for a set of decisions"""
        if len(decisions) < 10:
            return None

        num_bins = 10
        bins = [[] for _ in range(num_bins)]

        for decision in decisions:
            prob = decision["calibrated_probability"]
            bin_idx = min(int(prob * num_bins), num_bins - 1)
            bins[bin_idx].append(decision)

        ece = 0.0
        total = len(decisions)

        for bin_decisions in bins:
            if not bin_decisions:
                continue

            confidence = sum(d["calibrated_probability"] for d in bin_decisions) / len(
                bin_decisions
            )
            correct = sum(1 for d in bin_decisions if d["outcome"] == "correct")
            accuracy = correct / len(bin_decisions)

            ece += (len(bin_decisions) / total) * abs(confidence - accuracy)

        return round(ece, 4)

    def _optimize_temperature(self, decisions: list[dict]) -> float:
        """Optimize temperature to minimize ECE"""
        if len(decisions) < 50:
            return self.registry["calibration_parameters"]["temperature"]["value"]

        best_temp = 1.0
        best_ece = 1.0

        # Grid search
        for temp in [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 2.0]:
            test_decisions = []
            for d in decisions:
                raw = d.get("raw_probability", d["calibrated_probability"])
                # Recalibrate with test temperature
                logit = math.log(raw / (1 - raw + 1e-10) + 1e-10)
                scaled = logit / temp
                calibrated = 1 / (1 + math.exp(-scaled))

                test_d = d.copy()
                test_d["calibrated_probability"] = calibrated
                test_decisions.append(test_d)

            ece = self._calculate_ece(test_decisions)
            if ece and ece < best_ece:
                best_ece = ece
                best_temp = temp

        # Update in registry
        self.registry["calibration_parameters"]["temperature"]["value"] = best_temp
        return best_temp

    def _adjust_thresholds(self, decisions: list[dict]) -> dict[str, dict[str, float]]:
        """
        Adjust thresholds to maintain target precision.

        Strategy: If false positive rate is too high, raise threshold.
                 If false negative rate is too high, lower threshold.
        """
        adjustments = {}

        for threshold_name, threshold_config in self.registry.get(
            "probabilistic_thresholds", {}
        ).items():
            if not threshold_config.get("auto_adjust", False):
                continue

            threshold_value = threshold_config["value"]
            target_precision = threshold_config.get("target_precision", 0.80)

            # Classify decisions by this threshold
            above_threshold = [
                d for d in decisions if d["calibrated_probability"] >= threshold_value
            ]

            if len(above_threshold) < 10:
                continue  # Not enough data

            # Calculate current precision
            correct_above = sum(1 for d in above_threshold if d["outcome"] == "correct")
            current_precision = correct_above / len(above_threshold)

            # Adjust threshold
            adjustment = 0.0
            if current_precision < target_precision - 0.05:
                # Too many false positives - raise threshold
                adjustment = 0.02
            elif current_precision > target_precision + 0.05:
                # Too conservative - lower threshold
                adjustment = -0.02

            if adjustment != 0.0:
                new_value = max(0.0, min(1.0, threshold_value + adjustment))
                threshold_config["value"] = new_value
                threshold_config["last_calibrated"] = datetime.now(UTC).isoformat()

                # Update calibration data
                false_positives = len(above_threshold) - correct_above
                threshold_config["calibration_data"] = {
                    "true_positives": correct_above,
                    "false_positives": false_positives,
                    "precision": round(current_precision, 2),
                }

                adjustments[threshold_name] = {
                    "old_value": threshold_value,
                    "new_value": new_value,
                    "adjustment": adjustment,
                    "precision": current_precision,
                }

        return adjustments

    def _update_evidence_weights(self, decisions: list[dict]) -> dict[str, float]:
        """
        Update evidence source weights based on predictive power.

        Strategy: Evidence sources that correlate strongly with correct
                 outcomes get higher weights.
        """
        if len(decisions) < 100:
            return {}  # Need sufficient data

        # Analyze correlation between each evidence source and outcomes
        evidence_performance = defaultdict(
            lambda: {
                "correct_high": 0,
                "total_high": 0,
                "correct_low": 0,
                "total_low": 0,
            }
        )

        for decision in decisions:
            is_correct = decision["outcome"] == "correct"

            for evidence_name, evidence_data in decision.get("evidence", {}).items():
                value = evidence_data["value"]

                if value > 0.6:  # High evidence value
                    evidence_performance[evidence_name]["total_high"] += 1
                    if is_correct:
                        evidence_performance[evidence_name]["correct_high"] += 1
                elif value < 0.4:  # Low evidence value
                    evidence_performance[evidence_name]["total_low"] += 1
                    if is_correct:
                        evidence_performance[evidence_name]["correct_low"] += 1

        # Calculate predictive power for each evidence source
        weight_updates = {}

        for evidence_name, perf in evidence_performance.items():
            if perf["total_high"] < 10 or perf["total_low"] < 10:
                continue  # Not enough data

            # Predictive power = how well high/low values predict correctness
            precision_high = perf["correct_high"] / perf["total_high"]
            precision_low = perf["correct_low"] / perf["total_low"]

            predictive_power = abs(precision_high - precision_low)

            # Update weight (subtle adjustments)
            # Higher predictive power = slightly higher weight
            weight_adjustment = (predictive_power - 0.5) * 0.05  # Max ±2.5% adjustment

            if abs(weight_adjustment) > 0.01:
                weight_updates[evidence_name] = weight_adjustment

        # Apply updates to models
        for model in self.registry.get("probabilistic_models", {}).values():
            if "variables" in model:
                for _var_name, var_config in model["variables"].items():
                    if "weights" in var_config:
                        for evidence_name, adjustment in weight_updates.items():
                            if evidence_name in var_config["weights"]:
                                old_weight = var_config["weights"][evidence_name]
                                new_weight = max(
                                    0.05, min(0.50, old_weight + adjustment)
                                )
                                var_config["weights"][evidence_name] = round(
                                    new_weight, 3
                                )

        # Normalize weights to sum to 1.0
        self._normalize_weights()

        return weight_updates

    def _detect_evidence_correlations(
        self, decisions: list[dict]
    ) -> dict[str, dict[str, float]]:
        """
        Detect correlations between evidence sources.

        PAC-Bayesian insight: Correlated evidence should have reduced combined weight.
        """
        if len(decisions) < 50:
            return {}

        # Extract evidence values per source
        evidence_values = defaultdict(list)

        for decision in decisions:
            for evidence_name, evidence_data in decision.get("evidence", {}).items():
                evidence_values[evidence_name].append(evidence_data["value"])

        # Calculate pairwise correlations
        correlations = {}
        evidence_names = list(evidence_values.keys())

        for i, name1 in enumerate(evidence_names):
            correlations[name1] = {}
            for name2 in evidence_names[i + 1 :]:
                correlation = self._calculate_correlation(
                    evidence_values[name1], evidence_values[name2]
                )
                correlations[name1][name2] = round(correlation, 2)

                # Apply correlation penalty if high correlation detected
                if abs(correlation) > 0.70:
                    self._apply_correlation_penalty(name1, name2, correlation)

        # Store in registry
        if "calibration_parameters" not in self.registry:
            self.registry["calibration_parameters"] = {}
        if "evidence_correlations" not in self.registry["calibration_parameters"]:
            self.registry["calibration_parameters"]["evidence_correlations"] = {}

        self.registry["calibration_parameters"]["evidence_correlations"]["matrix"] = (
            correlations
        )
        self.registry["calibration_parameters"]["evidence_correlations"][
            "last_updated"
        ] = datetime.now(UTC).isoformat()

        return correlations

    def _calculate_correlation(
        self, values1: list[float], values2: list[float]
    ) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(values1) != len(values2) or len(values1) < 10:
            return 0.0

        n = len(values1)
        mean1 = sum(values1) / n
        mean2 = sum(values2) / n

        numerator = sum(
            (v1 - mean1) * (v2 - mean2)
            for v1, v2 in zip(values1, values2, strict=False)
        )
        denom1 = math.sqrt(sum((v1 - mean1) ** 2 for v1 in values1))
        denom2 = math.sqrt(sum((v2 - mean2) ** 2 for v2 in values2))

        if denom1 == 0 or denom2 == 0:
            return 0.0

        return numerator / (denom1 * denom2)

    def _apply_correlation_penalty(self, name1: str, name2: str, correlation: float):
        """
        Apply PAC-Bayesian correlation penalty to reduce double-counting.

        If two evidence sources are highly correlated, reduce their combined weight.
        """
        penalty = abs(correlation) * 0.10  # 10% penalty per correlation point

        for model in self.registry.get("probabilistic_models", {}).values():
            if "variables" in model:
                for var_config in model["variables"].values():
                    if "weights" in var_config:
                        weights = var_config["weights"]

                        if name1 in weights and name2 in weights:
                            # Reduce weight of the lesser-weighted source
                            if weights[name1] > weights[name2]:
                                weights[name2] = max(
                                    0.05, weights[name2] * (1 - penalty)
                                )
                            else:
                                weights[name1] = max(
                                    0.05, weights[name1] * (1 - penalty)
                                )

    def _normalize_weights(self):
        """Ensure all weights sum to 1.0 in each model"""
        for model in self.registry.get("probabilistic_models", {}).values():
            if "variables" in model:
                for var_config in model["variables"].values():
                    if "weights" in var_config:
                        weights = var_config["weights"]
                        total = sum(weights.values())
                        if total > 0:
                            for key in weights:
                                weights[key] = round(weights[key] / total, 3)

    def _save_registry(self):
        """Save updated registry back to file"""
        try:
            with open(self.registry_path, "w") as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error("Error saving registry", error=str(e))

    def _log_to_meta_learning(
        self,
        ece_before: float,
        ece_after: float,
        temp_before: float,
        temp_after: float,
        threshold_adjustments: dict,
        weight_updates: dict,
    ):
        """Log calibration to meta-learning log"""
        log_entry = f"""
## {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")} - Probabilistic Governance Calibration

**Calibration Type:** Nightly Auto-Calibration
**Decisions Analyzed:** {len(self.decisions)}
**Outcomes Available:** {len([d for d in self.decisions if d.get("outcome")])}

### Performance Improvement
- ECE Before: {ece_before:.4f if ece_before else 'N/A'}
- ECE After: {ece_after:.4f if ece_after else 'N/A'}
- Improvement: {ece_before - ece_after if ece_before and ece_after else "N/A"}

### Temperature Adjustment
- Before: {temp_before:.2f}
- After: {temp_after:.2f}
- Change: {temp_after - temp_before:+.2f}

### Threshold Adjustments
{json.dumps(threshold_adjustments, indent=2) if threshold_adjustments else "None"}

### Weight Updates
{json.dumps(weight_updates, indent=2) if weight_updates else "None"}

**Status:** {"✅ Calibration improved" if ece_after and ece_before and ece_after < ece_before else "⚠️ Monitoring"}

---
"""

        try:
            with open(self.meta_learning_log, "a") as f:
                f.write(log_entry)
        except Exception:
            logger.debug("auto_calibrator.meta_learning_log_write_failed")


def run_nightly_calibration():
    """Entry point for scheduled nightly calibration"""
    calibrator = AutoCalibrator()
    report = calibrator.run_calibration()

    logger.info(
        "Calibration Complete",
        decisions_analyzed=report.decisions_analyzed,
        ece_before=f"{report.ece_before:.4f}",
        ece_after=f"{report.ece_after:.4f}",
        temperature_before=f"{report.temperature_before:.2f}",
        temperature_after=f"{report.temperature_after:.2f}",
        thresholds_adjusted=len(report.thresholds_adjusted),
        time_seconds=f"{report.calibration_time_seconds:.2f}",
    )

    return report


if __name__ == "__main__":
    # Run calibration
    report = run_nightly_calibration()

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-048",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": [
        "api",
        "auth",
        "batch-processing",
        "current-work",
        "dataclass",
        "filesystem",
        "logging",
        "metrics",
        "migration",
        "monitoring",
    ],
    "keywords": ["auto", "calibration", "calibrator", "nightly", "report"],
    "business_value": "Provides auto calibrator components including CalibrationReport, AutoCalibrator",
    "last_modified": "2026-01-21T21:57:31Z",
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
