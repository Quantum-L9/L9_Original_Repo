"""
L9 L Agent Runtime - Reflection Engine
=======================================
Implements the Reflection Loop protocol (P-REFLECT-001).

The reflection loop:
1. Capture expectation (before action)
2. Execute action
3. Observe outcome
4. Compare expectation vs reality
5. Extract learning
6. Update models
7. Adjust behavior

Version: 1.0.0
Author: Manus AI
Created: 2025-12-20
"""

import structlog
from dataclasses import dataclass
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


@dataclass
class ReflectionResult:
    """Result of reflecting on an action."""

    prediction_accuracy: float
    surprise_factor: float
    error_magnitude: str  # "low", "medium", "high"
    learning: dict
    adjustments: list[str]


class ReflectionEngine:
    """Implements the Reflection Loop protocol (P-REFLECT-001)."""

    def __init__(self, state_manager, memory_manager=None):
        """
        Initialize reflection engine.

        Args:
            state_manager: Agent state manager
            memory_manager: Optional memory substrate
        """
        self.state = state_manager
        self.memory = memory_manager

    def reflect_on_recent_actions(self, window: int = 20) -> dict:
        """
        Perform batch reflection on recent actions.

        Args:
            window: Number of recent actions to reflect on

        Returns:
            Summary of reflection results
        """
        recent = self.state.action_history[-window:]

        reflected_count = 0
        total_accuracy = 0.0

        for action_record in recent:
            # Only reflect on completed actions
            if action_record.get("actual_outcome") is not None:
                result = self.reflect_on_action(action_record)
                reflected_count += 1
                total_accuracy += result.prediction_accuracy

        # Update last reflection timestamp
        self.state.last_reflection_timestamp = datetime.now(timezone.utc).isoformat()

        # Calculate average accuracy
        avg_accuracy = total_accuracy / reflected_count if reflected_count > 0 else 0.0

        return {
            "reflected_count": reflected_count,
            "average_accuracy": avg_accuracy,
            "timestamp": self.state.last_reflection_timestamp,
        }

    def reflect_on_action(self, action_record: dict) -> ReflectionResult:
        """
        Execute the 7-step reflection protocol on a single action.

        Args:
            action_record: Dict with action, expectation, outcome

        Returns:
            ReflectionResult object
        """
        # Step 1: Expectation already captured
        expectation = action_record.get("expectation", {})

        # Step 2: Action already executed
        # Step 3: Outcome already observed
        actual = action_record.get("actual_outcome", {})

        # Step 4: Compare expectation vs reality
        comparison = self.compare_expectation_vs_reality(expectation, actual)

        # Step 5: Extract learning
        learning = self.extract_learning(comparison, action_record)

        # Step 6: Update models
        self.update_models(learning)

        # Step 7: Adjust behavior
        adjustments = self.adjust_behavior(learning)

        # Store reflection in action record
        action_record["reflection"] = {
            "comparison": comparison,
            "learning": learning,
            "adjustments": adjustments,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return ReflectionResult(
            prediction_accuracy=comparison["prediction_accuracy"],
            surprise_factor=comparison["surprise_factor"],
            error_magnitude=comparison["error_magnitude"],
            learning=learning,
            adjustments=adjustments,
        )

    def compare_expectation_vs_reality(self, expectation: dict, actual: dict) -> dict:
        """
        Compare expected vs actual outcomes.

        Args:
            expectation: Expected outcome
            actual: Actual outcome

        Returns:
            Comparison metrics
        """
        # Simple heuristic: check if success matches expectation
        expected_success = expectation.get("outcome") == "success"
        actual_success = actual.get("success", False) or not actual.get("error")

        # Calculate prediction accuracy
        if expected_success == actual_success:
            prediction_accuracy = 0.9  # High accuracy
            surprise_factor = 0.1
            error_magnitude = "low"
        else:
            prediction_accuracy = 0.1  # Low accuracy
            surprise_factor = 0.9
            error_magnitude = "high"

        return {
            "prediction_accuracy": prediction_accuracy,
            "surprise_factor": surprise_factor,
            "error_magnitude": error_magnitude,
            "expected_success": expected_success,
            "actual_success": actual_success,
        }

    def extract_learning(self, comparison: dict, action_record: dict) -> dict:
        """
        Derive insights from the comparison.

        Args:
            comparison: Comparison results
            action_record: Full action record

        Returns:
            Learning insights
        """
        learning = {
            "what_worked": [],
            "what_failed": [],
            "why_it_happened": "",
            "what_to_change": [],
        }

        if comparison["prediction_accuracy"] > 0.7:
            # High accuracy - action worked as expected
            learning["what_worked"].append(
                f"Action {action_record['action'].get('type')} succeeded as predicted"
            )
            learning["why_it_happened"] = "Prediction model was accurate"
        else:
            # Low accuracy - unexpected outcome
            learning["what_failed"].append(
                f"Action {action_record['action'].get('type')} did not match expectation"
            )
            learning["why_it_happened"] = (
                "Context may have changed or model needs calibration"
            )
            learning["what_to_change"].append("Improve context awareness")
            learning["what_to_change"].append("Recalibrate confidence scoring")

        return learning

    def update_models(self, learning: dict):
        """
        Update confidence calibration and prediction models.

        Args:
            learning: Learning insights
        """
        # Calculate success rate over recent actions
        recent = self.state.action_history[-20:]
        if recent:
            success_rate = sum(1 for a in recent if a.get("success")) / len(recent)

            # Calculate prediction accuracy
            accurate_predictions = sum(
                1
                for a in recent
                if a.get("reflection", {})
                .get("comparison", {})
                .get("prediction_accuracy", 0)
                > 0.7
            )
            prediction_accuracy = accurate_predictions / len(recent) if recent else 0.0

            # Update performance metrics
            if not hasattr(self.state, "performance_metrics"):
                self.state.performance_metrics = {}

            self.state.performance_metrics.update(
                {
                    "success_rate_last_20": success_rate,
                    "prediction_accuracy": prediction_accuracy,
                    "surprise_rate": 1.0 - prediction_accuracy,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
            )

            logger.info(
                f"Updated models: success_rate={success_rate:.2f}, accuracy={prediction_accuracy:.2f}"
            )

    def adjust_behavior(self, learning: dict) -> list[str]:
        """
        Adjust confidence threshold based on performance (H-THRESHOLD-001).

        Args:
            learning: Learning insights

        Returns:
            List of adjustments made
        """
        adjustments = []

        # Get performance metrics
        metrics = getattr(self.state, "performance_metrics", {})
        success_rate = metrics.get("success_rate_last_20", 0.5)
        trust_index = getattr(self.state, "trust_index", 0.5)

        # Dynamic threshold tuning rules (H-THRESHOLD-001)
        current_threshold = self.state.confidence_threshold
        new_threshold = current_threshold

        # Rule 1: Increase confidence (lower threshold) if performing well
        if success_rate > 0.85 and trust_index > 0.7:
            new_threshold = max(0.30, current_threshold - 0.05)
            adjustments.append(
                f"Decreased threshold from {current_threshold:.2f} to {new_threshold:.2f} (high success rate)"
            )

        # Rule 2: Decrease confidence (raise threshold) if performing poorly
        elif success_rate < 0.60 or trust_index < 0.5:
            new_threshold = min(0.95, current_threshold + 0.10)
            adjustments.append(
                f"Increased threshold from {current_threshold:.2f} to {new_threshold:.2f} (low success rate or trust)"
            )

        # Apply threshold change
        if new_threshold != current_threshold:
            self.state.confidence_threshold = new_threshold
            logger.info(
                f"Adjusted confidence threshold: {current_threshold:.2f} → {new_threshold:.2f}"
            )

        return adjustments
