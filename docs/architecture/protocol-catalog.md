# L9 Protocol Catalog

**Version:** 1.0.0
**GMP:** di-dip-phase1-abstractions
**Quality:** Top Frontier AI Lab - Enterprise Production-Ready
**Author:** L9 DI/DIP Upgrade Team

---

## Overview

This catalog documents all protocol abstractions available in L9 for dependency injection. Protocols define **what** components do, not **how** they do it, enabling flexible, testable, and maintainable code.

---

## Kernel Protocols

**Module:** `core.abstractions.kernel_protocols`

### KernelValidator

Validates kernel YAML against schema.

```python
from core.abstractions import KernelValidator

class KernelValidator(Protocol):
    def validate(
        self, data: Dict[str, Any], file_path: str
    ) -> KernelValidationResult:
        """Validate kernel data against schema."""
        ...

    def validate_manifest(self, manifest: KernelManifest) -> bool:
        """Validate a kernel manifest object."""
        ...
```

**Implementations:**
- `PydanticKernelValidator` - Pydantic-based validation
- `StrictKernelValidator` - Enhanced validation with custom rules
- `MockKernelValidator` - Test double

**Usage:**
```python
container.bind_singleton(KernelValidator, PydanticKernelValidator)
validator = container.resolve(KernelValidator)
result = validator.validate(yaml_data, "kernel.yaml")
```

---

### KernelDiscovery

Discovers kernel files from configuration.

```python
from core.abstractions import KernelDiscovery

class KernelDiscovery(Protocol):
    def discover_kernels(self, base_path: Path) -> List[Path]:
        """Discover kernel files from base path."""
        ...

    def get_kernel_order(self) -> List[str]:
        """Get the configured kernel loading order."""
        ...
```

**Implementations:**
- `OrderedKernelDiscovery` - Fixed order from configuration
- `GlobKernelDiscovery` - Pattern-based discovery
- `DynamicKernelDiscovery` - Runtime-determined order

**Usage:**
```python
container.bind_singleton(KernelDiscovery, OrderedKernelDiscovery)
discovery = container.resolve(KernelDiscovery)
kernels = discovery.discover_kernels(Path("private/kernels"))
```

---

### IntegrityVerifier

Verifies kernel file integrity.

```python
from core.abstractions import IntegrityVerifier

class IntegrityVerifier(Protocol):
    def compute_hash(self, path: Path) -> str:
        """Compute hash of kernel file."""
        ...

    def verify_integrity(self, path: Path, stored_hash: str) -> bool:
        """Verify kernel file integrity against stored hash."""
        ...

    def get_algorithm(self) -> str:
        """Get the hash algorithm name."""
        ...
```

**Implementations:**
- `SHA256IntegrityVerifier` - SHA-256 based verification
- `MD5IntegrityVerifier` - MD5 based verification (legacy)
- `NoOpIntegrityVerifier` - Bypass verification (testing only)

**Usage:**
```python
container.bind_singleton(IntegrityVerifier, SHA256IntegrityVerifier)
verifier = container.resolve(IntegrityVerifier)
hash_value = verifier.compute_hash(kernel_path)
is_valid = verifier.verify_integrity(kernel_path, stored_hash)
```

---

### KernelActivator

Handles kernel activation operations.

```python
from core.abstractions import KernelActivator

class KernelActivator(Protocol):
    def activate(
        self,
        manifest: KernelManifest,
        agent: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> KernelActivationResult:
        """Activate a kernel with context injection."""
        ...

    def deactivate(self, agent: Any) -> bool:
        """Deactivate a kernel."""
        ...
```

**Implementations:**
- `StandardKernelActivator` - Default activation logic
- `TracedKernelActivator` - Activation with observability
- `MockKernelActivator` - Test double

---

### KernelStateManager

Manages kernel lifecycle state.

```python
from core.abstractions import KernelStateManager

class KernelStateManager(Protocol):
    def get_state(self, kernel_id: str) -> Optional[KernelState]:
        """Get current state of a kernel."""
        ...

    def set_state(self, kernel_id: str, state: KernelState) -> None:
        """Set state of a kernel."""
        ...

    def transition_state(
        self, kernel_id: str, from_state: KernelState, to_state: KernelState
    ) -> bool:
        """Transition kernel state with validation."""
        ...
```

**Implementations:**
- `InMemoryStateManager` - State stored in memory
- `PersistentStateManager` - State persisted to storage
- `DistributedStateManager` - State shared across instances

---

## Memory Protocols

**Module:** `core.abstractions.memory_protocols`

### CacheClient

Key-value cache operations.

```python
from core.abstractions import CacheClient

class CacheClient(Protocol):
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        ...

    async def set(
        self, key: str, value: str, ttl: Optional[int] = None
    ) -> bool:
        """Set key-value pair with optional TTL."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...
```

**Implementations:**
- `RedisClient` - Production Redis client
- `MemoryCacheClient` - In-memory cache for testing
- `DistributedCacheClient` - Multi-node cache cluster

**Usage:**
```python
container.bind_singleton(CacheClient, lambda: RedisClient())
cache = container.resolve(CacheClient)
await cache.set("key", "value", ttl=3600)
value = await cache.get("key")
```

---

### GraphClient

Graph database operations.

```python
from core.abstractions import GraphClient

class GraphClient(Protocol):
    async def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute Cypher query."""
        ...

    async def create_node(
        self, labels: List[str], properties: Dict[str, Any]
    ) -> str:
        """Create a node with labels and properties."""
        ...

    async def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create relationship between nodes."""
        ...
```

**Implementations:**
- `Neo4jClient` - Production Neo4j client
- `MemoryGraphClient` - In-memory graph for testing
- `RemoteGraphClient` - Remote graph database

---

### VectorStore

Vector similarity search operations.

```python
from core.abstractions import VectorStore

class VectorStore(Protocol):
    async def upsert_embedding(
        self,
        id: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Insert or update embedding with metadata."""
        ...

    async def search_similar(
        self, query_embedding: List[float], top_k: int = 10, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings."""
        ...
```

**Implementations:**
- `PgVectorStore` - PostgreSQL + pgvector
- `ChromaVectorStore` - Chroma vector database
- `MockVectorStore` - In-memory vectors for testing

---

### MemoryRepository

High-level memory CRUD operations.

```python
from core.abstractions import MemoryRepository

class MemoryRepository(Protocol):
    async def store_memory(
        self,
        content: str,
        memory_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a memory."""
        ...

    async def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve memory by ID."""
        ...

    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search memories by query."""
        ...
```

**Implementations:**
- `SubstrateMemoryRepository` - Multi-backend repository
- `InMemoryRepository` - Testing repository
- `ReadOnlyRepository` - Read-only memory access

---

### IngestionPipeline

Memory ingestion and processing.

```python
from core.abstractions import IngestionPipeline

class IngestionPipeline(Protocol):
    async def ingest(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Ingest content into memory system."""
        ...

    async def batch_ingest(
        self, items: List[Dict[str, Any]]
    ) -> List[str]:
        """Ingest multiple items in batch."""
        ...
```

**Implementations:**
- `StandardIngestionPipeline` - Default pipeline
- `EnrichedIngestionPipeline` - With additional enrichment
- `StreamingIngestionPipeline` - Real-time streaming ingestion

---

### RetrievalStrategy

Memory retrieval and ranking.

```python
from core.abstractions import RetrievalStrategy

class RetrievalStrategy(Protocol):
    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories for query."""
        ...

    def rank_results(
        self, results: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Re-rank retrieval results."""
        ...
```

**Implementations:**
- `SemanticRetrievalStrategy` - Embedding-based retrieval
- `HybridRetrievalStrategy` - Combined semantic + keyword
- `CachedRetrievalStrategy` - With caching layer

---

## Observability Protocols

**Module:** `core.abstractions.observability_protocols`

### SpanEmitter

Distributed tracing span emission.

```python
from core.abstractions import SpanEmitter, SpanKind, SpanStatus

class SpanEmitter(Protocol):
    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        **attributes: Any,
    ) -> Any:
        """Start a new span."""
        ...

    def finish_span(
        self,
        span: Any,
        status: SpanStatus = SpanStatus.OK,
        error: Optional[str] = None,
    ) -> None:
        """Finish a span."""
        ...
```

**Implementations:**
- `JaegerSpanEmitter` - Jaeger tracing backend
- `OpenTelemetrySpanEmitter` - OpenTelemetry backend
- `NoOpSpanEmitter` - No-op for testing/disabled tracing

---

### MetricsCollector

Metrics collection and aggregation.

```python
from core.abstractions import MetricsCollector

class MetricsCollector(Protocol):
    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        ...

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric."""
        ...

    def record_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a histogram value."""
        ...
```

**Implementations:**
- `PrometheusMetricsCollector` - Prometheus metrics
- `StatsdMetricsCollector` - StatsD metrics
- `InMemoryMetricsCollector` - Testing metrics

---

## Agent Protocols

**Module:** `core.abstractions.agent_protocols`

### ActivatableAgent

Agent with kernel activation capability.

```python
from core.abstractions import ActivatableAgent

class ActivatableAgent(Protocol):
    def kernel_activate(
        self, manifest: Any, context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Activate agent with kernel manifest."""
        ...

    def kernel_deactivate(self) -> bool:
        """Deactivate kernel from agent."""
        ...

    @property
    def agent_id(self) -> str:
        """Get unique agent identifier."""
        ...
```

**Implementations:**
- `BaseAgent` - Standard agent base class
- `CustomAgent` - User-defined agent implementations
- `MockAgent` - Test double

---

### ToolExecutor

Tool execution interface.

```python
from core.abstractions import ToolExecutor

class ToolExecutor(Protocol):
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a tool with parameters."""
        ...

    def list_available_tools(self) -> List[str]:
        """List available tools."""
        ...

    def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get tool parameter schema."""
        ...
```

**Implementations:**
- `StandardToolExecutor` - Default tool execution
- `SandboxedToolExecutor` - Isolated tool execution
- `TracedToolExecutor` - Tool execution with observability

---

### StateManager

Agent state management.

```python
from core.abstractions import StateManager, AgentState

class StateManager(Protocol):
    async def get_state(self, agent_id: str) -> Optional[AgentState]:
        """Get current state of an agent."""
        ...

    async def set_state(self, agent_id: str, state: AgentState) -> None:
        """Set state of an agent."""
        ...

    async def transition_state(
        self, agent_id: str, from_state: AgentState, to_state: AgentState
    ) -> bool:
        """Transition agent state with validation."""
        ...
```

**Implementations:**
- `InMemoryStateManager` - State stored in memory
- `PersistentStateManager` - State persisted to storage
- `DistributedStateManager` - State shared across instances

---

### AgentOrchestrator

Agent orchestration and coordination.

```python
from core.abstractions import AgentOrchestrator

class AgentOrchestrator(Protocol):
    async def register_agent(
        self, agent: ActivatableAgent, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register an agent with orchestrator."""
        ...

    async def route_task(
        self, task: Dict[str, Any], constraints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Route task to appropriate agent."""
        ...

    def list_agents(self) -> List[str]:
        """List all registered agents."""
        ...
```

**Implementations:**
- `StandardOrchestrator` - Default orchestration
- `PriorityOrchestrator` - Priority-based task routing
- `DistributedOrchestrator` - Multi-node orchestration

---

### AgentRegistry

Agent discovery and registration.

```python
from core.abstractions import AgentRegistry

class AgentRegistry(Protocol):
    def register(
        self,
        agent_id: str,
        agent_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register an agent."""
        ...

    def find_agents(
        self, agent_type: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Find agents by type or filters."""
        ...
```

**Implementations:**
- `InMemoryAgentRegistry` - Registry in memory
- `PersistentAgentRegistry` - Registry with persistence
- `DistributedAgentRegistry` - Multi-node registry

---

## Usage Patterns

### Complete Application Setup

```python
from core.di.container import get_di_container
from core.abstractions import *

def configure_protocols():
    """Configure all protocol bindings."""
    container = get_di_container()

    # Kernel protocols
    container.bind_singleton(KernelValidator, PydanticKernelValidator)
    container.bind_singleton(KernelDiscovery, OrderedKernelDiscovery)
    container.bind_singleton(IntegrityVerifier, SHA256IntegrityVerifier)

    # Memory protocols
    container.bind_singleton(CacheClient, lambda: RedisClient())
    container.bind_singleton(GraphClient, lambda: Neo4jClient())
    container.bind_singleton(VectorStore, lambda: PgVectorStore())
    container.bind_singleton(MemoryRepository, SubstrateMemoryRepository)

    # Observability protocols
    container.bind_singleton(SpanEmitter, JaegerSpanEmitter)
    container.bind_singleton(MetricsCollector, PrometheusMetricsCollector)

    # Agent protocols
    container.bind_singleton(AgentRegistry, InMemoryAgentRegistry)
    container.bind_singleton(AgentOrchestrator, StandardOrchestrator)

    return container
```

---

## Further Reading

- [DI Container Guide](./di-container-guide.md) - Comprehensive container documentation
- [Migration Checklist](./migration-checklist.md) - Step-by-step migration guide
- [Troubleshooting DI](./troubleshooting-di.md) - Common issues and solutions

---

**Quality Assurance:** This catalog is maintained to Top Frontier AI Lab standards. All protocols are production-tested and type-safe.

**Version History:**
- 1.0.0 (2026-01-20): Initial release with Phase 1 abstractions
