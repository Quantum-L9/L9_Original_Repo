"""
L9 Research Department - Perplexity Client
Version: 3.0.0

Production Perplexity API client with best practices codified.

Best Practices (from Perplexity docs):
1. Be specific and contextual - 2-3 extra words dramatically improve results
2. Avoid few-shot prompting - confuses search
3. Use API parameters, not prompt instructions for search control
4. One focused topic per query
5. Think like a web search user
6. Explicit limitations: "If you cannot find reliable sources, say so"

v3.0.0: Added retry logic with exponential backoff for transient failures
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Perplexity Client",
    "module_version": "3.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "data_models",
    "module_name": "perplexity_client",
    "type": "dataclass",
    "status": "production",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API"],
        "memory_layers": [],
        "imported_by": ["services.research.tools.__init__", "services.research.tools.tool_wrappers"],
    },
}
# ============================================================================

import structlog
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx

from core.resilience.retry import async_retry, AsyncRetryConfig
from core.decorators import must_stay_async

log = structlog.get_logger(__name__)

# Retry configuration for Perplexity API (longer timeouts for deep research)
PERPLEXITY_RETRY_CONFIG = AsyncRetryConfig(
    max_retries=3,
    base_backoff=1.0,  # Slightly longer base for API rate limits
    max_backoff=30.0,
    jitter=0.2,
)


class PerplexityModel(str, Enum):
    """Available Perplexity models with use cases."""

    # Fast, cheap - quick facts, simple queries
    SONAR = "sonar"

    # Deep citations, comprehensive research
    SONAR_PRO = "sonar-pro"

    # Logical reasoning, chain-of-thought
    SONAR_REASONING = "sonar-reasoning"

    # Expert-level reasoning and synthesis
    SONAR_REASONING_PRO = "sonar-reasoning-pro"

    # Autonomous multi-step research (2-5 min, 50+ sources)
    SONAR_DEEP_RESEARCH = "sonar-deep-research"


class SearchContextSize(str, Enum):
    """Search context size - controls how much web content is retrieved."""

    LOW = "low"  # Faster, fewer sources
    MEDIUM = "medium"  # Balanced (default)
    HIGH = "high"  # More sources, deeper search


@dataclass
class PerplexityRequest:
    """
    Structured Perplexity API request.

    Enforces best practices by design.
    """

    # The focused query - should be ONE topic, search-friendly
    query: str

    # Model selection based on task
    model: PerplexityModel = PerplexityModel.SONAR_PRO

    # API parameters (NOT prompt-based)
    search_context_size: SearchContextSize = SearchContextSize.MEDIUM
    search_domain_filter: list[str] = field(
        default_factory=list
    )  # e.g., ["docs.python.org"]
    search_recency_filter: Optional[str] = None  # "day", "week", "month", "year"

    # Response control
    temperature: float = 0.2
    max_tokens: int = 4000

    # System context (kept minimal per best practices)
    system_context: Optional[str] = None

    def validate(self) -> list[str]:
        """Validate request against best practices."""
        issues = []

        # Check query length (too short = vague)
        if len(self.query.split()) < 5:
            issues.append(
                "Query too short - add 2-3 words of context for better results"
            )

        # Check for few-shot patterns
        if "example:" in self.query.lower() or "for instance:" in self.query.lower():
            issues.append("Avoid few-shot examples in query - confuses search")

        # Check for multi-part requests
        if self.query.count("?") > 2:
            issues.append("Multiple questions detected - split into separate queries")

        # Check for prompt-based search control
        bad_patterns = ["only search", "search only", "use only", "don't search"]
        if any(p in self.query.lower() for p in bad_patterns):
            issues.append(
                "Use search_domain_filter parameter instead of prompt instructions"
            )

        return issues


@dataclass
class PerplexityResponse:
    """Structured Perplexity API response."""

    success: bool
    content: str
    citations: list[str]
    model: str
    tokens_used: int
    cost: float
    error: Optional[str] = None
    search_results: list[dict] = field(default_factory=list)


class PerplexityClient:
    """
    Production Perplexity API client.

    Codifies all best practices from Perplexity documentation.
    """

    BASE_URL = "https://api.perplexity.ai"

    # Rate limits by model (requests per minute)
    RATE_LIMITS = {
        PerplexityModel.SONAR: 50,
        PerplexityModel.SONAR_PRO: 50,
        PerplexityModel.SONAR_REASONING: 50,
        PerplexityModel.SONAR_REASONING_PRO: 50,
        PerplexityModel.SONAR_DEEP_RESEARCH: 5,  # Much lower!
    }

    def __init__(self, api_key: str):
        """Initialize client with API key."""
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    @must_stay_async("async context manager protocol")
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0)  # 5 min for deep research
        )
        return self

    async def __aexit__(self, *args):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def search(self, request: PerplexityRequest) -> PerplexityResponse:
        """
        Execute search with best practices enforced.

        Args:
            request: Validated PerplexityRequest

        Returns:
            PerplexityResponse with results
        """
        # Validate request
        issues = request.validate()
        if issues:
            log.warning(
                "perplexity_request_issues", issues=issues, query=request.query[:50]
            )

        # Build payload
        payload = self._build_payload(request)

        log.info(
            "perplexity_search_start",
            model=request.model.value,
            query_preview=request.query[:80],
            context_size=request.search_context_size.value,
        )

        try:
            if not self._client:
                self._client = httpx.AsyncClient(timeout=300.0)

            async def _make_request():
                """Inner function for retry logic."""
                response = await self._client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                # 5xx errors are transient - raise to trigger retry
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Server error {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                # 4xx errors are not retryable - return error response
                if response.status_code >= 400:
                    error_text = response.text[:500]
                    log.error(
                        "perplexity_error",
                        status=response.status_code,
                        error=error_text,
                    )
                    return PerplexityResponse(
                        success=False,
                        content="",
                        citations=[],
                        model=request.model.value,
                        tokens_used=0,
                        cost=0.0,
                        error=f"HTTP {response.status_code}: {error_text}",
                    )

                data = response.json()
                return self._parse_response(data, request.model)

            # Execute with retry for transient errors (timeouts, connection errors, 5xx)
            return await async_retry(
                _make_request,
                config=PERPLEXITY_RETRY_CONFIG,
                operation=f"perplexity_search_{request.model.value}",
                retry_on=(
                    httpx.TimeoutException,
                    httpx.ConnectError,
                    httpx.HTTPStatusError,
                ),
            )

        except httpx.TimeoutException:
            log.error("perplexity_timeout", model=request.model.value)
            return PerplexityResponse(
                success=False,
                content="",
                citations=[],
                model=request.model.value,
                tokens_used=0,
                cost=0.0,
                error="Request timed out after retries (deep research can take 2-5 minutes)",
            )
        except Exception as e:
            log.error("perplexity_exception", error=str(e))
            return PerplexityResponse(
                success=False,
                content="",
                citations=[],
                model=request.model.value,
                tokens_used=0,
                cost=0.0,
                error=str(e),
            )

    def _build_payload(self, request: PerplexityRequest) -> dict[str, Any]:
        """Build API payload with best practices."""

        messages = []

        # Minimal system message (per best practices - avoid complex prompts)
        if request.system_context:
            messages.append(
                {
                    "role": "system",
                    "content": request.system_context,
                }
            )

        # User query - should already be focused and specific
        messages.append(
            {
                "role": "user",
                "content": request.query,
            }
        )

        payload: dict[str, Any] = {
            "model": request.model.value,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        # Add web search options (API params, not prompt-based)
        web_search_options: dict[str, Any] = {}

        if request.search_context_size != SearchContextSize.MEDIUM:
            web_search_options["search_context_size"] = (
                request.search_context_size.value
            )

        if request.search_domain_filter:
            web_search_options["search_domain_filter"] = request.search_domain_filter

        if request.search_recency_filter:
            web_search_options["search_recency_filter"] = request.search_recency_filter

        if web_search_options:
            payload["web_search_options"] = web_search_options

        return payload

    def _parse_response(self, data: dict, model: PerplexityModel) -> PerplexityResponse:
        """Parse API response into structured format."""

        choices = data.get("choices", [])
        content = choices[0]["message"]["content"] if choices else ""

        citations = data.get("citations", [])
        search_results = data.get("search_results", [])

        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)
        cost_info = usage.get("cost", {})
        total_cost = (
            cost_info.get("total_cost", 0.0) if isinstance(cost_info, dict) else 0.0
        )

        log.info(
            "perplexity_search_complete",
            model=model.value,
            citations=len(citations),
            tokens=tokens_used,
            cost=total_cost,
        )

        return PerplexityResponse(
            success=True,
            content=content,
            citations=citations,
            model=model.value,
            tokens_used=tokens_used,
            cost=total_cost,
            search_results=search_results,
        )

    # -----------------------------------------------------------------
    # Convenience methods for common research patterns
    # -----------------------------------------------------------------

    async def quick_search(self, query: str) -> PerplexityResponse:
        """
        Quick factual search using Sonar.

        Best for: definitions, quick facts, simple lookups.
        """
        return await self.search(
            PerplexityRequest(
                query=query,
                model=PerplexityModel.SONAR,
                search_context_size=SearchContextSize.LOW,
            )
        )

    async def research(
        self,
        query: str,
        domains: Optional[list[str]] = None,
    ) -> PerplexityResponse:
        """
        Standard research using Sonar Pro.

        Best for: comprehensive research, multiple citations needed.
        """
        return await self.search(
            PerplexityRequest(
                query=query,
                model=PerplexityModel.SONAR_PRO,
                search_context_size=SearchContextSize.HIGH,
                search_domain_filter=domains or [],
            )
        )

    async def analyze(self, query: str) -> PerplexityResponse:
        """
        Reasoning-based analysis using Sonar Reasoning Pro.

        Best for: comparisons, evaluations, logical analysis.
        """
        return await self.search(
            PerplexityRequest(
                query=query,
                model=PerplexityModel.SONAR_REASONING_PRO,
                search_context_size=SearchContextSize.HIGH,
            )
        )

    async def deep_research(self, query: str) -> PerplexityResponse:
        """
        Autonomous deep research using Sonar Deep Research.

        WARNING: Takes 2-5 minutes, costs $0.50-$2.00 per request.
        Rate limit: 5 requests per minute.

        Best for: comprehensive reports, 50+ sources, expert analysis.
        """
        log.warning(
            "deep_research_started",
            note="This will take 2-5 minutes and cost $0.50-$2.00",
        )
        return await self.search(
            PerplexityRequest(
                query=query,
                model=PerplexityModel.SONAR_DEEP_RESEARCH,
                max_tokens=8000,  # Deep research generates long reports
            )
        )


# -----------------------------------------------------------------
# Factory function for easy initialization
# -----------------------------------------------------------------


def get_perplexity_client() -> Optional[PerplexityClient]:
    """
    Get configured Perplexity client from environment.

    Returns None if API key not configured.
    """
    import os

    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        log.warning("perplexity_not_configured", hint="Set PERPLEXITY_API_KEY")
        return None
    return PerplexityClient(api_key)

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-008",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators", "core.resilience.retry"],
    "tags": ["async", "auth", "client", "data-models", "dataclass", "http-client", "logging", "messaging", "operations"],
    "keywords": ["analyze", "best", "client", "deep", "model", "perplexity", "practices", "quick"],
    "business_value": "Provides perplexity client components including PerplexityModel, SearchContextSize, PerplexityRequest",
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
