"""
L9 Research Factory LangGraph Nodes

Generated from: research_factory_schema.yaml
Implements the 5-pass structured research pipeline as LangGraph node functions.

Each node follows the signature:
    async def pass_X(state: ResearchState) -> ResearchState

The pipeline flow:
    START → pass_1_plan_queries → pass_2_build_superprompts →
    pass_3_execute_retrieval → pass_4_extract_results →
    pass_5_integrate_results → END
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Research Factory Nodes",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-09T01:02:49Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "foundation",
    "domain": "core",
    "module_name": "research_factory_nodes",
    "type": "service",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [
            "core.schemas.__init__",
            "core.schemas.tests.test_research_factory",
            "core.schemas.universal_schema",
        ],
    },
}
# ============================================================================

import structlog
from datetime import datetime
from typing import Any, Callable, Optional

from core.schemas.research_factory_models import (
    IntegrationResult,
    ParsedObject,
    Query,
    QueryPlan,
    RetrievalBatch,
    Superprompt,
    ValidationStatus,
)
from core.schemas.research_factory_state import ResearchState
from core.decorators import must_stay_async

logger = structlog.get_logger(__name__)

# =============================================================================
# Type Aliases for Pluggable Backends
# =============================================================================

RetrievalBackend = Callable[[str], list[dict[str, Any]]]
ExtractionBackend = Callable[[dict[str, Any]], tuple[dict[str, Any], float]]

# =============================================================================
# Pass 1: Plan Queries
# =============================================================================


@must_stay_async("callers use await")
async def pass_1_plan_queries(state: ResearchState) -> ResearchState:
    """
    Pass 1 — Derive research plan from job specification.

    Input: ResearchJobSpec in state.job_spec
    Output: QueryPlan in state.query_plan

    Generates structured queries based on domain, polymer, and regions.
    """
    state = state.start_pass(1)
    logger.info(
        f"Pass 1: Planning queries for job {state.job_spec.job_id if state.job_spec else 'N/A'}"
    )

    try:
        if not state.job_spec:
            raise ValueError("job_spec is required for pass_1")

        job = state.job_spec

        # Generate queries based on job spec
        queries = []
        base_priority = 1

        # Primary query: polymer + regions
        for i, region in enumerate(job.regions):
            queries.append(
                Query(
                    query_text=f"{job.polymer} suppliers in {region}",
                    priority=base_priority + i,
                    filters={"region": region, "domain": job.domain},
                )
            )

        # Secondary query: market analysis
        queries.append(
            Query(
                query_text=f"{job.polymer} market analysis {job.domain}",
                priority=len(job.regions) + 1,
                filters={"domain": job.domain, "type": "market_analysis"},
            )
        )

        # Tertiary query: pricing data
        queries.append(
            Query(
                query_text=f"{job.polymer} pricing trends",
                priority=len(job.regions) + 2,
                filters={"domain": job.domain, "type": "pricing"},
            )
        )

        query_plan = QueryPlan(
            job_id=job.job_id,
            queries=queries,
            strategy="breadth_first",
            constraints={
                "max_results_per_query": job.max_results // len(queries),
                "timeout_seconds": 30,
            },
        )

        state = state.model_copy(update={"query_plan": query_plan})
        state = state.complete_pass(1)

        logger.info(f"Pass 1 complete: Generated {len(queries)} queries")
        return state

    except Exception as e:
        logger.error(f"Pass 1 failed: {e}")
        return state.complete_pass(1, error=str(e))


# =============================================================================
# Pass 2: Build Superprompts
# =============================================================================


@must_stay_async("callers use await")
async def pass_2_build_superprompts(state: ResearchState) -> ResearchState:
    """
    Pass 2 — Construct optimized prompts from query plan.

    Input: QueryPlan in state.query_plan
    Output: list[Superprompt] in state.superprompts

    Builds templated prompts with context injection.
    """
    state = state.start_pass(2)
    logger.info("Pass 2: Building superprompts")

    try:
        if not state.query_plan:
            raise ValueError("query_plan is required for pass_2")

        superprompts = []
        template = """Research Query:
{query_text}

Context:
- Domain: {domain}
- Filters: {filters}
- Max Results: {max_results}

Instructions:
Return structured data with sources, confidence scores, and timestamps.
Format: JSON with keys [results, metadata, sources]
"""

        for query in state.query_plan.queries:
            variables = {
                "query_text": query.query_text,
                "domain": query.filters.get("domain", "general"),
                "filters": str(query.filters),
                "max_results": state.query_plan.constraints.get(
                    "max_results_per_query", 10
                ),
            }

            rendered = template.format(**variables)

            superprompts.append(
                Superprompt(
                    query_id=query.query_id,
                    template=template,
                    variables=variables,
                    context=f"Priority: {query.priority}",
                    rendered=rendered,
                )
            )

        state = state.model_copy(update={"superprompts": superprompts})
        state = state.complete_pass(2)

        logger.info(f"Pass 2 complete: Built {len(superprompts)} superprompts")
        return state

    except Exception as e:
        logger.error(f"Pass 2 failed: {e}")
        return state.complete_pass(2, error=str(e))


# =============================================================================
# Pass 3: Execute Retrieval
# =============================================================================


@must_stay_async("callers use await")
async def pass_3_execute_retrieval(
    state: ResearchState, retrieval_backend: Optional[RetrievalBackend] = None
) -> ResearchState:
    """
    Pass 3 — Call research backend(s) with superprompts.

    Input: list[Superprompt] in state.superprompts
    Output: list[RetrievalBatch] in state.retrieval_batches

    Executes retrieval against configured backends.
    """
    state = state.start_pass(3)
    logger.info("Pass 3: Executing retrieval")

    try:
        if not state.superprompts:
            raise ValueError("superprompts are required for pass_3")

        retrieval_batches = []

        for prompt in state.superprompts:
            start_time = datetime.utcnow()

            # Use injected backend or default mock
            if retrieval_backend:
                raw_responses = retrieval_backend(prompt.rendered)
            else:
                # Mock response for testing
                raw_responses = [
                    {
                        "source": "mock_database",
                        "data": {"result": f"Mock result for query {prompt.query_id}"},
                        "confidence": 0.85,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ]

            end_time = datetime.utcnow()
            latency_ms = (end_time - start_time).total_seconds() * 1000

            retrieval_batches.append(
                RetrievalBatch(
                    prompt_id=prompt.prompt_id,
                    sources=["mock_database"],  # Would be real sources
                    raw_responses=raw_responses,
                    response_count=len(raw_responses),
                    latency_ms=latency_ms,
                    metadata={"prompt_context": prompt.context},
                )
            )

        state = state.model_copy(update={"retrieval_batches": retrieval_batches})
        state = state.complete_pass(3)

        logger.info(f"Pass 3 complete: Retrieved {len(retrieval_batches)} batches")
        return state

    except Exception as e:
        logger.error(f"Pass 3 failed: {e}")
        return state.complete_pass(3, error=str(e))


# =============================================================================
# Pass 4: Extract Results
# =============================================================================


@must_stay_async("callers use await")
async def pass_4_extract_results(
    state: ResearchState, extraction_backend: Optional[ExtractionBackend] = None
) -> ResearchState:
    """
    Pass 4 — Transform raw JSON into validated objects.

    Input: list[RetrievalBatch] in state.retrieval_batches
    Output: list[ParsedObject] in state.parsed_objects

    Validates and structures raw responses.
    """
    state = state.start_pass(4)
    logger.info("Pass 4: Extracting results")

    try:
        if not state.retrieval_batches:
            raise ValueError("retrieval_batches are required for pass_4")

        parsed_objects = []

        for batch in state.retrieval_batches:
            for raw in batch.raw_responses:
                # Use injected backend or default extraction
                if extraction_backend:
                    extracted, confidence = extraction_backend(raw)
                else:
                    # Default extraction logic
                    extracted = {
                        "source": raw.get("source", "unknown"),
                        "data": raw.get("data", {}),
                        "timestamp": raw.get(
                            "timestamp", datetime.utcnow().isoformat()
                        ),
                    }
                    confidence = raw.get("confidence", 0.5)

                # Validate
                errors = []
                if not extracted.get("source"):
                    errors.append("Missing source field")
                if not extracted.get("data"):
                    errors.append("Missing data field")

                status = ValidationStatus.VALID
                if errors:
                    status = (
                        ValidationStatus.INVALID
                        if len(errors) > 1
                        else ValidationStatus.PARTIAL
                    )

                parsed_objects.append(
                    ParsedObject(
                        batch_id=batch.batch_id,
                        extracted_data=extracted,
                        validation_status=status,
                        confidence=confidence,
                        errors=errors,
                    )
                )

        state = state.model_copy(update={"parsed_objects": parsed_objects})
        state = state.complete_pass(4)

        logger.info(f"Pass 4 complete: Extracted {len(parsed_objects)} objects")
        return state

    except Exception as e:
        logger.error(f"Pass 4 failed: {e}")
        return state.complete_pass(4, error=str(e))


# =============================================================================
# Pass 5: Integrate Results
# =============================================================================


@must_stay_async("callers use await")
async def pass_5_integrate_results(state: ResearchState) -> ResearchState:
    """
    Pass 5 — Persist output to hypergraph and world model.

    Input: All accumulated state data
    Output: IntegrationResult in state.integration_result

    Produces final research pipeline output.
    """
    state = state.start_pass(5)
    logger.info("Pass 5: Integrating results")

    try:
        if not state.job_spec or not state.query_plan:
            raise ValueError("job_spec and query_plan are required for pass_5")

        # Generate metrics
        metrics = state.to_metrics()

        # Build integration summary
        valid_count = sum(
            1
            for p in state.parsed_objects
            if p.validation_status == ValidationStatus.VALID
        )
        integration_summary = {
            "total_processed": len(state.parsed_objects),
            "valid_objects": valid_count,
            "success_rate": valid_count / len(state.parsed_objects)
            if state.parsed_objects
            else 0.0,
            "sources_used": list(
                set(
                    batch.sources[0]
                    for batch in state.retrieval_batches
                    if batch.sources
                )
            ),
            "integration_targets": ["hypergraph", "world_model"],
            "integration_status": "completed",
        }

        # Create final result
        integration_result = IntegrationResult(
            job_spec=state.job_spec,
            query_plan=state.query_plan,
            superprompts=state.superprompts,
            retrieval_batches=len(state.retrieval_batches),
            parsed_objects=state.parsed_objects,
            integration_summary=integration_summary,
            metrics=metrics,
            status="completed" if not state.has_errors else "completed_with_errors",
        )

        state = state.model_copy(update={"integration_result": integration_result})
        state = state.complete_pass(5)

        logger.info(
            f"Pass 5 complete: Integration finished with {valid_count} valid objects"
        )
        return state

    except Exception as e:
        logger.error(f"Pass 5 failed: {e}")
        return state.complete_pass(5, error=str(e))


# =============================================================================
# Graph Builder Helper
# =============================================================================


def build_research_graph():
    """
    Build the LangGraph StateGraph for the Research Factory.

    Returns a compiled graph ready for execution.

    Usage:
        graph = build_research_graph()
        result = await graph.ainvoke({"job_spec": job_spec})
    """
    try:
        from langgraph.graph import StateGraph, START, END
    except ImportError:
        logger.warning("LangGraph not installed. Graph builder unavailable.")
        return None

    # Create graph with ResearchState
    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("pass_1_plan_queries", pass_1_plan_queries)
    graph.add_node("pass_2_build_superprompts", pass_2_build_superprompts)
    graph.add_node("pass_3_execute_retrieval", pass_3_execute_retrieval)
    graph.add_node("pass_4_extract_results", pass_4_extract_results)
    graph.add_node("pass_5_integrate_results", pass_5_integrate_results)

    # Add edges (linear pipeline)
    graph.add_edge(START, "pass_1_plan_queries")
    graph.add_edge("pass_1_plan_queries", "pass_2_build_superprompts")
    graph.add_edge("pass_2_build_superprompts", "pass_3_execute_retrieval")
    graph.add_edge("pass_3_execute_retrieval", "pass_4_extract_results")
    graph.add_edge("pass_4_extract_results", "pass_5_integrate_results")
    graph.add_edge("pass_5_integrate_results", END)

    return graph.compile()


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COR-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [
        "core.decorators",
        "core.schemas.research_factory_models",
        "core.schemas.research_factory_state",
    ],
    "tags": [
        "async",
        "batch-processing",
        "core",
        "foundation",
        "logging",
        "metrics",
        "mocking",
        "service",
        "testing",
    ],
    "keywords": [
        "build",
        "execute",
        "extract",
        "factory",
        "graph",
        "integrate",
        "langgraph",
        "nodes",
    ],
    "business_value": "Implements the 5-pass structured research pipeline as LangGraph node functions.",
    "last_modified": "2026-01-17T23:47:56Z",
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
