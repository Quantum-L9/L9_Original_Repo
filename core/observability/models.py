"""
Observability data models and span definitions.

Defines all Pydantic models for traces, spans, metrics, failures, and KPIs.
"""

from typing import Optional, Any, Dict, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class SpanKind(str, Enum):
    """Kind of span."""
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"
    # Kernel lifecycle spans (v3.4+ / GMP-KERNEL-BOOT)
    KERNEL_LOAD = "KERNEL_LOAD"
    KERNEL_INTEGRITY_CHECK = "KERNEL_INTEGRITY_CHECK"
    KERNEL_ACTIVATION = "KERNEL_ACTIVATION"
    KERNEL_RELOAD = "KERNEL_RELOAD"
    KERNEL_EVOLUTION = "KERNEL_EVOLUTION"


class SpanStatus(str, Enum):
    """Span execution status."""
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


class FailureClass(str, Enum):
    """Classification of failures."""
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_ERROR = "TOOL_ERROR"
    CONTEXT_WINDOW_EXCEEDED = "CONTEXT_WINDOW_EXCEEDED"
    LLM_HALLUCINATION = "LLM_HALLUCINATION"
    GOVERNANCE_DENIED = "GOVERNANCE_DENIED"
    EXTERNAL_API_TIMEOUT = "EXTERNAL_API_TIMEOUT"
    PLANNING_FAILURE = "PLANNING_FAILURE"
    COST_CONSTRAINT_BREACH = "COST_CONSTRAINT_BREACH"
    LLM_CONTENT_FILTER = "LLM_CONTENT_FILTER"
    TOKEN_LIMIT = "TOKEN_LIMIT"
    RATE_LIMIT = "RATE_LIMIT"
    UNKNOWN = "UNKNOWN"


class TraceContext(BaseModel):
    """W3C-compatible trace context."""
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()).replace("-", ""))
    span_id: str = Field(default_factory=lambda: str(uuid.uuid4()).replace("-", "")[:16])
    parent_span_id: Optional[str] = None
    is_sampled: bool = True
    user_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None

    def child_context(self) -> "TraceContext":
        """Create a child context with new span_id."""
        return TraceContext(
            trace_id=self.trace_id,
            parent_span_id=self.span_id,
            is_sampled=self.is_sampled,
            user_id=self.user_id,
            task_id=self.task_id,
            agent_id=self.agent_id,
        )

    def to_headers(self) -> Dict[str, str]:
        """Convert to W3C traceparent header."""
        version = "00"
        trace_flags = "01" if self.is_sampled else "00"
        return {
            "traceparent": f"{version}-{self.trace_id}-{self.span_id}-{trace_flags}"
        }


class Span(BaseModel):
    """Core span model."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    kind: SpanKind = SpanKind.INTERNAL
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    error: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)

    def finish(self, status: SpanStatus = SpanStatus.OK, error: Optional[str] = None) -> None:
        """Mark span as finished."""
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
        self.error = error

    @classmethod
    def start(
        cls,
        name: str,
        trace_id: str,
        parent_span_id: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        **attributes: Any,
    ) -> "Span":
        """Create and start a new span.
        
        For subclasses with required fields (e.g., ToolCallSpan.tool_name),
        those fields are extracted from attributes and passed directly.
        """
        span_id = str(uuid.uuid4()).replace("-", "")[:16]
        
        # Build base kwargs
        kwargs: Dict[str, Any] = {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "name": name,
            "kind": kind,
            "start_time": datetime.utcnow(),
        }
        
        # Extract subclass-specific fields from attributes
        # ToolCallSpan requires: tool_name, tool_input
        subclass_fields = {"tool_name", "tool_input", "tool_output", "tool_error",
                          "model", "prompt_tokens", "completion_tokens", "total_tokens",
                          "cost_usd", "temperature", "strategy", "tokens_used",
                          "tokens_available", "truncation_occurred", "overflow_event"}
        
        remaining_attrs = {}
        for key, value in attributes.items():
            if key in subclass_fields:
                kwargs[key] = value
            else:
                remaining_attrs[key] = value
        
        kwargs["attributes"] = remaining_attrs
        
        return cls(**kwargs)


class LLMGenerationSpan(Span):
    """Span for LLM generation."""
    model: str = "gpt-4"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    temperature: Optional[float] = None


class ToolCallSpan(Span):
    """Span for tool invocation."""
    tool_name: str
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    tool_output: Optional[Any] = None
    tool_error: Optional[str] = None


class ContextAssemblySpan(Span):
    """Span for context window assembly."""
    strategy: str = "recency_biased_window"
    tokens_used: int = 0
    tokens_available: int = 8000
    truncation_occurred: bool = False
    overflow_event: bool = False


class RAGRetrievalSpan(Span):
    """Span for RAG retrieval."""
    query: str
    top_k: int = 5
    chunks_retrieved: int = 0
    relevance_scores: List[float] = Field(default_factory=list)


class GovernanceCheckSpan(Span):
    """Span for governance policy check."""
    policy_name: str
    policy_result: str = "allow"  # allow, deny, review
    policy_reason: Optional[str] = None


class AgentTrajectorySpan(Span):
    """Root span for complete agent task execution."""
    agent_name: str
    task_kind: str
    max_iterations: int = 10
    current_iteration: int = 0
    success: Optional[bool] = None
    final_result: Optional[Any] = None


class KernelLifecycleSpan(Span):
    """Span for kernel lifecycle events (v3.4+ / GMP-KERNEL-BOOT)."""
    kernel_id: str
    kernel_version: Optional[str] = None
    kernel_hash: Optional[str] = None
    phase: str = "load"  # load, validate, activate, reload, evolve
    integrity_status: Optional[str] = None  # NEW, MODIFIED, UNCHANGED, DELETED
    rules_count: int = 0
    agent_id: Optional[str] = None
    kernel_count: int = 0

    @classmethod
    def start(
        cls,
        name: str,
        trace_id: str,
        kernel_id: str,
        parent_span_id: Optional[str] = None,
        kind: SpanKind = SpanKind.KERNEL_LOAD,
        **kwargs: Any,
    ) -> "KernelLifecycleSpan":
        """Create and start a new kernel lifecycle span."""
        span_id = str(uuid.uuid4()).replace("-", "")[:16]
        return cls(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            start_time=datetime.utcnow(),
            kernel_id=kernel_id,
            **kwargs,
        )


class FailureSignal(BaseModel):
    """Signal indicating a failure event."""
    failure_class: FailureClass
    span_id: str
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = Field(default_factory=dict)
    auto_recovery_applied: bool = False
    recovery_action: Optional[str] = None


class RemediationAction(BaseModel):
    """Action to remediate a failure."""
    action_type: str  # retry, fallback, summarize, degrade, escalate, etc.
    target: Optional[str] = None  # what to act on (tool name, model, etc.)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    applied: bool = False
    result: Optional[str] = None


class SREMetric(BaseModel):
    """SRE-level metric."""
    metric_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    value: float
    unit: str = ""
    dimensions: Dict[str, str] = Field(default_factory=dict)


class AgentKPI(BaseModel):
    """Agent performance KPI."""
    agent_name: str
    metric_name: str
    value: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    period: str = "1h"  # 1h, 1d, 1w
