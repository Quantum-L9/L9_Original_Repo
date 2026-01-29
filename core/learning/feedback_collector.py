#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "INT-FC-001"
component_name: "Feedback Collector"
layer: "intelligence"
domain: "learning"
type: "collector"
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
dependencies: ["json", "datetime", "pathlib", "enum"]
integrates_with: ["FND-PE-001", "INT-AC-001", "INT-ML-001"]
api_endpoints: []
data_sources: ["user_feedback", "behavioral_signals"]
outputs: ["telemetry/logs/user_feedback.jsonl", "meta-learning-log.md", "immediate_adjustments"]

# === OPERATIONAL METADATA ===
execution_mode: "realtime"
monitoring_required: true
logging_level: "info"
performance_tier: "realtime"

# === BUSINESS METADATA ===
purpose: "Capture and process user feedback on governance decisions for real-time learning"
summary: "Real-time feedback collection with immediate micro-adjustments, pattern detection, and meta-learning integration - fully autonomous"
business_value: "Enables continuous learning from user corrections without manual intervention"
success_metrics: ["feedback_processing_latency < 10ms", "pattern_detection_rate > 0.80", "immediate_adjustment_success = 1.0"]

# === INTEGRATION METADATA ===
suite_2_origin: "New component - built by Claude Sonnet 4.5"
migration_notes: "Real-time learning system with explicit and implicit feedback capture"

# === TAGS & CLASSIFICATION ===
tags: ["feedback", "learning", "real-time", "pattern-detection", "user-corrections"]
keywords: ["feedback", "learning", "correction", "pattern", "micro-adjustment"]
related_components: ["FND-PE-001", "INT-AC-001"]

# === DESCRIPTION ===
Real-Time Feedback Collector for Probabilistic Governance

Captures user feedback on governance decisions and triggers:
1. Immediate micro-adjustments (<5% weight/threshold changes)
2. Pattern recognition for systematic corrections
3. Meta-learning log updates
4. Triggers for next calibration if significant drift detected

Fully autonomous - no manual intervention required.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Feedback Collector",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-27T02:13:14Z",
    "updated_at": "2026-01-21T21:57:31Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "feedback_collector",
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

from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class FeedbackType(Enum):
    """Types of user feedback"""
    CORRECT = "correct"
    TOO_STRICT = "too_strict"
    TOO_LENIENT = "too_lenient"
    UNCLEAR = "unclear"


@dataclass
class FeedbackEvent:
    """Single feedback event"""
    decision_id: str
    feedback_type: FeedbackType
    context: Dict
    timestamp: str
    immediate_action_taken: str


class FeedbackCollector:
    """
    Collects and processes user feedback on governance decisions.
    
    Feedback Sources:
    1. Explicit: User says "that was fine" or "too strict"
    2. Implicit: Behavioral (user edits file after warning = I was right)
    3. Pattern: User repeatedly ignores warnings in specific context
    """
    
    def __init__(
        self,
        registry_path: str = "foundation/logic/rule-registry.json",
        telemetry_path: str = "telemetry/logs/probabilistic_decisions.jsonl",
        feedback_log_path: str = "telemetry/logs/user_feedback.jsonl"
    ):
        self.registry_path = Path(registry_path)
        self.telemetry_path = Path(telemetry_path)
        self.feedback_log_path = Path(feedback_log_path)
        
        self.registry = {}
        self.feedback_history = []
        
        self._load_registry()
        self._load_feedback_history()
    
    def _load_registry(self):
        """Load current registry"""
        try:
            with open(self.registry_path) as f:
                self.registry = json.load(f)
        except FileNotFoundError:
            self.registry = {
                'probabilistic_thresholds': {},
                'calibration_parameters': {'temperature': {'value': 1.0}},
                'probabilistic_models': {}
            }
    
    def _load_feedback_history(self):
        """Load recent feedback history"""
        if not self.feedback_log_path.exists():
            return
        
        with open(self.feedback_log_path) as f:
            for line in f:
                try:
                    self.feedback_history.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
    
    def record_explicit_feedback(
        self,
        decision_id: str,
        feedback: str,
        context: Optional[Dict] = None
    ) -> FeedbackEvent:
        """
        Record explicit user feedback.
        
        Args:
            decision_id: ID of the decision being evaluated
            feedback: User's feedback ('correct', 'too_strict', 'too_lenient')
            context: Additional context about the feedback
        """
        # Normalize feedback
        feedback_type = self._parse_feedback(feedback)
        
        # Create event
        event = FeedbackEvent(
            decision_id=decision_id,
            feedback_type=feedback_type,
            context=context or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
            immediate_action_taken="pending"
        )
        
        # Process feedback immediately
        action = self._process_feedback(event)
        event.immediate_action_taken = action
        
        # Log feedback
        self._log_feedback(event)
        
        # Update decision outcome in telemetry
        self._update_decision_outcome(decision_id, feedback_type.value)
        
        return event
    
    def record_implicit_feedback(
        self,
        decision_id: str,
        user_action: str,
        decision_context: Dict
    ) -> Optional[FeedbackEvent]:
        """
        Infer feedback from user behavior.
        
        Examples:
        - User edits file after I warned → I was correct
        - User says "this is fine" after I block → I was too strict
        - User ignores 5 warnings in same directory → Too strict for this context
        """
        feedback_type = self._infer_feedback_from_behavior(user_action, decision_context)
        
        if feedback_type is None:
            return None  # Ambiguous behavior, don't learn from it
        
        event = FeedbackEvent(
            decision_id=decision_id,
            feedback_type=feedback_type,
            context={'source': 'implicit', 'user_action': user_action, **decision_context},
            timestamp=datetime.now(timezone.utc).isoformat(),
            immediate_action_taken="pending"
        )
        
        action = self._process_feedback(event)
        event.immediate_action_taken = action
        
        self._log_feedback(event)
        self._update_decision_outcome(decision_id, feedback_type.value)
        
        return event
    
    def _parse_feedback(self, feedback_text: str) -> FeedbackType:
        """Parse user feedback text into type"""
        text_lower = feedback_text.lower()
        
        if any(word in text_lower for word in ['correct', 'right', 'good', 'fine', 'yes']):
            return FeedbackType.CORRECT
        elif any(word in text_lower for word in ['too strict', 'too harsh', 'unnecessary', 'false alarm']):
            return FeedbackType.TOO_STRICT
        elif any(word in text_lower for word in ['too lenient', 'should have blocked', 'missed', 'should have warned']):
            return FeedbackType.TOO_LENIENT
        else:
            return FeedbackType.UNCLEAR
    
    def _infer_feedback_from_behavior(self, user_action: str, context: Dict) -> Optional[FeedbackType]:
        """Infer feedback from user behavior"""
        decision_action = context.get('decision_action', '')
        
        # Behavioral inference rules
        if decision_action == 'WARN_AND_LOG':
            if user_action == 'edited_file':
                return FeedbackType.CORRECT  # Warning was valid
            elif user_action == 'said_fine':
                return FeedbackType.TOO_STRICT  # Warning unnecessary
        
        elif decision_action == 'BLOCK_OR_REQUIRE_REVIEW':
            if user_action == 'added_header':
                return FeedbackType.CORRECT  # Block was appropriate
            elif user_action == 'overrode':
                return FeedbackType.TOO_STRICT  # Block unnecessary
        
        elif decision_action == 'LOG_ONLY':
            if user_action == 'error_occurred':
                return FeedbackType.TOO_LENIENT  # Should have warned
            elif user_action == 'no_issues':
                return FeedbackType.CORRECT  # Was right to allow
        
        return None  # Ambiguous
    
    def _process_feedback(self, event: FeedbackEvent) -> str:
        """
        Process feedback and make immediate micro-adjustments.
        
        Philosophy: Small immediate adjustments (<5%) + nightly full calibration
        """
        actions = []
        
        if event.feedback_type == FeedbackType.TOO_STRICT:
            # I was too harsh - reduce sensitivity slightly
            actions.append(self._micro_adjust_thresholds(direction='lower', magnitude=0.02))
            actions.append(self._micro_adjust_temperature(direction='higher', magnitude=0.05))
            
        elif event.feedback_type == FeedbackType.TOO_LENIENT:
            # I was too loose - increase sensitivity slightly
            actions.append(self._micro_adjust_thresholds(direction='higher', magnitude=0.02))
            actions.append(self._micro_adjust_temperature(direction='lower', magnitude=0.05))
        
        elif event.feedback_type == FeedbackType.CORRECT:
            # Reinforce current calibration
            actions.append("reinforced_current_calibration")
        
        # Check for systematic patterns
        pattern = self._detect_systematic_pattern(event)
        if pattern:
            actions.append(f"pattern_detected: {pattern}")
            self._log_pattern_to_meta_learning(pattern, event)
        
        return " | ".join(actions) if actions else "no_immediate_action"
    
    def _micro_adjust_thresholds(self, direction: str, magnitude: float) -> str:
        """Make small immediate threshold adjustments"""
        adjustment = magnitude if direction == 'higher' else -magnitude
        
        for threshold_name in self.registry.get('probabilistic_thresholds', {}):
            threshold_config = self.registry['probabilistic_thresholds'][threshold_name]
            if threshold_config.get('auto_adjust', False):
                old_value = threshold_config['value']
                new_value = max(0.30, min(0.95, old_value + adjustment))
                threshold_config['value'] = round(new_value, 3)
        
        self._save_registry()
        return f"thresholds_{direction}_{magnitude}"
    
    def _micro_adjust_temperature(self, direction: str, magnitude: float) -> str:
        """Make small immediate temperature adjustments"""
        current = self.registry['calibration_parameters']['temperature']['value']
        adjustment = magnitude if direction == 'higher' else -magnitude
        new_temp = max(0.5, min(2.0, current + adjustment))
        
        self.registry['calibration_parameters']['temperature']['value'] = round(new_temp, 2)
        self._save_registry()
        
        return f"temperature_{direction}_{magnitude}"
    
    def _detect_systematic_pattern(self, event: FeedbackEvent) -> Optional[str]:
        """
        Detect if this feedback is part of a systematic pattern.
        
        Returns:
            Description of pattern if detected, None otherwise
        """
        # Look for patterns in recent feedback history
        recent_feedback = [
            f for f in self.feedback_history[-20:]  # Last 20 feedbacks
            if f.get('feedback_type') == event.feedback_type.value
        ]
        
        if len(recent_feedback) < 5:
            return None  # Not enough for pattern
        
        # Check for context patterns
        contexts = [f.get('context', {}) for f in recent_feedback]
        
        # Pattern 1: Same file type repeatedly
        file_types = [c.get('file_type') for c in contexts if c.get('file_type')]
        if file_types and len(set(file_types)) == 1 and len(file_types) >= 5:
            return f"repeated_{event.feedback_type.value}_for_{file_types[0]}"
        
        # Pattern 2: Same directory repeatedly
        file_paths = [c.get('file_path', '') for c in contexts]
        common_dirs = ['/'.join(p.split('/')[:2]) for p in file_paths if p]
        if common_dirs and len(set(common_dirs)) == 1 and len(common_dirs) >= 5:
            return f"repeated_{event.feedback_type.value}_in_{common_dirs[0]}"
        
        # Pattern 3: General trend (>70% of recent feedback is same type)
        if len(recent_feedback) / len(self.feedback_history[-20:]) > 0.7:
            return f"systematic_{event.feedback_type.value}_trend"
        
        return None
    
    def _log_pattern_to_meta_learning(self, pattern: str, event: FeedbackEvent):
        """Log detected pattern to meta-learning log"""
        log_entry = f"""
## {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} - Pattern Detected in Probabilistic Governance

**Pattern:** {pattern}
**Feedback Type:** {event.feedback_type.value}
**Context:** {json.dumps(event.context, indent=2)}

**Learning Action:** Adjusting model weights/thresholds to address systematic pattern.

---
"""
        
        try:
            with open(self.meta_learning_log, 'a') as f:
                f.write(log_entry)
        except Exception:
            pass
    
    def _log_feedback(self, event: FeedbackEvent):
        """Log feedback event to telemetry"""
        record = {
            'decision_id': event.decision_id,
            'feedback_type': event.feedback_type.value,
            'context': event.context,
            'timestamp': event.timestamp,
            'immediate_action': event.immediate_action_taken
        }
        
        self.feedback_history.append(record)
        
        try:
            with open(self.feedback_log_path, 'a') as f:
                f.write(json.dumps(record) + '\n')
        except Exception:
            pass
    
    def _update_decision_outcome(self, decision_id: str, outcome: str):
        """Update outcome in original decision log"""
        # Read all decisions
        if not self.telemetry_path.exists():
            return
        
        decisions = []
        with open(self.telemetry_path) as f:
            for line in f:
                try:
                    decision = json.loads(line.strip())
                    if decision.get('decision_id') == decision_id:
                        decision['outcome'] = outcome
                        decision['outcome_timestamp'] = datetime.now(timezone.utc).isoformat()
                    decisions.append(decision)
                except json.JSONDecodeError:
                    continue
        
        # Write back
        with open(self.telemetry_path, 'w') as f:
            for decision in decisions:
                f.write(json.dumps(decision) + '\n')
    
    def _save_registry(self):
        """Save updated registry"""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error("Error saving registry", error=str(e))
    
    def get_feedback_summary(self, days: int = 7) -> Dict:
        """
        Generate summary of recent feedback.
        
        Returns:
            Summary statistics for monitoring
        """
        recent = self.feedback_history[-100:]  # Last 100 feedbacks
        
        summary = {
            'total_feedbacks': len(recent),
            'by_type': {},
            'patterns_detected': [],
            'avg_response_time_hours': 0.0
        }
        
        for feedback_type in FeedbackType:
            count = sum(1 for f in recent if f.get('feedback_type') == feedback_type.value)
            summary['by_type'][feedback_type.value] = count
        
        return summary


# CLI interface for testing
if __name__ == '__main__':
    import sys
    
    collector = FeedbackCollector()
    
    if len(sys.argv) < 3:
        logger.info("Usage: python feedback_collector.py <decision_id> <feedback>")
        logger.info("Feedback: correct | too_strict | too_lenient")
        sys.exit(1)
    
    decision_id = sys.argv[1]
    feedback = sys.argv[2]
    
    event = collector.record_explicit_feedback(decision_id, feedback)
    
    logger.info("Feedback recorded",
                feedback_type=event.feedback_type.value,
                immediate_action=event.immediate_action_taken,
                logged_to=str(collector.feedback_log_path))

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "CUR-OPER-049",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "auth", "data-models", "dataclass", "event-driven", "filesystem", "logging", "metrics", "migration", "monitoring"],
    "keywords": ["collector", "event", "explicit", "feedback", "implicit", "record", "summary"],
    "business_value": "Provides feedback collector components including FeedbackType, FeedbackEvent, FeedbackCollector",
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
