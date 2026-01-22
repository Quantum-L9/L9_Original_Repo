"""
Anomaly Classifier Tests
=========================

Unit tests for AnomalyClassifier.
Tests classification rules, severity determination, and confidence scoring.

GMP: GMP-Workers-Wiring
Phase: 4 (VALIDATE)
"""

import pytest

from workers.anomaly_classifier import (AnomalyClassifier,
                                        AnomalyClassifierRequest,
                                        AnomalySeverity, AnomalyType,
                                        ClassificationRule)


class TestAnomalyClassifierInit:
    """Test AnomalyClassifier initialization."""

    def test_init_loads_default_rules(self):
        """Classifier initializes with default rules."""
        classifier = AnomalyClassifier()
        assert len(classifier._rules) > 0
        assert len(classifier._rules) >= len(AnomalyClassifier.DEFAULT_RULES)

    def test_init_with_custom_rules(self):
        """Classifier accepts custom rules."""
        custom_rule = ClassificationRule(
            pattern="custom_pattern",
            anomaly_type=AnomalyType.WORKFLOW,
            severity=AnomalySeverity.MINOR,
            description="Custom test rule",
        )
        classifier = AnomalyClassifier(custom_rules=[custom_rule])
        assert custom_rule in classifier._rules


class TestClassificationRules:
    """Test classification rule matching."""

    @pytest.mark.asyncio
    async def test_critical_security_detected(self):
        """Critical security anomalies are detected."""
        classifier = AnomalyClassifier()
        await classifier.startup()

        request = AnomalyClassifierRequest(
            anomaly_id="test-123",
            source="auth_service",
            raw_data={"event": "unauthorized_access attempt"},
        )

        response = await classifier.process(request)

        assert response.ok is True
        assert response.result is not None
        assert response.result.severity == AnomalySeverity.CRITICAL
        assert response.result.anomaly_type == AnomalyType.SECURITY

    @pytest.mark.asyncio
    async def test_moderate_performance_detected(self):
        """Moderate performance anomalies are detected."""
        classifier = AnomalyClassifier()
        await classifier.startup()

        request = AnomalyClassifierRequest(
            anomaly_id="test-456",
            source="api_gateway",
            raw_data={"metric": "high_latency", "value": 5000},
        )

        response = await classifier.process(request)

        assert response.ok is True
        assert response.result is not None
        assert response.result.severity == AnomalySeverity.MODERATE
        assert response.result.anomaly_type == AnomalyType.PERFORMANCE

    @pytest.mark.asyncio
    async def test_governance_violation_detected(self):
        """Governance violations are classified as critical."""
        classifier = AnomalyClassifier()
        await classifier.startup()

        request = AnomalyClassifierRequest(
            anomaly_id="test-789",
            source="kernel_monitor",
            raw_data={"event": "kernel_violation detected"},
        )

        response = await classifier.process(request)

        assert response.ok is True
        assert response.result is not None
        assert response.result.severity == AnomalySeverity.CRITICAL
        assert response.result.anomaly_type == AnomalyType.GOVERNANCE

    @pytest.mark.asyncio
    async def test_unknown_defaults_to_moderate(self):
        """Unknown anomalies default to moderate for investigation."""
        classifier = AnomalyClassifier()
        await classifier.startup()

        request = AnomalyClassifierRequest(
            anomaly_id="test-unknown",
            source="mystery_service",
            raw_data={"unknown": "data"},
        )

        response = await classifier.process(request)

        assert response.ok is True
        assert response.result is not None
        assert response.result.severity == AnomalySeverity.MODERATE
        assert response.result.recommended_action == "investigate"


class TestRecommendedActions:
    """Test recommended action generation."""

    @pytest.mark.asyncio
    async def test_critical_recommends_rollback(self):
        """Critical severity recommends rollback."""
        classifier = AnomalyClassifier()
        await classifier.startup()

        request = AnomalyClassifierRequest(
            anomaly_id="test-critical",
            source="safety_kernel",
            raw_data={"event": "safety_bypass attempt"},
        )

        response = await classifier.process(request)

        assert response.result.recommended_action == "rollback"

    @pytest.mark.asyncio
    async def test_moderate_recommends_remediate(self):
        """Moderate severity recommends remediation."""
        classifier = AnomalyClassifier()
        await classifier.startup()

        request = AnomalyClassifierRequest(
            anomaly_id="test-moderate",
            source="task_queue",
            raw_data={"event": "task_timeout occurred"},
        )

        response = await classifier.process(request)

        assert response.result.recommended_action == "remediate"

    @pytest.mark.asyncio
    async def test_minor_recommends_log_and_monitor(self):
        """Minor severity recommends log and monitor."""
        classifier = AnomalyClassifier()
        await classifier.startup()

        request = AnomalyClassifierRequest(
            anomaly_id="test-minor",
            source="config_service",
            raw_data={"event": "config_drift detected"},
        )

        response = await classifier.process(request)

        assert response.result.recommended_action == "log_and_monitor"


class TestConfidenceScoring:
    """Test confidence score calculation."""

    @pytest.mark.asyncio
    async def test_confidence_increases_with_matches(self):
        """Confidence increases when multiple rules match."""
        # Create classifier with rules that will both match
        custom_rules = [
            ClassificationRule(
                pattern="error",
                anomaly_type=AnomalyType.WORKFLOW,
                severity=AnomalySeverity.MODERATE,
                description="Error pattern 1",
            ),
            ClassificationRule(
                pattern="failure",
                anomaly_type=AnomalyType.WORKFLOW,
                severity=AnomalySeverity.MODERATE,
                description="Error pattern 2",
            ),
        ]
        classifier = AnomalyClassifier(custom_rules=custom_rules)
        await classifier.startup()

        # Request with data that matches both patterns
        request = AnomalyClassifierRequest(
            anomaly_id="test-multi",
            source="test",
            raw_data={"message": "error and failure occurred"},
        )

        response = await classifier.process(request)

        # Confidence should be higher with multiple matches
        assert response.result.confidence >= 0.5

    @pytest.mark.asyncio
    async def test_confidence_capped_at_95(self):
        """Confidence is capped at 0.95."""
        classifier = AnomalyClassifier()
        await classifier.startup()

        request = AnomalyClassifierRequest(
            anomaly_id="test-cap",
            source="test",
            raw_data={
                "unauthorized_access": True,
                "credential_leak": True,
                "kernel_violation": True,
            },
        )

        response = await classifier.process(request)

        assert response.result.confidence <= 0.95


class TestHealthCheck:
    """Test classifier health check."""

    @pytest.mark.asyncio
    async def test_health_before_startup(self):
        """Health check returns not_initialized before startup."""
        classifier = AnomalyClassifier()
        health = await classifier.health_check()

        assert health["status"] == "not_initialized"

    @pytest.mark.asyncio
    async def test_health_after_startup(self):
        """Health check returns healthy after startup."""
        classifier = AnomalyClassifier()
        await classifier.startup()
        health = await classifier.health_check()

        assert health["status"] == "healthy"
        assert health["rule_count"] > 0
