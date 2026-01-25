import json
import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

import psycopg2
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """Tool availability states"""

    AVAILABLE = "available"
    AUTH_REQUIRED = "auth_required"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"


@dataclass
class ToolDefinition:
    """Complete tool specification"""

    id: str
    name: str
    description: str
    category: str
    subcategories: list[str]
    parameters: dict[str, Any]
    examples: list[dict[str, str]]
    tags: list[str]
    status: ToolStatus
    performance: dict[str, Any]  # latency_ms, throughput_qps, etc
    requirements: dict[str, Any]  # embeddings_available, auth, etc

    def to_embedding_text(self) -> str:
        """Construct optimal text for vector embedding"""
        parts = [
            self.description,
            f"Category: {self.category}",
            f"Tags: {', '.join(self.tags)}",
            f"Parameters: {', '.join(self.parameters.keys())}",
        ]

        # Add examples for semantic context
        if self.examples:
            parts.append(f"Example: {self.examples[0].get('description', '')}")

        return "\n".join(parts)


@dataclass
class DiscoveryResult:
    """Tool discovery result with confidence scores"""

    tool_id: str
    tool_name: str
    description: str
    similarity_score: float  # 0.0 to 1.0
    rank: int
    discovery_method: str  # "semantic", "keyword", "hybrid"
    token_budget_tokens: int
    is_available: bool
    auth_required: bool


class DynamicToolDiscoveryService:
    """
    Production-grade tool discovery with:
    - Semantic search (vector embeddings)
    - Keyword search (BM25/PostgreSQL full-text)
    - Hybrid fusion (RRF + confidence filtering)
    - Token budget management
    - Availability checking
    """

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        postgres_dsn: str = "postgresql://localhost/l9_tools",
        embedding_model: str = "all-MiniLM-L6-v2",
        tool_budget_tokens: int = 2000,
        confidence_threshold: float = 0.70,
        top_k_results: int = 5,
    ):
        """Initialize discovery service with all backends"""

        # Vector search backend
        self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        # Keyword search backend
        self.postgres_dsn = postgres_dsn
        self.postgres_conn = None

        # Configuration
        self.tool_budget_tokens = tool_budget_tokens
        self.confidence_threshold = confidence_threshold
        self.top_k_results = top_k_results

        # Tool registry cache
        self.tool_registry: dict[str, ToolDefinition] = {}
        self.tool_status_cache: dict[
            str, tuple[ToolStatus, float]
        ] = {}  # status, last_check_time

        logger.info(
            f"Initialized DynamicToolDiscoveryService with {embedding_dim}-dim embeddings"
        )

    def initialize_qdrant_collection(self, collection_name: str = "l9_tools"):
        """Create Qdrant collection if not exists"""
        try:
            self.qdrant.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' exists")
        except:
            self.qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim, distance=Distance.COSINE
                ),
            )
            logger.info(f"Created collection '{collection_name}'")

    def index_tools(
        self, tools: list[ToolDefinition], collection_name: str = "l9_tools"
    ):
        """Index tools with vector embeddings"""
        self.initialize_qdrant_collection(collection_name)

        points = []
        for i, tool in enumerate(tools):
            # Generate embedding text
            embed_text = tool.to_embedding_text()

            # Create vector
            vector = self.embedding_model.encode(embed_text).tolist()

            # Create point
            point = PointStruct(
                id=hash(tool.id) % (10**9),  # Convert string ID to integer
                vector=vector,
                payload={
                    "tool_id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category,
                    "tags": tool.tags,
                    "status": tool.status.value,
                    "performance": tool.performance,
                    "requirements": tool.requirements,
                },
            )
            points.append(point)

            # Cache tool definition
            self.tool_registry[tool.id] = tool

        # Upsert to Qdrant
        self.qdrant.upsert(collection_name=collection_name, points=points, wait=True)
        logger.info(f"Indexed {len(tools)} tools in Qdrant")

    def setup_postgres_hybrid_search(self):
        """Initialize PostgreSQL for hybrid BM25 + vector search"""
        conn = psycopg2.connect(self.postgres_dsn)
        cur = conn.cursor()

        # Enable extensions
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Create tools table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tools (
                id SERIAL PRIMARY KEY,
                tool_id VARCHAR(255) UNIQUE,
                name VARCHAR(255),
                description TEXT,
                category VARCHAR(100),
                tags TEXT[],
                parameters JSONB,
                embedding vector(384),
                status VARCHAR(50),
                performance JSONB,
                requirements JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Create BM25 index
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tools_bm25 ON tools
            USING bm25(description, name)
        """)

        # Create vector index
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tools_vector ON tools
            USING hnsw(embedding vector_cosine_ops)
        """)

        conn.commit()
        cur.close()
        self.postgres_conn = conn
        logger.info("PostgreSQL hybrid search initialized")

    def discover_tools_semantic(
        self, query: str, top_k: int | None = None, collection_name: str = "l9_tools"
    ) -> list[DiscoveryResult]:
        """
        Semantic tool discovery using vector similarity
        Fast (<100ms), high-quality results for semantic matching
        """
        top_k = top_k or self.top_k_results

        start_time = time.time()

        # Embed query
        query_vector = self.embedding_model.encode(query).tolist()

        # Search Qdrant
        search_results = self.qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k * 2,  # Retrieve more, then filter
            score_threshold=self.confidence_threshold,
        )

        # Convert to DiscoveryResult
        results = []
        for rank, point in enumerate(search_results):
            payload = point.payload

            # Check tool availability
            is_available = self._check_tool_availability(payload["tool_id"])

            result = DiscoveryResult(
                tool_id=payload["tool_id"],
                tool_name=payload["name"],
                description=payload["description"][:200],
                similarity_score=point.score,
                rank=rank,
                discovery_method="semantic",
                token_budget_tokens=self._estimate_tokens(payload),
                is_available=is_available,
                auth_required=payload["requirements"].get("auth", False),
            )
            results.append(result)

        latency_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Semantic discovery for '{query}': {len(results)} tools, {latency_ms:.1f}ms"
        )

        return results[:top_k]

    def discover_tools_hybrid(
        self,
        query: str,
        top_k: int | None = None,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ) -> list[DiscoveryResult]:
        """
        Hybrid tool discovery combining semantic + keyword search
        Robust to both conceptual and exact-match queries
        """
        top_k = top_k or self.top_k_results

        # Semantic search results
        semantic_results = self.discover_tools_semantic(query, top_k=top_k * 2)
        semantic_scores = {r.tool_id: r.similarity_score for r in semantic_results}

        # Keyword search (BM25) - requires PostgreSQL
        if not self.postgres_conn:
            logger.warning(
                "PostgreSQL not initialized, returning semantic results only"
            )
            return semantic_results[:top_k]

        keyword_results = self._discover_tools_bm25(query, top_k=top_k * 2)
        keyword_scores = {r.tool_id: r.similarity_score for r in keyword_results}

        # Hybrid fusion using weighted combination
        all_tool_ids = set(semantic_scores.keys()) | set(keyword_scores.keys())

        hybrid_scores = {}
        for tool_id in all_tool_ids:
            sem_score = semantic_scores.get(tool_id, 0.0)
            kw_score = keyword_scores.get(tool_id, 0.0)

            # Weighted combination
            hybrid_scores[tool_id] = (
                semantic_weight * sem_score + keyword_weight * kw_score
            )

        # Sort by hybrid score
        sorted_tools = sorted(hybrid_scores.items(), key=lambda x: x[-1], reverse=True)

        # Convert back to DiscoveryResult format
        results = []
        for rank, (tool_id, score) in enumerate(sorted_tools[:top_k]):
            # Get tool details from cache or registry
            tool = self.tool_registry.get(tool_id)
            if not tool:
                continue

            is_available = self._check_tool_availability(tool_id)

            result = DiscoveryResult(
                tool_id=tool_id,
                tool_name=tool.name,
                description=tool.description[:200],
                similarity_score=score,
                rank=rank,
                discovery_method="hybrid",
                token_budget_tokens=self._estimate_tokens(asdict(tool)),
                is_available=is_available,
                auth_required=tool.requirements.get("auth", False),
            )
            results.append(result)

        return results

    def _discover_tools_bm25(
        self, query: str, top_k: int = 10
    ) -> list[DiscoveryResult]:
        """BM25 keyword search using PostgreSQL"""
        cur = self.postgres_conn.cursor()

        # PostgreSQL full-text search with ranking
        cur.execute(
            """
            SELECT 
                tool_id, 
                name, 
                description,
                ts_rank(
                    to_tsvector('english', description),
                    plainto_tsquery('english', %s)
                ) as rank
            FROM tools
            WHERE to_tsvector('english', description) @@ 
                  plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
        """,
            (query, query, top_k),
        )

        results = []
        for i, row in enumerate(cur.fetchall()):
            result = DiscoveryResult(
                tool_id=row[0],
                tool_name=row[-1],
                description=row[-2][:200],
                similarity_score=row[-3],  # ts_rank output
                rank=i,
                discovery_method="keyword",
                token_budget_tokens=self._estimate_tokens({"description": row[-2]}),
                is_available=self._check_tool_availability(row[0]),
                auth_required=False,
            )
            results.append(result)

        cur.close()
        return results

    def _check_tool_availability(self, tool_id: str) -> bool:
        """Check if tool is available (auth valid, service online, etc)"""
        # Cache availability checks (30 second TTL)
        if tool_id in self.tool_status_cache:
            status, last_check = self.tool_status_cache[tool_id]
            if time.time() - last_check < 30:
                return status == ToolStatus.AVAILABLE

        # Default: assume available (in production, check actual service status)
        self.tool_status_cache[tool_id] = (ToolStatus.AVAILABLE, time.time())
        return True

    def _estimate_tokens(self, tool_data: dict[str, Any]) -> int:
        """Rough token estimation for tool spec (1 token ≈ 4 chars)"""
        text = json.dumps(tool_data)
        return len(text) // 4 + 50  # Add 50 for JSON overhead

    def select_tools_for_context(
        self,
        discovered_tools: list[DiscoveryResult],
        max_tokens: int = 2000,
        min_confidence: float = 0.70,
    ) -> list[ToolDefinition]:
        """
        Select tools to load into context, respecting token budget
        and confidence thresholds
        """
        selected = []
        tokens_used = 0

        for result in discovered_tools:
            # Skip low-confidence tools
            if result.similarity_score < min_confidence:
                continue

            # Skip unavailable tools
            if not result.is_available:
                logger.debug(f"Skipping unavailable tool: {result.tool_name}")
                continue

            # Check token budget
            if tokens_used + result.token_budget_tokens > max_tokens:
                logger.debug("Token budget exceeded, stopping tool selection")
                break

            # Get full tool definition
            tool = self.tool_registry.get(result.tool_id)
            if tool:
                selected.append(tool)
                tokens_used += result.token_budget_tokens

        logger.info(f"Selected {len(selected)} tools, {tokens_used} tokens used")
        return selected


class ToolContextFormatter:
    """Format discovered tools into LLM-ready prompt sections"""

    @staticmethod
    def format_tools_for_prompt(
        tools: list[ToolDefinition], max_chars: int = 8000
    ) -> str:
        """Format tools into optimized prompt text"""
        prompt_parts = ["# Available Tools\n"]

        for tool in tools:
            # Tool header
            prompt_parts.append(f"\n## {tool.name}\n")
            prompt_parts.append(f"**Category**: {tool.category}\n")
            prompt_parts.append(f"**Description**: {tool.description}\n")

            # Parameters
            if tool.parameters:
                prompt_parts.append("\n**Parameters**:\n")
                for param_name, param_spec in tool.parameters.items():
                    prompt_parts.append(
                        f"- `{param_name}`: {param_spec.get('type', 'any')}"
                    )
                    if param_spec.get("description"):
                        prompt_parts.append(f" - {param_spec['description']}")
                    prompt_parts.append("\n")

            # Example usage
            if tool.examples:
                prompt_parts.append("\n**Example**:\n")
                prompt_parts.append(f"```\n{tool.examples.get('call', '')}\n```\n")

        full_text = "".join(prompt_parts)

        # Truncate if needed
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n\n... (truncated)"

        return full_text


class L9AgentToolDiscoveryIntegration:
    """Integration point for L9 agent to use dynamic tool discovery"""

    def __init__(self, discovery_service: DynamicToolDiscoveryService):
        self.discovery = discovery_service
        self.formatter = ToolContextFormatter()

    def process_task_with_tool_discovery(
        self,
        task: str,
        llm_call_fn,
        system_prompt: str,
        max_tool_tokens: int = 2000,
        use_hybrid: bool = True,
    ) -> str:
        """
        Main execution flow: discover tools, load into context, invoke LLM
        """
        logger.info(f"Processing task: {task}")

        # PHASE 1: DISCOVERY
        if use_hybrid:
            discovered = self.discovery.discover_tools_hybrid(task, top_k=10)
        else:
            discovered = self.discovery.discover_tools_semantic(task, top_k=10)

        logger.info(f"Discovered {len(discovered)} tools")

        # PHASE 2: SELECTION
        selected_tools = self.discovery.select_tools_for_context(
            discovered, max_tokens=max_tool_tokens, min_confidence=0.70
        )

        # PHASE 3: FORMAT FOR PROMPT
        tools_section = self.formatter.format_tools_for_prompt(selected_tools)

        # PHASE 4: BUILD PROMPT
        full_prompt = f"""{system_prompt}

{tools_section}

## Task
{task}

Please use the available tools to complete this task.
"""

        # PHASE 5: INVOKE LLM
        response = llm_call_fn(full_prompt)

        logger.info("Task completed")
        return response


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Initialize discovery service
    discovery = DynamicToolDiscoveryService(
        qdrant_host="localhost",
        qdrant_port=6333,
        postgres_dsn="postgresql://user:password@localhost/l9_tools",
        tool_budget_tokens=2000,
        confidence_threshold=0.70,
        top_k_results=5,
    )

    # Load tools (would normally come from tool registry)
    sample_tools = [
        ToolDefinition(
            id="web_search",
            name="Web Search",
            description="Search the web for recent information and news",
            category="retrieval",
            subcategories=["information_retrieval", "search"],
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "int", "description": "Max results (default: 10)"},
            },
            examples=[
                {
                    "query": "latest AI news",
                    "call": "web_search(query='latest AI news', limit=5)",
                }
            ],
            tags=["search", "web", "news"],
            status=ToolStatus.AVAILABLE,
            performance={"latency_ms": 500, "throughput_qps": 100},
            requirements={"auth": True, "api_key_required": True},
        ),
        ToolDefinition(
            id="semantic_search",
            name="Semantic Vector Search",
            description="Search documents using vector embeddings for semantic similarity",
            category="retrieval",
            subcategories=["semantic_search", "embeddings"],
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "index": {"type": "string", "description": "Vector index name"},
                "limit": {"type": "int", "description": "Max results"},
            },
            examples=[
                {
                    "query": "find climate research",
                    "call": "semantic_search(query='climate research', index='papers', limit=10)",
                }
            ],
            tags=["vector", "semantic", "embeddings"],
            status=ToolStatus.AVAILABLE,
            performance={"latency_ms": 50, "throughput_qps": 500},
            requirements={"embeddings_available": True},
        ),
    ]

    # Index tools
    discovery.initialize_qdrant_collection()
    discovery.index_tools(sample_tools)

    # Discover tools for a task
    task = "Search for information about quantum computing breakthroughs"
    results = discovery.discover_tools_hybrid(task)

    print(f"\nDiscovered {len(results)} tools:")
    for result in results:
        print(
            f"  - {result.tool_name} (score: {result.similarity_score:.2f}, available: {result.is_available})"
        )

    # Select tools for context
    selected = discovery.select_tools_for_context(results, max_tokens=2000)
    print(f"\nSelected {len(selected)} tools for context")

    # Format for prompt
    formatter = ToolContextFormatter()
    prompt_section = formatter.format_tools_for_prompt(selected)
    print(f"\nPrompt section ({len(prompt_section)} chars):\n{prompt_section[:500]}...")
