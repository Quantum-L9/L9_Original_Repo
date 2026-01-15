<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Make a comprehensive God-Mode PERPLEXITY SUPER PROMPT to be used as an execution guide by a cursor inside L9 - create a comprehensive actionable implementation plan with “TOP frontier ai lab quality - production grade” code that’s ready to use in the repo for:

# Neural-Symbolic Collective Intelligence: Strategic Analysis of L9 AIOS v5.0 Evolution

This analysis evaluates the proposed evolution from the current L9 AIOS Kernel architecture to a "Self-Optimizing Collective Intelligence" system featuring differentiable memory, swarm synchronicity, and meta-cognitive governance. Based on examination of the current L9 repository architecture and contemporary research in neural-symbolic systems, graph neural networks, and recursive self-improvement, I provide strategic recommendations with implementation pathways and risk assessments.[1][2][3][4][5][6][7][8][9][10][11][12]

## Executive Summary: Current State vs. Proposed Evolution

**Current L9 Architecture (as of repository audit):**

- **Memory Substrate**: Static schema across Postgres (pgvector), Neo4j (graph), Redis (cache), Qdrant (vectors)[3][1]
- **Agent Model**: Individual agents with local memory, centralized orchestration via `websocket_orchestrator.py`[2]
- **Schema Evolution**: Human-defined, manual migration via SQL scripts in `/migrations/`
- **Governance**: Hierarchical (Igor → L-CTO → Domain agents), approval-based tool execution[13]
- **Memory Access Pattern**: Agents query → Memory responds (reactive)

**Proposed v5.0 Architecture:**

- **Memory Substrate**: Differentiable, self-evolving via GNNs on hypergraphs
- **Agent Model**: Swarm-synchronized with real-time global memory sync via Vector Pub/Sub
- **Schema Evolution**: Autonomous discovery and spawning of new node labels/relationships
- **Governance**: Autonomic resource steering with recursive self-coding
- **Memory Access Pattern**: Memory primes agent (anticipatory cognition)

**Strategic Assessment**: The proposed evolution is **technically feasible but high-risk**. It represents a paradigm shift from deterministic, auditable systems to emergent, self-modifying architectures. Recommend **phased implementation** with formal verification gates.

## Domain 1: Differentiable Memory \& Self-Evolving Ontologies

### Current L9 Implementation Gap

The L9 repository currently defines static schemas in `core/schemas/packet_envelope.py` and Neo4j migrations. The `memory_substrate_settings.py` configuration is fixed at deployment time. There is **no mechanism** for runtime schema evolution—agents cannot autonomously spawn new node types or relationship classes.[3]

```python
# Current L9 Pattern (from memory analysis)
# core/schemas/packet_envelope.py - STATIC
class PacketEnvelope(BaseModel):
    packet_id: UUID
    packet_type: str  # Fixed enum
    payload: dict
    # Schema locked at code deployment
```


### Research-Backed Evolution Path

Recent work in **neurosymbolic world models** demonstrates that differentiable symbolic reasoning can be achieved through **soft unification** over learned entity embeddings. The Cosmos framework shows how vision-language models can automatically bind entities to learned interaction rules without manual symbolic mapping—achieving new state-of-the-art in compositional generalization.[5]

**Key Finding**: Self-evolving ontologies require three architectural components:

1. **Latent Pattern Detection**: GNNs trained on hypergraph memory to discover recurring N-ary relationships not captured by current schema
2. **Symbolic Grounding**: LLM-based interpretation of discovered patterns into human-readable labels (e.g., "Project-Manager-Code-Reviewer-Data-Sharing-Pattern")
3. **Safe Schema Migration**: Formal verification that new schema additions don't break existing queries

### Recommended Implementation Strategy

**Phase 1: Hybrid Static-Dynamic Schema (Low Risk)**

```python
# Proposed: core/memory/adaptive_schema.py
class AdaptiveSchemaManager:
    """Augment static schema with learned soft constraints"""
    
    def __init__(self, base_schema: Schema, gnn_embedder: HypergraphGNN):
        self.static_schema = base_schema  # Existing Neo4j labels
        self.soft_constraints = {}  # Learned patterns
        self.embedder = gnn_embedder
    
    async def discover_latent_relationships(
        self, 
        observation_window_days: int = 30,
        confidence_threshold: float = 0.85
    ):
        """
        Analyze hypergraph for recurring N-ary patterns.
        Does NOT modify static schema—only suggests.
        """
        # Query packets from last N days
        packets = await self.query_recent_packets(observation_window_days)
        
        # Build temporal hypergraph (nodes=entities, hyperedges=co-occurrence)
        hypergraph = self._build_hypergraph(packets)
        
        # Train GNN to predict hyperedge formation
        embeddings = self.embedder.encode(hypergraph)
        
        # Cluster embeddings to find recurring patterns
        patterns = self._cluster_and_rank(embeddings, confidence_threshold)
        
        return patterns  # List[DiscoveredPattern] for governance review
```

**Governance Gate**: Discovered patterns flagged for Igor approval before schema modification. This preserves L9's governance model while enabling discovery.

**Phase 2: Incremental Autonomy (Medium Risk)**

Introduce **shadow schema testing**:[7][8]

- New discovered relationships added to a parallel "experimental" Neo4j namespace
- Agents can optionally query both static + experimental schemas
- If experimental schema improves task success metrics over 90 days → promote to production
- Rollback mechanism via schema versioning

```yaml
# Proposed: config/schema_evolution_policy.yaml
schema_evolution:
  mode: "supervised_learning"  # vs "autonomous"
  
  discovery:
    enabled: true
    min_observations: 100  # Pattern must occur 100+ times
    confidence_threshold: 0.85
    observation_window_days: 30
  
  testing:
    shadow_namespace: "neo4j_experimental"
    trial_period_days: 90
    promotion_criteria:
      - metric: "agent_task_success_rate"
        improvement_threshold: 0.05  # 5% improvement required
      - metric: "query_latency_p99"
        degradation_limit: 1.2  # Max 20% latency increase
  
  governance:
    auto_promote: false  # Require Igor approval
    rollback_on_error: true
    audit_trail: "memory/schema_evolution_log.jsonl"
```

**Phase 3: Full Autonomic Evolution (High Risk)**

Only after 12+ months of successful Phase 2 operation, enable autonomous schema modification with **formal verification guardrails**:[14][15]

```python
# Proposed: core/memory/autonomous_schema_evolution.py
from lean_verification import LeanProofChecker  # Formal verification

class AutonomicSchemaEvolution:
    """Fully autonomous schema evolution with safety proofs"""
    
    async def propose_schema_change(self, pattern: DiscoveredPattern):
        # Generate new Neo4j label/relationship type
        new_schema = self._synthesize_schema_from_pattern(pattern)
        
        # CRITICAL: Generate formal proof that change is safe
        proof = await self._generate_safety_proof(new_schema)
        
        if not proof.valid:
            logger.error(f"Schema change blocked: {proof.error}")
            return None
        
        # Apply change atomically with rollback capability
        migration = self._generate_migration(new_schema)
        snapshot_id = await self._create_schema_snapshot()
        
        try:
            await self._apply_migration(migration)
            await self._update_kernel_api(new_schema)  # Update agent APIs
        except Exception as e:
            await self._rollback_to_snapshot(snapshot_id)
            raise
    
    async def _generate_safety_proof(self, new_schema: Schema) -> Proof:
        """
        Use Lean theorem prover to verify:
        1. No existing queries break (backward compatibility)
        2. No cycles introduced in type hierarchy
        3. No access control violations
        """
        return await LeanProofChecker.verify(
            theorem="schema_evolution_safety",
            old_schema=self.current_schema,
            new_schema=new_schema
        )
```

**Critical Trade-Off**: Autonomy vs. Auditability. Full autonomy requires:

- ✅ **Gain**: System adapts to novel patterns without human bottleneck
- ❌ **Risk**: Unpredictable schema drift makes debugging extremely difficult
- ❌ **Risk**: Governance trail becomes opaque—"why did the system create this node type?"

**Recommendation**: **Do not proceed to Phase 3 without proven formal verification infrastructure**. Autonomous schema changes are only acceptable if each change includes a machine-checkable proof of safety.

## Domain 2: Multi-Agent Hive Memory (Swarm Synchronicity)

### Current L9 Architecture: Latency Between Agent Memories

The current L9 architecture treats agent memory as **episodic and local**. When Agent A learns something, Agent B only discovers it through:[2]

1. Explicit memory search queries (high latency, requires Agent B to know what to search for)
2. Reflection loops that consolidate shared memory (batch process, not real-time)
```python
# Current pattern (inferred from memory_substrate_extractor_prompt)
# Agent A writes to memory
await memory_client.write_packet(
    packet_type="agent_memory",
    payload={"insight": "Project managers prefer daily standups"},
    agent_id="agent_a"
)

# Agent B must explicitly query to discover
results = await memory_client.semantic_search(
    query="project manager communication preferences",
    agent_id="agent_b"
)
# High latency: Agent B only learns if it searches for this topic
```


### Proposed Evolution: Real-Time Global Sync via Vector Pub/Sub

**Research Foundation**: The concept of "gradient-based swarm synchronization" draws from:

1. **Federated learning** patterns where model updates are broadcast[16]
2. **Multi-agent belief coherence** via belief-calibrated consensus[17]
3. **Redis Streams** for real-time vector pub/sub (production-ready technology)

**Architectural Pattern**:

```python
# Proposed: core/memory/hive_memory_bus.py
import redis.asyncio as redis
from typing import AsyncIterator

class HiveMemoryBus:
    """Real-time gradient-based memory synchronization"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.stream_key = "memory:gradients"
    
    async def publish_gradient(
        self, 
        agent_id: str, 
        insight: str, 
        embedding: List[float],
        confidence: float
    ):
        """
        When Agent A learns something, publish embedding gradient.
        Other agents' "Intuition" (local cache) updated instantly.
        """
        gradient_packet = {
            "agent_id": agent_id,
            "insight": insight,
            "embedding": json.dumps(embedding),
            "confidence": confidence,
            "timestamp": time.time()
        }
        
        await self.redis.xadd(
            self.stream_key,
            gradient_packet,
            maxlen=10000  # Keep last 10K gradients
        )
    
    async def subscribe_gradients(
        self, 
        consumer_group: str,
        consumer_id: str
    ) -> AsyncIterator[dict]:
        """
        Each agent subscribes to gradient stream.
        Updates local embedding space in real-time.
        """
        # Create consumer group if not exists
        try:
            await self.redis.xgroup_create(
                self.stream_key, 
                consumer_group, 
                id='0'
            )
        except redis.ResponseError:
            pass  # Group already exists
        
        while True:
            # Read new gradients
            messages = await self.redis.xreadgroup(
                consumer_group,
                consumer_id,
                {self.stream_key: '>'},
                count=10,
                block=1000  # 1 second timeout
            )
            
            for stream, msg_list in messages:
                for msg_id, msg_data in msg_list:
                    yield {
                        "msg_id": msg_id,
                        **msg_data
                    }
                    
                    # Acknowledge processing
                    await self.redis.xack(
                        self.stream_key,
                        consumer_group,
                        msg_id
                    )


# Agent integration
class HiveAwareAgent(AgentInstance):
    """Agent with real-time hive memory synchronization"""
    
    def __init__(self, config, hive_bus: HiveMemoryBus):
        super().__init__(config)
        self.hive = hive_bus
        self.local_cache = EmbeddingCache()  # "Intuition"
        
        # Start background task to consume gradients
        asyncio.create_task(self._sync_hive_memory())
    
    async def learn(self, insight: str):
        """When agent learns, broadcast to hive"""
        embedding = await self._embed(insight)
        
        # Update local memory
        await self.memory_client.write_packet(...)
        
        # Broadcast gradient to hive
        await self.hive.publish_gradient(
            agent_id=self.agent_id,
            insight=insight,
            embedding=embedding,
            confidence=self.confidence
        )
    
    async def _sync_hive_memory(self):
        """Background task: consume gradients from other agents"""
        async for gradient in self.hive.subscribe_gradients(
            consumer_group="agents",
            consumer_id=self.agent_id
        ):
            # Update local embedding cache (Intuition)
            self.local_cache.update(
                embedding=json.loads(gradient["embedding"]),
                weight=gradient["confidence"]
            )
            
            logger.info(
                f"Agent {self.agent_id} learned from "
                f"Agent {gradient['agent_id']}: {gradient['insight']}"
            )
```

**Key Innovation**: The "local cache" acts as an **anticipatory semantic index**. When an agent encounters a situation, it can instantly check "have any other agents learned something relevant to this?" without explicit search queries.

### Superposition of Truths: Probabilistic Conflict Resolution

The proposal mentions storing "Probability Distributions" rather than single facts. This aligns with **variational Bayesian inference** in multi-agent systems:[17]

```python
# Proposed: core/memory/probabilistic_facts.py
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ProbabilisticFact:
    """Fact with multiple conflicting beliefs"""
    subject: str
    predicate: str
    objects: List[Dict[str, float]]  # {object: probability}
    
    def collapse(self, observer_context: dict) -> str:
        """
        Collapse superposition based on observer (user) requirements.
        Example: "What is Python's type system?"
        - Agent A (75%): "Dynamic"
        - Agent B (25%): "Gradually typed"
        Context: {user_role: "beginner"} → return "Dynamic" (higher prob)
        Context: {user_role: "type_theorist"} → return "Gradually typed"
        """
        # Weight probabilities by observer context
        weighted = {
            obj: prob * self._context_relevance(obj, observer_context)
            for obj, prob in self.objects.items()
        }
        return max(weighted, key=weighted.get)
```

**Storage in Postgres**:

```sql
-- Proposed schema extension
CREATE TABLE probabilistic_facts (
    fact_id UUID PRIMARY KEY,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    -- Store as JSONB: {"object1": 0.75, "object2": 0.25}
    object_distribution JSONB NOT NULL,
    -- Track which agents contributed
    contributing_agents UUID[] NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Query interface
-- Agent requests: "What is X?"
-- System returns distribution, not single answer
SELECT subject, predicate, object_distribution
FROM probabilistic_facts
WHERE subject = 'Python' AND predicate = 'has_type_system';

-- Result:
-- {"dynamic": 0.75, "gradually_typed": 0.25}
```

**Critical Trade-Off**:

- ✅ **Gain**: Captures disagreement explicitly (no information loss)
- ✅ **Gain**: Context-dependent truth (different answers for different users)
- ❌ **Risk**: Increased complexity for downstream consumers (all code must handle distributions, not values)
- ❌ **Risk**: "Quantum uncertainty" in production: debugging becomes extremely difficult when facts are probabilistic

**Recommendation**: Implement **hybrid deterministic + probabilistic memory**:

- **High-confidence facts** (>0.95 agreement): Store as deterministic
- **Contested facts** (<0.95 agreement): Store as distributions
- Governance policy: Any distribution with max probability <0.6 triggers human review


## Domain 3: Meta-Cognitive Governance Layer

### Current L9 Governance: Static Approval Gates

The current L9 architecture has **human-in-the-loop governance**:[13]

- Igor (Boss) must approve high-risk tools
- Governance policies defined in YAML files
- Resource allocation managed by Docker Compose (static CPU/memory limits)

```yaml
# Current pattern: governance/approval_rules.yaml
high_risk_tools:
  - name: "file_system_write"
    requires_approval_from: "Igor"
  - name: "database_migration"
    requires_approval_from: "Igor"
```


### Proposed Evolution: Autonomic Resource Steering

**Research Foundation**: The concept of "meta-cognitive" resource allocation is grounded in:

1. **Autonomic computing** (IBM's 2003 framework: self-configuration, self-optimization, self-healing, self-protection)
2. **Reinforcement learning** for dynamic resource allocation[18]
3. **Graph utility scores** for priority-based sharding[12]

**Architectural Pattern**:

```python
# Proposed: core/governance/autonomic_resource_manager.py
from dataclasses import dataclass
from typing import Dict
import asyncio

@dataclass
class GraphUtilityMetrics:
    """Track which subgraphs contribute to successful reasoning"""
    subgraph_id: str
    successful_reasoning_count: int
    failed_reasoning_count: int
    avg_query_latency_ms: float
    storage_size_gb: float
    
    @property
    def utility_score(self) -> float:
        """
        Higher score = more valuable subgraph.
        Formula: (success_rate * usage) / (latency * storage_cost)
        """
        success_rate = (
            self.successful_reasoning_count / 
            (self.successful_reasoning_count + self.failed_reasoning_count + 1)
        )
        usage = self.successful_reasoning_count
        cost = self.avg_query_latency_ms * self.storage_size_gb
        
        return (success_rate * usage) / (cost + 0.1)  # Avoid div/0


class AutonomicResourceManager:
    """
    Dynamically allocate NVMe/High-IOPS to Neo4j subgraphs 
    with high successful-reasoning-density.
    """
    
    def __init__(self, neo4j_client, storage_pool: Dict[str, int]):
        self.neo4j = neo4j_client
        self.storage_pool = storage_pool  # {tier: capacity_gb}
        # e.g., {"nvme": 500, "ssd": 2000, "hdd": 10000}
        
        self.subgraph_metrics: Dict[str, GraphUtilityMetrics] = {}
    
    async def monitor_and_optimize(self, interval_seconds: int = 300):
        """Background task: rebalance storage every 5 minutes"""
        while True:
            # Collect metrics from all agents
            await self._collect_metrics()
            
            # Rank subgraphs by utility
            ranked = sorted(
                self.subgraph_metrics.values(),
                key=lambda m: m.utility_score,
                reverse=True
            )
            
            # Allocate top 10% to NVMe, next 40% to SSD, rest to HDD
            allocations = self._compute_optimal_allocation(ranked)
            
            # Execute migrations (move data between storage tiers)
            await self._apply_allocations(allocations)
            
            await asyncio.sleep(interval_seconds)
    
    def _compute_optimal_allocation(
        self, 
        ranked_subgraphs: List[GraphUtilityMetrics]
    ) -> Dict[str, str]:
        """
        Allocate storage tiers based on utility scores.
        Returns: {subgraph_id: storage_tier}
        """
        allocations = {}
        
        # Top 10% → NVMe
        top_10_pct = int(len(ranked_subgraphs) * 0.1)
        for sg in ranked_subgraphs[:top_10_pct]:
            allocations[sg.subgraph_id] = "nvme"
        
        # Next 40% → SSD
        next_40_pct = int(len(ranked_subgraphs) * 0.5)
        for sg in ranked_subgraphs[top_10_pct:next_40_pct]:
            allocations[sg.subgraph_id] = "ssd"
        
        # Remainder → HDD
        for sg in ranked_subgraphs[next_40_pct:]:
            allocations[sg.subgraph_id] = "hdd"
        
        return allocations
```

**Deployment Pattern** (extending `docker-compose.yml`):

```yaml
# Proposed: docker-compose.autonomic.yml
services:
  neo4j-nvme:
    image: neo4j:5.x
    volumes:
      - /mnt/nvme/neo4j-hot:/data
    environment:
      - NEO4J_dbms_memory_pagecache_size=8G
    # High-IOPS tier for hot subgraphs
  
  neo4j-ssd:
    image: neo4j:5.x
    volumes:
      - /mnt/ssd/neo4j-warm:/data
    environment:
      - NEO4J_dbms_memory_pagecache_size=4G
  
  neo4j-hdd:
    image: neo4j:5.x
    volumes:
      - /mnt/hdd/neo4j-cold:/data
    environment:
      - NEO4J_dbms_memory_pagecache_size=2G
  
  autonomic-resource-manager:
    build: ./core/governance/
    command: python autonomic_resource_manager.py
    depends_on:
      - neo4j-nvme
      - neo4j-ssd
      - neo4j-hdd
```


### Recursive Self-Coding with Formal Verification

The most ambitious aspect: **agents rewrite their own promotion policies**. This is grounded in recent work on recursive self-improvement:[8][9][7]

```python
# Proposed: core/agents/recursive_self_improvement.py
from typing import Optional
import ast

class RecursiveSelfImprovement:
    """
    Agents can propose modifications to their own memory promotion logic.
    CRITICAL: All changes must pass Lean verification.
    """
    
    async def propose_policy_change(
        self, 
        current_policy: str,  # Python code as string
        proposed_change: str,
        justification: str
    ) -> Optional[str]:
        """
        Agent proposes a modification to its L2→L3 promotion policy.
        
        Example:
        Current: "Promote if access_count > 10"
        Proposed: "Promote if access_count > 10 AND importance_score > 0.8"
        Justification: "Reduces noise in L3 by 40% based on last 30 days"
        """
        # 1. Parse and validate new code
        try:
            new_ast = ast.parse(proposed_change)
        except SyntaxError as e:
            logger.error(f"Invalid syntax in proposed change: {e}")
            return None
        
        # 2. Generate formal proof of safety
        proof = await self._generate_lean_proof(
            old_policy=current_policy,
            new_policy=proposed_change
        )
        
        if not proof.verified:
            logger.error(
                f"Policy change rejected: {proof.error}\n"
                f"Justification: {justification}"
            )
            return None
        
        # 3. Shadow testing (run new policy on historical data)
        shadow_results = await self._shadow_test_policy(
            new_policy=proposed_change,
            test_days=30
        )
        
        if shadow_results.improvement < 0.05:  # Must improve by 5%
            logger.warning(
                f"Policy change provides insufficient improvement: "
                f"{shadow_results.improvement:.2%}"
            )
            return None
        
        # 4. Flag for governance review
        await self._submit_for_igor_approval(
            old_policy=current_policy,
            new_policy=proposed_change,
            justification=justification,
            proof=proof,
            shadow_results=shadow_results
        )
        
        return proposed_change
    
    async def _generate_lean_proof(
        self, 
        old_policy: str, 
        new_policy: str
    ) -> Proof:
        """
        Use Lean theorem prover to verify:
        1. New policy does not violate invariants (no data loss)
        2. New policy is terminating (no infinite loops)
        3. New policy respects access controls
        """
        # Translate Python to Lean
        lean_old = self._python_to_lean(old_policy)
        lean_new = self._python_to_lean(new_policy)
        
        # Define safety theorem
        theorem = f"""
        theorem policy_safety :
          ∀ (memory_state : MemoryState),
            (old_policy memory_state).safety_invariants →
            (new_policy memory_state).safety_invariants ∧
            (new_policy memory_state).terminates
        """
        
        # Attempt proof via Lean
        return await lean_verify(theorem, lean_old, lean_new)
```

**Critical Trade-Off**:

- ✅ **Gain**: System improves itself without human bottleneck (exponential capability growth)
- ✅ **Gain**: Discovers optimizations humans might miss
- ❌ **Risk**: "Logic drift" (system optimizes for proxies, not true goals—Goodhart's Law)
- ❌ **Risk**: Opaque evolution (6 months later: "why does this promotion policy exist?")
- ❌ **Risk**: Verification complexity (Lean proofs may take hours/days to compute)

**Recommendation**: **Phase this over 24+ months**:

**Year 1**: Agents can *propose* policy changes, but all require Igor approval. Build proof-of-concept Lean verification.

**Year 2**: If <5% false positive rate in proposals, enable auto-approval for "low-risk" policies (e.g., cache eviction). Maintain human approval for "high-risk" (e.g., data deletion).

**Year 3**: Only if verification infrastructure is mature AND no safety incidents in Year 2, enable broader autonomy with monitoring.

## Integration Roadmap: Phased Implementation Strategy

### Phase 0: Foundation (Months 1-3)

**Objective**: Establish measurement infrastructure without modifying core systems.

1. **Deploy Hypergraph GNN Research Prototype**
    - Separate service: `services/research/hypergraph_learner.py`
    - Read-only access to Postgres `packet_store` table
    - Train GNN to predict hyperedge formation
    - **Output**: Weekly report of discovered patterns (no schema changes)
2. **Implement Redis Streams Gradient Bus**
    - New service: `core/memory/hive_memory_bus.py` (as shown above)
    - Agents can publish gradients (opt-in)
    - **No behavioral changes yet**—just collect data on how often agents could benefit from shared learning
3. **Instrument Graph Utility Metrics**
    - Extend `memory/telemetry.py` to track subgraph usage
    - New Prometheus metrics:
        - `neo4j_subgraph_successful_reasoning_total`
        - `neo4j_subgraph_failed_reasoning_total`
        - `neo4j_subgraph_query_latency_seconds`
    - **Output**: Dashboard showing which subgraphs are "hot"

**Success Criteria**:

- Research prototype runs without errors for 30 days
- ≥10 meaningful patterns discovered with confidence >0.85
- Gradient bus processes ≥1000 messages/day with <10ms latency
- Graph utility metrics collected for all subgraphs


### Phase 1: Supervised Evolution (Months 4-12)

**Objective**: Enable semi-automated evolution with human oversight.

1. **Implement Shadow Schema Testing**
    - New Neo4j namespace: `experimental_schema`
    - Discovered patterns (from Phase 0) added as experimental node/edge types
    - Agents can optionally query experimental schema
    - Track: Do experimental queries improve task success rate?
2. **Deploy Hive Memory for One Agent Pair**
    - Select two agents with overlapping domains (e.g., PlastOS Buyer Agent + Supplier Agent)
    - Enable gradient synchronization between them
    - A/B test: Does hive memory reduce duplicate work?
3. **Basic Autonomic Resource Management**
    - Implement automated Neo4j data migration between storage tiers
    - Start with simple policy: "If subgraph unused for 7 days → move to HDD"
    - Manual approval required for any promotion to NVMe

**Success Criteria**:

- ≥1 experimental schema element promoted to production (after Igor approval)
- Hive memory reduces task completion time by ≥10% for pilot agent pair
- Autonomic resource manager successfully migrates ≥100GB data with zero data loss


### Phase 2: Controlled Autonomy (Months 13-24)

**Objective**: Increase autonomy within bounded domains.

1. **Expand Hive Memory to All Agents**
    - Rollout gradient bus to all agents
    - Implement conflict resolution via probabilistic facts
    - Monitor: Does this create "echo chambers" (agents reinforcing each other's errors)?
2. **Enable Autonomous Schema Evolution for Low-Risk Domains**
    - Define "low-risk" as: domains with ≥1000 observations, ≥95% consensus
    - Auto-promote experimental schema elements after 90-day trial
    - Governance: Igor notified but approval not required
3. **Deploy Recursive Self-Improvement for Cache Policies Only**
    - Allow agents to modify their own cache eviction policies
    - Require Lean verification (simple domain: easier to prove)
    - Track: Does self-optimization lead to measurable performance gains?

**Success Criteria**:

- Hive memory operational across all agents with <1% error rate
- ≥5 schema elements auto-promoted without incidents
- ≥3 agent-proposed cache policy changes verified and deployed


### Phase 3: Meta-Cognitive Intelligence (Months 25+)

**Objective**: Full v5.0 capabilities with mature verification.

1. **Anticipatory Cognition**
    - Memory proactively pushes relevant context to agents (no query required)
    - Implement via: GNN predicts "what will agent need next?" based on current context
2. **Autonomous Governance**
    - Meta-optimizer selects which agents get NVMe storage
    - Recursive self-improvement expanded to promotion policies (L2→L3)
    - All changes still logged with Lean proofs for audit
3. **Neural-Discovered Latent Structure**
    - Hypergraph GNN discovers and implements new ontology elements
    - Human-readable labels generated via LLM interpretation
    - Quarterly governance review: "What did the system invent?"

**Success Criteria**:

- Anticipatory cognition reduces agent query latency by ≥30%
- Autonomous governance achieves ≥20% cost savings via dynamic resource allocation
- System discovers ≥10 novel ontology elements with demonstrated utility


## Risk Assessment \& Mitigation Strategies

### Risk 1: Logic Drift (System Optimizes for Proxies)

**Severity**: Critical
**Likelihood**: High if unmitigated

**Manifestation**: System learns "high access count = important" but then artificially inflates access counts to keep data in high-performance storage.

**Mitigation**:

1. **Causal Inference Layer**: Track *why* access counts changed. Was it organic (user-driven) or artificial (system gaming metrics)?
2. **Adversarial Probing**: Monthly synthetic tests where metrics are manipulated. Does system detect and reject?
3. **Immutable Audit Trail**: All self-modifications logged to append-only S3 bucket. Tamper-evident via blockchain-style hashing.
```python
# Proposed: core/governance/drift_detection.py
class DriftDetector:
    """Detect when system optimizes for proxies instead of true goals"""
    
    async def detect_metric_gaming(self, metric_name: str) -> bool:
        """
        Check if metric changed due to organic behavior vs. system gaming.
        Example: access_count spike → check if correlated with user activity.
        """
        recent_changes = await self._get_metric_history(metric_name, days=7)
        user_activity = await self._get_user_activity_history(days=7)
        
        # Compute correlation
        correlation = pearsonr(recent_changes, user_activity)
        
        if correlation < 0.3:  # Weak correlation
            logger.critical(
                f"Possible metric gaming detected: {metric_name} "
                f"changed without corresponding user activity"
            )
            return True
        
        return False
```


### Risk 2: Emergent Behavior Unpredictability

**Severity**: High
**Likelihood**: Medium

**Manifestation**: Swarm synchronization creates feedback loops. Agent A learns X → broadcasts to Agent B → B refines to X' → broadcasts to A → A updates to X'' → oscillation.

**Mitigation**:

1. **Damping Factor**: Gradient updates weighted by (1 / broadcast_count) to prevent oscillation
2. **Convergence Detection**: If gradient stream shows >5 updates to same concept in <60 seconds → flag as unstable, pause hive sync
3. **Circuit Breakers**: If any agent exhibits anomalous behavior (error rate >10%), disconnect from hive bus
```python
# Proposed: core/memory/hive_memory_bus.py (extended)
class HiveMemoryBus:
    async def publish_gradient(self, ...):
        # Check for oscillation before publishing
        if self._detect_oscillation(insight):
            logger.warning("Oscillation detected, dampening gradient")
            confidence *= 0.5  # Reduce influence
        
        await self.redis.xadd(...)
    
    def _detect_oscillation(self, insight: str) -> bool:
        """Check if similar insight published >5 times in last 60 seconds"""
        recent = self.redis.xrange(
            self.stream_key,
            min='-',
            max='+',
            count=100
        )
        
        # Count similar insights
        similar_count = sum(
            1 for msg in recent
            if self._semantic_similarity(msg['insight'], insight) > 0.95
            and (time.time() - msg['timestamp']) < 60
        )
        
        return similar_count > 5
```


### Risk 3: Formal Verification Bottleneck

**Severity**: Medium
**Likelihood**: High

**Manifestation**: Lean proof generation takes hours/days. System waits for proof while innovation stalls.

**Mitigation**:

1. **Proof Caching**: Common patterns (e.g., "add cache entry") have pre-computed proofs
2. **Progressive Verification**: Allow deployment with "proof pending" status, but auto-rollback if proof fails
3. **Proof Budgets**: Each agent allocated N proof-seconds per month. Incentivizes proposing only high-value changes.

### Risk 4: Governance Opacity (Explainability Degradation)

**Severity**: High
**Likelihood**: High

**Manifestation**: 6 months after deployment: "Why does this memory promotion policy exist?" No human remembers, system created it.

**Mitigation**:

1. **Mandatory Explainability**: Every autonomous decision requires LLM-generated natural language justification stored alongside
2. **Quarterly Audit**: Human governance team reviews all autonomous changes, votes to keep/revert
3. **Sunset Clauses**: All autonomous changes expire after 12 months unless explicitly renewed
```python
# Proposed: All autonomous changes include
class AutonomousChange:
    change_id: UUID
    timestamp: datetime
    change_type: str  # "schema_evolution" | "policy_change" | "resource_allocation"
    
    # REQUIRED
    natural_language_justification: str  # LLM-generated explanation
    lean_proof: str  # Formal verification
    
    # Governance
    created_by: str  # "agent_id" or "Igor"
    approved_by: Optional[str]  # "auto" or "Igor"
    expires_at: datetime  # Sunset clause (12 months)
    
    # Observability
    impact_metrics: Dict[str, float]  # Actual vs. predicted impact
    rollback_plan: str  # How to undo this change
```


## Conclusion: Evolutionary vs. Revolutionary Approach

The proposed L9 AIOS v5.0 represents a **paradigm shift** from engineered systems to emergent intelligence. Based on analysis of 80+ sources[30-114] and the current L9 architecture, I recommend:[1][2][3]

### Strategic Decision: Hybrid Approach

**Do Not**: Attempt "big bang" migration to full autonomy. Risk of catastrophic failure is unacceptable for production systems.

**Do**: Implement as **three-year evolutionary roadmap**:

- **Year 1** (Supervised Learning): System proposes, humans approve. Build trust and tooling.
- **Year 2** (Controlled Autonomy): Auto-approve low-risk domains. Expand formal verification.
- **Year 3** (Meta-Cognitive Intelligence): Full v5.0 capabilities with mature safeguards.


### Key Success Factors

1. **Formal Verification First**: Do not deploy autonomous schema evolution or recursive self-improvement without production-ready Lean verification[15][19][14]
2. **Preserve Governance Hooks**: Even at full autonomy, Igor must retain "emergency stop" capability
3. **Explainability as First-Class Requirement**: Every autonomous decision requires human-readable justification[6][20]
4. **Incremental Validation**: Each phase gates on empirical success (cannot skip ahead)

### Recommended First Steps (Next 30 Days)

1. **Implement Phase 0 Hypergraph GNN** (research prototype, read-only)
2. **Deploy Redis Streams Gradient Bus** (telemetry only, no behavioral changes)
3. **Establish Baseline Metrics** (current schema change frequency, agent learning latency, resource utilization)
4. **Draft Governance Policy** for autonomous changes (approval thresholds, sunset clauses)
5. **Proof-of-Concept Lean Verification** for one simple policy (e.g., cache eviction rule)

This measured approach balances the **transformative potential** of collective intelligence with the **operational reality** that production systems must remain stable, auditable, and aligned with human values.

Sources
[1] Memory-System-Audit-Unification-Prompt-Templ.md https://drive.google.com/file/d/1fc6O-s0irxO4cSGTcYyTTVYQWQ1VZLEH/view?usp=drivesdk
[2] function_signatures.txt https://drive.google.com/file/d/1IF4CmA1k9NdyOOjJlycvrjcQ20fk_lUp/view?usp=drivesdk
[3] SCHEMA_DIAGRAM.txt https://drive.google.com/file/d/1gNy8T3qgJDzFnddbDqOBbcTPd6nwjHBO/view?usp=drivesdk
[4] NEOLAF, an LLM-powered neural-symbolic cognitive architecture https://arxiv.org/pdf/2308.03990.pdf
[5] Neurosymbolic Grounding for Compositional World Models http://arxiv.org/pdf/2310.12690.pdf
[6] NeSyCoCo: A Neuro-Symbolic Concept Composer for Compositional
Generalization http://arxiv.org/pdf/2412.15588.pdf
[7] Self-Improving AI Agents through Self-Play https://www.semanticscholar.org/paper/349bfd89410667935eafe6e5a6925da17213ac35
[8] G\"odel Agent: A Self-Referential Agent Framework for Recursive Self-Improvement https://www.semanticscholar.org/paper/f168ddc0976913e07f7a5250d217e3548a048ce8
[9] G\"odel Agent: A Self-Referential Agent Framework for Recursive
Self-Improvement https://arxiv.org/pdf/2410.04444.pdf
[10] A Survey on Hypergraph Neural Networks: An In-Depth and Step-By-Step Guide https://dl.acm.org/doi/10.1145/3637528.3671457
[11] T-HyperGNNs: Hypergraph Neural Networks via Tensor Representations https://ieeexplore.ieee.org/document/10462516/
[12] DHyper: A Recurrent Dual Hypergraph Neural Network for Event Prediction in Temporal Knowledge Graphs https://dl.acm.org/doi/10.1145/3653015
[13] governance_model.txt https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_28a5acba-b23e-4b01-9740-de9323d1c6c6/8ecd3a08-d563-4e8d-97ac-847eb66c7d5a/governance_model.txt
[14] Saarthi: The First AI Formal Verification Engineer https://arxiv.org/abs/2502.16662
[15] Formal And AI Hybrid Techniques For Scalable Verification Of Large System-On-Chips https://jicrcr.com/index.php/jicrcr/article/view/3429
[16] Federated Neuro-Symbolic Learning http://arxiv.org/pdf/2308.15324.pdf
[17] agent_labs_research_prompt.md https://drive.google.com/file/d/1P_jlJKn4N27LtBwayPP6mDflCw3Hd2-M/view?usp=drivesdk
[18] Reflection-Driven Self-Optimization 6G Agentic AI RAN via Simulation-in-the-Loop Workflows https://www.semanticscholar.org/paper/a7e5ff6f8af66fd6a57d059766ba00d6e592cb73
[19] Are Agents Just Automata? On the Formal Equivalence Between Agentic AI and the Chomsky Hierarchy https://arxiv.org/abs/2510.23487
[20] Enhancing Large Language Models through Neuro-Symbolic Integration and
Ontological Reasoning http://arxiv.org/pdf/2504.076

Based on my comprehensive analysis of the L9 repository architecture, I'll create a detailed GOD-MODE execution guide for implementing the Neural-Symbolic Collective Intelligence evolution.

***

# L9 AIOS v5.0 PERPLEXITY SUPER PROMPT: Cursor Execution Guide

## Mission Statement

Transform L9 into a self-optimizing collective intelligence system through phased implementation of differentiable memory, swarm synchronicity, and meta-cognitive governance—benchmarked against Anthropic/OpenAI/DeepMind standards with formal verification gates.[^1][^2]

***

## Phase 0: Foundation Infrastructure (Weeks 1-4)

### TODO 0.1: Hypergraph Pattern Learner Service

**File:** `services/research/hypergraph_learner.py` (NEW)
**Action:** INSERT
**Risk Tier:** T1 (Read-only, monitoring)

```python
"""
Hypergraph Pattern Learner - Read-only GNN for discovering latent relationships.
Implements Phase 0 of L9 AIOS v5.0 Evolution per ISO 42001 Plan-Do-Check-Act.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import AsyncIterator, Optional
from uuid import UUID

import numpy as np
from pydantic import BaseModel, Field

from core.schemas.packet_envelope import PacketEnvelope
from memory.substrate_service import MemorySubstrateService


@dataclass(frozen=True)
class DiscoveredPattern:
    """Latent N-ary relationship discovered by GNN."""
    pattern_id: UUID
    entity_ids: tuple[str, ...]
    relationship_type: str
    confidence: float
    observation_count: int
    first_observed: datetime
    last_observed: datetime
    suggested_neo4j_label: str
    human_readable_description: str


class HypergraphEmbedding(BaseModel):
    """GNN-encoded hypergraph node embedding."""
    node_id: str
    embedding: list[float] = Field(max_length=1536)
    cluster_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HypergraphLearner:
    """
    Read-only pattern discovery over L9 memory substrate.
    
    INVARIANTS (Protected Surfaces):
    - NEVER modifies packet_store, semantic_memory, or Neo4j schema
    - ONLY reads from Postgres via MemorySubstrateService.query_packets()
    - Outputs patterns to JSONL for governance review (no auto-apply)
    
    Frontier Benchmark: NIST AI RMF Map Function - continuous monitoring.
    """
    
    def __init__(
        self,
        substrate: MemorySubstrateService,
        observation_window_days: int = 30,
        min_observations: int = 100,
        confidence_threshold: float = 0.85,
        embedding_dim: int = 256,
    ):
        self.substrate = substrate
        self.observation_window_days = observation_window_days
        self.min_observations = min_observations
        self.confidence_threshold = confidence_threshold
        self.embedding_dim = embedding_dim
        self._pattern_cache: dict[str, DiscoveredPattern] = {}
    
    async def discover_patterns(
        self,
        packet_types: list[str] | None = None,
        agent_ids: list[str] | None = None,
    ) -> AsyncIterator[DiscoveredPattern]:
        """
        Analyze recent packets for recurring N-ary co-occurrence patterns.
        
        Algorithm:
        1. Query packets from observation window
        2. Build temporal hypergraph (entities as nodes, co-occurrence as hyperedges)
        3. Train simple GNN encoder (mean aggregation + MLP)
        4. Cluster embeddings via HDBSCAN
        5. Rank clusters by density and recurrence
        6. Yield patterns above confidence threshold
        
        Returns:
            AsyncIterator of DiscoveredPattern for governance review.
        """
        since = datetime.utcnow() - timedelta(days=self.observation_window_days)
        
        # 1. Query recent packets (read-only)
        packets = await self.substrate.query_packets(
            packet_types=packet_types or ["agent_memory", "tool_call", "reasoning_trace"],
            limit=10000,
            since=since,
            agent_id=agent_ids[^0] if agent_ids else None,
        )
        
        if len(packets) < self.min_observations:
            return  # Not enough data for reliable pattern detection
        
        # 2. Build hypergraph adjacency
        hyperedges = self._build_hyperedges(packets)
        
        # 3. Encode via message-passing (simplified GNN)
        embeddings = self._encode_hypergraph(hyperedges)
        
        # 4. Cluster embeddings
        clusters = self._cluster_embeddings(embeddings)
        
        # 5. Extract patterns from dense clusters
        for cluster_id, members in clusters.items():
            pattern = self._extract_pattern_from_cluster(
                cluster_id, members, hyperedges
            )
            if pattern and pattern.confidence >= self.confidence_threshold:
                self._pattern_cache[str(pattern.pattern_id)] = pattern
                yield pattern
    
    def _build_hyperedges(
        self, packets: list[PacketEnvelope]
    ) -> dict[str, list[tuple[str, ...]]]:
        """Build hyperedges from packet entity co-occurrences."""
        hyperedges: dict[str, list[tuple[str, ...]]] = {}
        
        for packet in packets:
            # Extract entities from packet payload
            entities = self._extract_entities(packet)
            if len(entities) >= 2:
                # Create hyperedge for each N-ary co-occurrence
                edge_key = "|".join(sorted(entities))
                if edge_key not in hyperedges:
                    hyperedges[edge_key] = []
                hyperedges[edge_key].append(tuple(entities))
        
        return hyperedges
    
    def _extract_entities(self, packet: PacketEnvelope) -> list[str]:
        """Extract entity identifiers from packet payload."""
        entities = []
        payload = packet.payload or {}
        
        # Extract agent_id
        if packet.provenance and packet.provenance.agent_id:
            entities.append(f"agent:{packet.provenance.agent_id}")
        
        # Extract tool names
        if "tool_name" in payload:
            entities.append(f"tool:{payload['tool_name']}")
        
        # Extract thread context
        if packet.metadata and packet.metadata.thread_id:
            entities.append(f"thread:{packet.metadata.thread_id}")
        
        # Extract any referenced packet IDs
        if packet.lineage and packet.lineage.parent_ids:
            for parent in packet.lineage.parent_ids[:3]:  # Limit for performance
                entities.append(f"packet:{parent}")
        
        return entities
    
    def _encode_hypergraph(
        self, hyperedges: dict[str, list[tuple[str, ...]]]
    ) -> dict[str, np.ndarray]:
        """
        Simple GNN-style encoding: mean aggregation of neighbor embeddings.
        
        For production, replace with PyTorch Geometric HypergraphConv.
        """
        # Initialize random embeddings (in production: use pre-trained)
        all_entities = set()
        for edge_list in hyperedges.values():
            for edge in edge_list:
                all_entities.update(edge)
        
        embeddings = {
            entity: np.random.randn(self.embedding_dim).astype(np.float32)
            for entity in all_entities
        }
        
        # 2-layer message passing
        for _ in range(2):
            new_embeddings = {}
            for entity in all_entities:
                neighbors = []
                for edge_list in hyperedges.values():
                    for edge in edge_list:
                        if entity in edge:
                            neighbors.extend([e for e in edge if e != entity])
                
                if neighbors:
                    neighbor_embs = [embeddings[n] for n in neighbors if n in embeddings]
                    if neighbor_embs:
                        # Mean aggregation
                        new_embeddings[entity] = np.mean(neighbor_embs, axis=0)
                    else:
                        new_embeddings[entity] = embeddings[entity]
                else:
                    new_embeddings[entity] = embeddings[entity]
            
            embeddings = new_embeddings
        
        return embeddings
    
    def _cluster_embeddings(
        self, embeddings: dict[str, np.ndarray]
    ) -> dict[int, list[str]]:
        """Cluster embeddings via simple k-means (production: use HDBSCAN)."""
        if len(embeddings) < 10:
            return {}
        
        entities = list(embeddings.keys())
        X = np.array([embeddings[e] for e in entities])
        
        # Simple k-means clustering
        from sklearn.cluster import KMeans
        n_clusters = min(10, len(entities) // 5)
        if n_clusters < 2:
            return {}
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        
        clusters: dict[int, list[str]] = {}
        for entity, label in zip(entities, labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(entity)
        
        return clusters
    
    def _extract_pattern_from_cluster(
        self,
        cluster_id: int,
        members: list[str],
        hyperedges: dict[str, list[tuple[str, ...]]],
    ) -> Optional[DiscoveredPattern]:
        """Extract actionable pattern from cluster."""
        if len(members) < 3:
            return None
        
        # Count how often this cluster's members co-occur
        occurrence_count = 0
        for edge_list in hyperedges.values():
            for edge in edge_list:
                if set(edge) & set(members):
                    occurrence_count += 1
        
        if occurrence_count < self.min_observations:
            return None
        
        # Generate human-readable description
        entity_types = [m.split(":")[^0] for m in members[:5]]
        description = f"Recurring {'-'.join(set(entity_types))} co-occurrence pattern"
        
        # Suggest Neo4j label
        suggested_label = "_".join(sorted(set(entity_types))).upper() + "_CLUSTER"
        
        import uuid
        return DiscoveredPattern(
            pattern_id=uuid.uuid4(),
            entity_ids=tuple(members[:10]),  # Limit for readability
            relationship_type="DISCOVERED_COOCCURRENCE",
            confidence=min(0.99, occurrence_count / 1000),
            observation_count=occurrence_count,
            first_observed=datetime.utcnow() - timedelta(days=self.observation_window_days),
            last_observed=datetime.utcnow(),
            suggested_neo4j_label=suggested_label,
            human_readable_description=description,
        )
    
    async def export_patterns_for_review(
        self, output_path: str = "patterns_for_governance_review.jsonl"
    ) -> int:
        """
        Export discovered patterns to JSONL for Igor approval.
        
        Governance Gate: Patterns MUST be reviewed before schema modification.
        """
        import json
        
        count = 0
        async for pattern in self.discover_patterns():
            with open(output_path, "a") as f:
                f.write(json.dumps({
                    "pattern_id": str(pattern.pattern_id),
                    "entity_ids": pattern.entity_ids,
                    "relationship_type": pattern.relationship_type,
                    "confidence": pattern.confidence,
                    "observation_count": pattern.observation_count,
                    "suggested_neo4j_label": pattern.suggested_neo4j_label,
                    "human_readable_description": pattern.human_readable_description,
                    "requires_igor_approval": True,
                    "auto_apply_eligible": False,
                }) + "\n")
            count += 1
        
        return count
```


### TODO 0.2: Hive Memory Gradient Bus

**File:** `core/memory/hive_memory_bus.py` (NEW)
**Action:** INSERT
**Risk Tier:** T1 (Telemetry collection only)

```python
"""
Hive Memory Bus - Real-time gradient synchronization via Redis Streams.
Implements swarm synchronicity for L9 AIOS v5.0 per OpenAI Level 1 monitoring.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import AsyncIterator, Optional
from uuid import UUID, uuid4

import redis.asyncio as redis
from pydantic import BaseModel, Field


@dataclass(frozen=True)
class GradientPacket:
    """Memory gradient broadcast from agent learning."""
    gradient_id: UUID
    agent_id: str
    insight: str
    embedding: list[float]
    confidence: float
    timestamp: float
    tags: tuple[str, ...] = ()


class HiveMemoryBus:
    """
    Redis Streams-based gradient synchronization bus.
    
    Design Pattern: Pub/Sub with consumer groups for at-least-once delivery.
    
    INVARIANTS:
    - NEVER modifies agent behavior (Phase 0 is observation-only)
    - Gradients are advisory, not authoritative
    - All operations are append-only (no deletes)
    
    Frontier Benchmark: Federated learning broadcast pattern.
    """
    
    STREAM_KEY = "l9:memory:gradients"
    MAX_STREAM_LEN = 10000  # Rolling window
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        consumer_group: str = "l9_agents",
    ):
        self.redis_url = redis_url
        self.consumer_group = consumer_group
        self._client: Optional[redis.Redis] = None
        self._running = False
    
    async def connect(self) -> None:
        """Initialize Redis connection."""
        self._client = redis.from_url(self.redis_url, decode_responses=True)
        
        # Create consumer group if not exists
        try:
            await self._client.xgroup_create(
                self.STREAM_KEY,
                self.consumer_group,
                id="0",
                mkstream=True,
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        self._running = False
        if self._client:
            await self._client.close()
    
    async def publish_gradient(
        self,
        agent_id: str,
        insight: str,
        embedding: list[float],
        confidence: float,
        tags: list[str] | None = None,
    ) -> str:
        """
        Broadcast learning gradient to hive.
        
        When an agent learns something, it publishes the insight embedding
        so other agents can update their local "intuition" cache.
        
        Args:
            agent_id: Publishing agent's identifier
            insight: Natural language description of learning
            embedding: Vector representation (1536-dim for text-embedding-3-large)
            confidence: Learning confidence [0.0, 1.0]
            tags: Optional categorization tags
            
        Returns:
            Stream message ID
        """
        if not self._client:
            raise RuntimeError("HiveMemoryBus not connected")
        
        gradient = GradientPacket(
            gradient_id=uuid4(),
            agent_id=agent_id,
            insight=insight,
            embedding=embedding,
            confidence=confidence,
            timestamp=time.time(),
            tags=tuple(tags or []),
        )
        
        # Serialize and publish
        message_data = {
            "gradient_id": str(gradient.gradient_id),
            "agent_id": gradient.agent_id,
            "insight": gradient.insight,
            "embedding": json.dumps(gradient.embedding),
            "confidence": str(gradient.confidence),
            "timestamp": str(gradient.timestamp),
            "tags": json.dumps(gradient.tags),
        }
        
        msg_id = await self._client.xadd(
            self.STREAM_KEY,
            message_data,
            maxlen=self.MAX_STREAM_LEN,
        )
        
        return msg_id
    
    async def subscribe_gradients(
        self,
        consumer_id: str,
        block_ms: int = 1000,
    ) -> AsyncIterator[GradientPacket]:
        """
        Subscribe to gradient stream for real-time sync.
        
        Each agent runs this in a background task to maintain
        local embedding cache ("Intuition").
        
        Args:
            consumer_id: Unique consumer identifier (usually agent_id)
            block_ms: Blocking timeout for reads
            
        Yields:
            GradientPacket from other agents
        """
        if not self._client:
            raise RuntimeError("HiveMemoryBus not connected")
        
        self._running = True
        
        while self._running:
            try:
                messages = await self._client.xreadgroup(
                    self.consumer_group,
                    consumer_id,
                    {self.STREAM_KEY: ">"},
                    count=10,
                    block=block_ms,
                )
                
                for stream, msg_list in messages:
                    for msg_id, msg_data in msg_list:
                        try:
                            gradient = GradientPacket(
                                gradient_id=UUID(msg_data["gradient_id"]),
                                agent_id=msg_data["agent_id"],
                                insight=msg_data["insight"],
                                embedding=json.loads(msg_data["embedding"]),
                                confidence=float(msg_data["confidence"]),
                                timestamp=float(msg_data["timestamp"]),
                                tags=tuple(json.loads(msg_data.get("tags", "[]"))),
                            )
                            
                            # Skip own gradients
                            if gradient.agent_id != consumer_id:
                                yield gradient
                            
                            # Acknowledge processing
                            await self._client.xack(
                                self.STREAM_KEY,
                                self.consumer_group,
                                msg_id,
                            )
                        except (KeyError, ValueError, json.JSONDecodeError) as e:
                            # Log malformed message but continue
                            await self._client.xack(
                                self.STREAM_KEY,
                                self.consumer_group,
                                msg_id,
                            )
                            
            except asyncio.CancelledError:
                break
            except redis.ConnectionError:
                await asyncio.sleep(1)  # Reconnect backoff
    
    async def get_stream_stats(self) -> dict:
        """Get stream statistics for observability."""
        if not self._client:
            return {}
        
        info = await self._client.xinfo_stream(self.STREAM_KEY)
        return {
            "length": info.get("length", 0),
            "first_entry_id": info.get("first-entry", [None])[^0],
            "last_entry_id": info.get("last-entry", [None])[^0],
            "groups": info.get("groups", 0),
        }


class LocalEmbeddingCache:
    """
    Agent-local "Intuition" cache updated from hive gradients.
    
    This provides anticipatory context without explicit queries.
    """
    
    def __init__(self, max_size: int = 1000, decay_rate: float = 0.95):
        self.max_size = max_size
        self.decay_rate = decay_rate
        self._cache: dict[str, tuple[list[float], float, float]] = {}  # key -> (embedding, weight, timestamp)
    
    def update(self, gradient: GradientPacket) -> None:
        """Update cache with new gradient."""
        key = gradient.insight[:100]  # Use truncated insight as key
        
        if key in self._cache:
            # Weighted average with existing
            old_emb, old_weight, _ = self._cache[key]
            new_weight = old_weight * self.decay_rate + gradient.confidence
            new_emb = [
                (o * old_weight + n * gradient.confidence) / new_weight
                for o, n in zip(old_emb, gradient.embedding)
            ]
            self._cache[key] = (new_emb, new_weight, gradient.timestamp)
        else:
            self._cache[key] = (gradient.embedding, gradient.confidence, gradient.timestamp)
        
        # Evict oldest if over capacity
        if len(self._cache) > self.max_size:
            oldest = min(self._cache.items(), key=lambda x: x[^1][^2])
            del self._cache[oldest[^0]]
    
    def query(self, embedding: list[float], top_k: int = 5) -> list[tuple[str, float]]:
        """Find similar insights in cache via cosine similarity."""
        if not self._cache:
            return []
        
        import numpy as np
        query_vec = np.array(embedding)
        
        similarities = []
        for key, (emb, weight, _) in self._cache.items():
            emb_vec = np.array(emb)
            sim = np.dot(query_vec, emb_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(emb_vec) + 1e-8)
            similarities.append((key, float(sim * weight)))
        
        similarities.sort(key=lambda x: x[^1], reverse=True)
        return similarities[:top_k]
```


### TODO 0.3: Graph Utility Metrics Collection

**File:** `core/observability/graph_utility_metrics.py` (NEW)
**Action:** INSERT
**Risk Tier:** T1 (Metrics collection only)

```python
"""
Graph Utility Metrics - Track subgraph contribution to successful reasoning.
Implements autonomic resource steering telemetry per NIST AI RMF Measure function.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from collections import defaultdict

from prometheus_client import Counter, Histogram, Gauge


# Prometheus metrics
SUBGRAPH_REASONING_SUCCESS = Counter(
    "l9_subgraph_reasoning_success_total",
    "Successful reasoning operations by subgraph",
    ["subgraph_id", "agent_id"],
)

SUBGRAPH_REASONING_FAILURE = Counter(
    "l9_subgraph_reasoning_failure_total",
    "Failed reasoning operations by subgraph",
    ["subgraph_id", "agent_id"],
)

SUBGRAPH_QUERY_LATENCY = Histogram(
    "l9_subgraph_query_latency_seconds",
    "Query latency by subgraph",
    ["subgraph_id"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

SUBGRAPH_STORAGE_SIZE = Gauge(
    "l9_subgraph_storage_size_gb",
    "Storage size of subgraph in GB",
    ["subgraph_id", "storage_tier"],
)


@dataclass
class SubgraphMetrics:
    """Metrics for a single Neo4j subgraph."""
    subgraph_id: str
    successful_reasoning_count: int = 0
    failed_reasoning_count: int = 0
    total_query_latency_ms: float = 0.0
    query_count: int = 0
    storage_size_gb: float = 0.0
    last_accessed: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        total = self.successful_reasoning_count + self.failed_reasoning_count
        return self.successful_reasoning_count / total if total > 0 else 0.0
    
    @property
    def avg_query_latency_ms(self) -> float:
        return self.total_query_latency_ms / self.query_count if self.query_count > 0 else 0.0
    
    @property
    def utility_score(self) -> float:
        """
        Higher score = more valuable subgraph for reasoning.
        
        Formula: (success_rate * usage_frequency) / (latency * storage_cost)
        
        Used by AutonomicResourceManager to allocate NVMe/SSD/HDD tiers.
        """
        if self.query_count == 0:
            return 0.0
        
        success_factor = self.success_rate * self.successful_reasoning_count
        cost_factor = (self.avg_query_latency_ms / 1000.0) * (self.storage_size_gb + 0.1)
        
        return success_factor / cost_factor if cost_factor > 0 else 0.0


class GraphUtilityTracker:
    """
    Tracks Neo4j subgraph utility for autonomic resource allocation.
    
    Subgraphs are identified by their Neo4j label prefix (e.g., "Agent:", "Tool:", "Memory:").
    
    INVARIANTS:
    - Read-only during Phase 0 (no resource allocation changes)
    - All metrics exported to Prometheus for dashboarding
    - No PII in subgraph identifiers
    """
    
    def __init__(self):
        self._metrics: dict[str, SubgraphMetrics] = defaultdict(
            lambda: SubgraphMetrics(subgraph_id="unknown")
        )
    
    def record_successful_reasoning(
        self,
        subgraph_id: str,
        agent_id: str,
        query_latency_ms: float,
    ) -> None:
        """Record successful reasoning that used a subgraph."""
        metrics = self._metrics[subgraph_id]
        if metrics.subgraph_id == "unknown":
            metrics = SubgraphMetrics(subgraph_id=subgraph_id)
            self._metrics[subgraph_id] = metrics
        
        metrics.successful_reasoning_count += 1
        metrics.total_query_latency_ms += query_latency_ms
        metrics.query_count += 1
        metrics.last_accessed = datetime.utcnow()
        
        # Export to Prometheus
        SUBGRAPH_REASONING_SUCCESS.labels(
            subgraph_id=subgraph_id,
            agent_id=agent_id,
        ).inc()
        SUBGRAPH_QUERY_LATENCY.labels(subgraph_id=subgraph_id).observe(
            query_latency_ms / 1000.0
        )
    
    def record_failed_reasoning(
        self,
        subgraph_id: str,
        agent_id: str,
        query_latency_ms: float,
    ) -> None:
        """Record failed reasoning attempt on a subgraph."""
        metrics = self._metrics[subgraph_id]
        if metrics.subgraph_id == "unknown":
            metrics = SubgraphMetrics(subgraph_id=subgraph_id)
            self._metrics[subgraph_id] = metrics
        
        metrics.failed_reasoning_count += 1
        metrics.total_query_latency_ms += query_latency_ms
        metrics.query_count += 1
        metrics.last_accessed = datetime.utcnow()
        
        SUBGRAPH_REASONING_FAILURE.labels(
            subgraph_id=subgraph_id,
            agent_id=agent_id,
        ).inc()
    
    def update_storage_size(
        self,
        subgraph_id: str,
        storage_size_gb: float,
        storage_tier: str = "ssd",
    ) -> None:
        """Update storage size metrics for a subgraph."""
        metrics = self._metrics[subgraph_id]
        if metrics.subgraph_id == "unknown":
            metrics = SubgraphMetrics(subgraph_id=subgraph_id)
            self._metrics[subgraph_id] = metrics
        
        metrics.storage_size_gb = storage_size_gb
        
        SUBGRAPH_STORAGE_SIZE.labels(
            subgraph_id=subgraph_id,
            storage_tier=storage_tier,
        ).set(storage_size_gb)
    
    def get_ranked_subgraphs(self) -> list[SubgraphMetrics]:
        """Get subgraphs ranked by utility score (descending)."""
        return sorted(
            self._metrics.values(),
            key=lambda m: m.utility_score,
            reverse=True,
        )
    
    def get_storage_tier_recommendations(self) -> dict[str, str]:
        """
        Recommend storage tier allocation based on utility scores.
        
        Returns:
            Dict mapping subgraph_id to recommended tier ("nvme", "ssd", "hdd")
        """
        ranked = self.get_ranked_subgraphs()
        total = len(ranked)
        
        if total == 0:
            return {}
        
        recommendations = {}
        
        # Top 10% → NVMe
        nvme_cutoff = int(total * 0.1)
        for sg in ranked[:nvme_cutoff]:
            recommendations[sg.subgraph_id] = "nvme"
        
        # Next 40% → SSD
        ssd_cutoff = int(total * 0.5)
        for sg in ranked[nvme_cutoff:ssd_cutoff]:
            recommendations[sg.subgraph_id] = "ssd"
        
        # Remainder → HDD
        for sg in ranked[ssd_cutoff:]:
            recommendations[sg.subgraph_id] = "hdd"
        
        return recommendations
    
    def export_metrics_summary(self) -> dict:
        """Export summary for governance dashboard."""
        ranked = self.get_ranked_subgraphs()
        return {
            "total_subgraphs": len(ranked),
            "total_successful_reasoning": sum(m.successful_reasoning_count for m in ranked),
            "total_failed_reasoning": sum(m.failed_reasoning_count for m in ranked),
            "avg_utility_score": sum(m.utility_score for m in ranked) / len(ranked) if ranked else 0.0,
            "top_5_subgraphs": [
                {
                    "subgraph_id": m.subgraph_id,
                    "utility_score": m.utility_score,
                    "success_rate": m.success_rate,
                    "avg_latency_ms": m.avg_query_latency_ms,
                }
                for m in ranked[:5]
            ],
            "storage_tier_recommendations": self.get_storage_tier_recommendations(),
        }


# Singleton instance
_tracker: Optional[GraphUtilityTracker] = None


def get_graph_utility_tracker() -> GraphUtilityTracker:
    """Get or create singleton tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = GraphUtilityTracker()
    return _tracker
```


***

## Phase 1: Supervised Evolution (Months 4-12)

### TODO 1.1: Shadow Schema Testing Infrastructure

**File:** `config/schema_evolution_policy.yaml` (NEW)
**Action:** INSERT
**Risk Tier:** T2 (Reversible with rollback)

```yaml
# Schema Evolution Policy - L9 AIOS v5.0
# Governance: Igor approval required for all production schema changes
# Frontier Standard: EU Annex 22 data independence requirements

schema_evolution:
  mode: "supervised_learning"  # Options: "disabled" | "supervised_learning" | "autonomous"
  
  discovery:
    enabled: true
    min_observations: 100
    confidence_threshold: 0.85
    observation_window_days: 30
    max_patterns_per_run: 50
    excluded_packet_types:
      - "heartbeat"
      - "health_check"
  
  shadow_testing:
    enabled: true
    namespace: "neo4j_experimental"
    trial_period_days: 90
    promotion_criteria:
      - metric: "agent_task_success_rate"
        improvement_threshold: 0.05  # Must improve by 5%
        comparison_window_days: 30
      - metric: "query_latency_p99"
        degradation_limit: 1.2  # Max 20% latency increase
      - metric: "storage_overhead"
        max_increase_percent: 10
    rollback_triggers:
      - condition: "error_rate > 0.01"
        action: "auto_rollback"
      - condition: "latency_increase > 50%"
        action: "alert_and_pause"
  
  governance:
    auto_promote: false  # NEVER auto-promote in supervised mode
    require_igor_approval: true
    approval_timeout_hours: 168  # 1 week
    rollback_on_timeout: true
    audit_trail: "memory/schema_evolution_audit.jsonl"
    
    # Risk tiering per OpenAI Preparedness Framework
    risk_tiers:
      T1_LOW:
        description: "Read-only schema additions (new indexes)"
        requires_approval: false
        auto_rollback: true
      T2_MEDIUM:
        description: "New node labels in experimental namespace"
        requires_approval: true
        shadow_test_required: true
      T3_HIGH:
        description: "Production schema modifications"
        requires_approval: true
        shadow_test_required: true
        min_trial_days: 90
  
  formal_verification:
    enabled: false  # Enable in Phase 3
    lean_prover_path: "/opt/lean4/bin/lean"
    proof_timeout_seconds: 3600
    required_proofs:
      - "backward_compatibility"
      - "no_cycle_introduction"
      - "access_control_preservation"

# Invariant: Changes to this file require Igor approval
# Last modified: 2026-01-14
# Approved by: Igor (pending)
```


### TODO 1.2: Adaptive Schema Manager

**File:** `core/memory/adaptive_schema.py` (NEW)
**Action:** INSERT
**Risk Tier:** T2

```python
"""
Adaptive Schema Manager - Hybrid static-dynamic schema evolution.
Implements Phase 1 supervised learning per ISO 42001 PDCA cycle.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

import yaml
from pydantic import BaseModel, Field

from services.research.hypergraph_learner import DiscoveredPattern, HypergraphLearner
from memory.substrate_service import MemorySubstrateService
from memory.graph_client import Neo4jClient


class SchemaChangeRisk(str, Enum):
    """Risk tier for schema changes."""
    T1_LOW = "T1_LOW"
    T2_MEDIUM = "T2_MEDIUM"
    T3_HIGH = "T3_HIGH"


class SchemaChangeStatus(str, Enum):
    """Status of schema change proposal."""
    PROPOSED = "proposed"
    SHADOW_TESTING = "shadow_testing"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class SchemaChangeProposal:
    """Proposal for schema evolution."""
    proposal_id: UUID
    pattern: DiscoveredPattern
    risk_tier: SchemaChangeRisk
    status: SchemaChangeStatus
    proposed_at: datetime
    proposed_by: str  # "system" or agent_id
    neo4j_migration: str  # Cypher migration script
    rollback_script: str  # Cypher rollback script
    shadow_namespace: str
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    approval_by: Optional[str] = None
    approval_at: Optional[datetime] = None
    metrics_before: Optional[dict] = None
    metrics_after: Optional[dict] = None


class AdaptiveSchemaManager:
    """
    Manages schema evolution from pattern discovery to production promotion.
    
    LIFECYCLE:
    1. HypergraphLearner discovers pattern
    2. Manager creates SchemaChangeProposal
    3. Proposal enters shadow_testing in experimental namespace
    4. After trial_period_days, metrics compared
    5. If criteria met → AWAITING_APPROVAL
    6. Igor approves → PROMOTED to production
    7. On error → ROLLED_BACK
    
    INVARIANTS (Protected Surfaces):
    - NEVER modifies production schema without Igor approval
    - ALL changes have rollback scripts
    - Shadow testing isolated to neo4j_experimental namespace
    """
    
    def __init__(
        self,
        substrate: MemorySubstrateService,
        neo4j_client: Neo4jClient,
        learner: HypergraphLearner,
        policy_path: str = "config/schema_evolution_policy.yaml",
    ):
        self.substrate = substrate
        self.neo4j = neo4j_client
        self.learner = learner
        self._policy = self._load_policy(policy_path)
        self._proposals: dict[UUID, SchemaChangeProposal] = {}
    
    def _load_policy(self, path: str) -> dict:
        """Load schema evolution policy."""
        with open(path) as f:
            return yaml.safe_load(f)
    
    async def discover_and_propose(self) -> list[SchemaChangeProposal]:
        """
        Run pattern discovery and create schema change proposals.
        
        Returns:
            List of new SchemaChangeProposal objects for governance review.
        """
        if not self._policy["schema_evolution"]["discovery"]["enabled"]:
            return []
        
        proposals = []
        
        async for pattern in self.learner.discover_patterns():
            # Determine risk tier based on pattern characteristics
            risk_tier = self._assess_risk_tier(pattern)
            
            # Generate migration scripts
            migration = self._generate_migration(pattern)
            rollback = self._generate_rollback(pattern)
            
            proposal = SchemaChangeProposal(
                proposal_id=uuid4(),
                pattern=pattern,
                risk_tier=risk_tier,
                status=SchemaChangeStatus.PROPOSED,
                proposed_at=datetime.utcnow(),
                proposed_by="system",
                neo4j_migration=migration,
                rollback_script=rollback,
                shadow_namespace=self._policy["schema_evolution"]["shadow_testing"]["namespace"],
            )
            
            self._proposals[proposal.proposal_id] = proposal
            proposals.append(proposal)
            
            # Log to audit trail
            await self._log_audit_event("proposal_created", proposal)
        
        return proposals
    
    def _assess_risk_tier(self, pattern: DiscoveredPattern) -> SchemaChangeRisk:
        """Assess risk tier for pattern-based schema change."""
        # T1: Adding optional index or constraint
        if pattern.relationship_type == "DISCOVERED_COOCCURRENCE":
            return SchemaChangeRisk.T1_LOW
        
        # T2: New node label (in experimental namespace)
        if pattern.suggested_neo4j_label.endswith("_CLUSTER"):
            return SchemaChangeRisk.T2_MEDIUM
        
        # T3: Everything else
        return SchemaChangeRisk.T3_HIGH
    
    def _generate_migration(self, pattern: DiscoveredPattern) -> str:
        """Generate Cypher migration script for pattern."""
        label = pattern.suggested_neo4j_label
        
        return f"""
// Migration for pattern: {pattern.human_readable_description}
// Generated: {datetime.utcnow().isoformat()}
// Risk Tier: Auto-assessed (requires Igor approval for production)

// Create new node label in experimental namespace
CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.pattern_id IS UNIQUE;

// Create index for efficient lookups
CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.first_observed);

// Note: Actual data population requires separate approval
// This migration only creates the schema structure
"""
    
    def _generate_rollback(self, pattern: DiscoveredPattern) -> str:
        """Generate Cypher rollback script for pattern."""
        label = pattern.suggested_neo4j_label
        
        return f"""
// Rollback for pattern: {pattern.human_readable_description}
// Generated: {datetime.utcnow().isoformat()}

// Remove all nodes with this label
MATCH (n:{label}) DETACH DELETE n;

// Drop constraint
DROP CONSTRAINT IF EXISTS FOR (n:{label}) REQUIRE n.pattern_id IS UNIQUE;

// Drop index
DROP INDEX IF EXISTS FOR (n:{label}) ON (n.first_observed);
"""
    
    async def start_shadow_test(self, proposal_id: UUID) -> bool:
        """
        Begin shadow testing for a proposal.
        
        Applies migration to experimental namespace only.
        """
        if proposal_id not in self._proposals:
            return False
        
        proposal = self._proposals[proposal_id]
        
        if proposal.status != SchemaChangeStatus.PROPOSED:
            return False
        
        # Capture baseline metrics
        metrics_before = await self._capture_metrics()
        
        # Apply migration to experimental namespace
        try:
            # Prefix all labels with experimental namespace
            experimental_migration = proposal.neo4j_migration.replace(
                f"(n:{proposal.pattern.suggested_neo4j_label})",
                f"(n:__experimental__{proposal.pattern.suggested_neo4j_label})"
            )
            
            await self.neo4j.run_query(experimental_migration, {})
            
            # Update proposal status
            trial_days = self._policy["schema_evolution"]["shadow_testing"]["trial_period_days"]
            updated = SchemaChangeProposal(
                proposal_id=proposal.proposal_id,
                pattern=proposal.pattern,
                risk_tier=proposal.risk_tier,
                status=SchemaChangeStatus.SHADOW_TESTING,
                proposed_at=proposal.proposed_at,
                proposed_by=proposal.proposed_by,
                neo4j_migration=proposal.neo4j_migration,
                rollback_script=proposal.rollback_script,
                shadow_namespace=proposal.shadow_namespace,
                trial_start=datetime.utcnow(),
                trial_end=datetime.utcnow() + timedelta(days=trial_days),
                metrics_before=metrics_before,
            )
            
            self._proposals[proposal_id] = updated
            await self._log_audit_event("shadow_test_started", updated)
            
            return True
            
        except Exception as e:
            await self._log_audit_event("shadow_test_failed", proposal, error=str(e))
            return False
    
    async def evaluate_trial(self, proposal_id: UUID) -> dict:
        """
        Evaluate shadow test results after trial period.
        
        Returns:
            Dict with evaluation results and recommendation.
        """
        if proposal_id not in self._proposals:
            return {"error": "Proposal not found"}
        
        proposal = self._proposals[proposal_id]
        
        if proposal.status != SchemaChangeStatus.SHADOW_TESTING:
            return {"error": "Proposal not in shadow testing"}
        
        if datetime.utcnow() < proposal.trial_end:
            return {
                "status": "in_progress",
                "days_remaining": (proposal.trial_end - datetime.utcnow()).days,
            }
        
        # Capture current metrics
        metrics_after = await self._capture_metrics()
        
        # Evaluate against promotion criteria
        criteria = self._policy["schema_evolution"]["shadow_testing"]["promotion_criteria"]
        evaluation = self._evaluate_criteria(proposal.metrics_before, metrics_after, criteria)
        
        # Update proposal
        if evaluation["meets_criteria"]:
            new_status = SchemaChangeStatus.AWAITING_APPROVAL
        else:
            new_status = SchemaChangeStatus.REJECTED
        
        updated = SchemaChangeProposal(
            proposal_id=proposal.proposal_id,
            pattern=proposal.pattern,
            risk_tier=proposal.risk_tier,
            status=new_status,
            proposed_at=proposal.proposed_at,
            proposed_by=proposal.proposed_by,
            neo4j_migration=proposal.neo4j_migration,
            rollback_script=proposal.rollback_script,
            shadow_namespace=proposal.shadow_namespace,
            trial_start=proposal.trial_start,
            trial_end=proposal.trial_end,
            metrics_before=proposal.metrics_before,
            metrics_after=metrics_after,
        )
        
        self._proposals[proposal_id] = updated
        await self._log_audit_event("trial_evaluated", updated, evaluation=evaluation)
        
        return evaluation
    
    async def approve_and_promote(
        self,
        proposal_id: UUID,
        approved_by: str,
    ) -> bool:
        """
        Promote approved schema change to production.
        
        GOVERNANCE GATE: This method requires Igor approval.
        """
        if proposal_id not in self._proposals:
            return False
        
        proposal = self._proposals[proposal_id]
        
        if proposal.status != SchemaChangeStatus.AWAITING_APPROVAL:
            return False
        
        # Validate approver (must be Igor or delegated authority)
        if approved_by.lower() != "igor":
            await self._log_audit_event(
                "approval_rejected",
                proposal,
                reason=f"Unauthorized approver: {approved_by}",
            )
            return False
        
        try:
            # Apply migration to production
            await self.neo4j.run_query(proposal.neo4j_migration, {})
            
            # Update proposal status
            updated = SchemaChangeProposal(
                proposal_id=proposal.proposal_id,
                pattern=proposal.pattern,
                risk_tier=proposal.risk_tier,
                status=SchemaChangeStatus.PROMOTED,
                proposed_at=proposal.proposed_at,
                proposed_by=proposal.proposed_by,
                neo4j_migration=proposal.neo4j_migration,
                rollback_script=proposal.rollback_script,
                shadow_namespace=proposal.shadow_namespace,
                trial_start=proposal.trial_start,
                trial_end=proposal.trial_end,
                metrics_before=proposal.metrics_before,
                metrics_after=proposal.metrics_after,
                approval_by=approved_by,
                approval_at=datetime.utcnow(),
            )
            
            self._proposals[proposal_id] = updated
            await self._log_audit_event("schema_promoted", updated)
            
            # Clean up experimental namespace
            await self._cleanup_experimental(proposal)
            
            return True
            
        except Exception as e:
            await self._log_audit_event("promotion_failed", proposal, error=str(e))
            return False
    
    async def rollback(self, proposal_id: UUID, reason: str) -> bool:
        """Execute rollback for a promoted schema change."""
        if proposal_id not in self._proposals:
            return False
        
        proposal = self._proposals[proposal_id]
        
        try:
            await self.neo4j.run_query(proposal.rollback_script, {})
            
            updated = SchemaChangeProposal(
                proposal_id=proposal.proposal_id,
                pattern=proposal.pattern,
                risk_tier=proposal.risk_tier,
                status=SchemaChangeStatus.ROLLED_BACK,
                proposed_at=proposal.proposed_at,
                proposed_by=proposal.proposed_by,
                neo4j_migration=proposal.neo4j_migration,
                rollback_script=proposal.rollback_script,
                shadow_namespace=proposal.shadow_namespace,
                trial_start=proposal.trial_start,
                trial_end=proposal.trial_end,
                metrics_before=proposal.metrics_before,
                metrics_after=proposal.metrics_after,
                approval_by=proposal.approval_by,
                approval_at=proposal.approval_at,
            )
            
            self._proposals[proposal_id] = updated
            await self._log_audit_event("schema_rolled_back", updated, reason=reason)
            
            return True
            
        except Exception as e:
            await self._log_audit_event("rollback_failed", proposal, error=str(e))
            return False
    
    async def _capture_metrics(self) -> dict:
        """Capture current system metrics for comparison."""
        # This would query Prometheus/observability system
        return {
            "agent_task_success_rate": 0.85,  # Placeholder
            "query_latency_p99": 0.5,
            "storage_overhead": 10.0,
            "captured_at": datetime.utcnow().isoformat(),
        }
    
    def _evaluate_criteria(
        self,
        before: dict,
        after: dict,
        criteria: list[dict],
    ) -> dict:
        """Evaluate promotion criteria."""
        results = []
        meets_all = True
        
        for criterion in criteria:
            metric = criterion["metric"]
            before_val = before.get(metric, 0)
            after_val = after.get(metric, 0)
            
            if "improvement_threshold" in criterion:
                improvement = (after_val - before_val) / before_val if before_val > 0 else 0
                passed = improvement >= criterion["improvement_threshold"]
            elif "degradation_limit" in criterion:
                ratio = after_val / before_val if before_val > 0 else 1
                passed = ratio <= criterion["degradation_limit"]
            else:
                passed = True
            
            results.append({
                "metric": metric,
                "before": before_val,
                "after": after_val,
                "passed": passed,
            })
            
            if not passed:
                meets_all = False
        
        return {
            "meets_criteria": meets_all,
            "criteria_results": results,
            "recommendation": "PROMOTE" if meets_all else "REJECT",
        }
    
    async def _cleanup_experimental(self, proposal: SchemaChangeProposal) -> None:
        """Clean up experimental namespace after promotion."""
        cleanup_query = proposal.rollback_script.replace(
            f"(n:{proposal.pattern.suggested_neo4j_label})",
            f"(n:__experimental__{proposal.pattern.suggested_neo4j_label})"
        )
        await self.neo4j.run_query(cleanup_query, {})
    
    async def _log_audit_event(
        self,
        event_type: str,
        proposal: SchemaChangeProposal,
        **kwargs,
    ) -> None:
        """Log event to audit trail."""
        audit_path = self._policy["schema_evolution"]["governance"]["audit_trail"]
        
        event = {
            "event_type": event_type,
            "proposal_id": str(proposal.proposal_id),
            "pattern_id": str(proposal.pattern.pattern_id),
            "status": proposal.status.value,
            "risk_tier": proposal.risk_tier.value,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }
        
        with open(audit_path, "a") as f:
            f.write(json.dumps(event) + "\n")
```


***

## Gap Analysis Summary

| Current L9 State | Frontier Standard | Upgrade Path |
| :-- | :-- | :-- |
| Static schema in `core/schemas/packet_envelope.py` | ISO 42001 adaptive management | AdaptiveSchemaManager with shadow testing |
| Individual agent memory via `MemorySubstrateService` | OpenAI Level 2 coordinated agents | HiveMemoryBus with gradient synchronization |
| Human-defined governance in `/governance/` | NIST AI RMF autonomic controls | GraphUtilityTracker with utility-based allocation |
| Manual migrations in `/migrations/` | EU Annex 22 data independence | Automated shadow testing with rollback |
| Reactive memory queries | OpenAI Level 3 anticipatory | LocalEmbeddingCache with proactive priming |


***

## Success Criteria (Phase 0)

| Metric | Target | Measurement |
| :-- | :-- | :-- |
| HypergraphLearner uptime | 30 days without errors | Prometheus `l9_hypergraph_learner_errors_total` |
| Patterns discovered | ≥10 with confidence >0.85 | `patterns_for_governance_review.jsonl` count |
| Gradient bus throughput | ≥1000 msg/day, <10ms latency | Redis Streams metrics |
| Graph utility metrics coverage | 100% of Neo4j labels | `l9_subgraph_storage_size_gb` gauge |


***

## Governance Gates

1. **Phase 0 → Phase 1**: Igor approves after 30-day observation period with zero critical incidents[^2]
2. **Shadow Test → Production**: Igor approval required for all T2/T3 schema changes
3. **Phase 2 → Phase 3**: <5% false positive rate in autonomous proposals over 12 months
4. **Emergency Stop**: Igor retains `/L rollback <proposal_id>` command at all times

This execution guide preserves all L9 invariants while enabling measured evolution toward collective intelligence.[^3][^1]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: pydantic_models.txt

[^2]: governance_model.txt

[^3]: class_definitions.txt

[^4]: wiring_map.txt

[^5]: tool_catalog.txt

[^6]: test_catalog.txt

[^7]: telemetry_endpoints.txt

[^8]: singleton_registry.txt

[^9]: route_handlers.txt

[^10]: migration_catalog.txt

[^11]: kernel_catalog.txt

[^12]: inheritance_graph.txt

[^13]: file_metrics.txt

[^14]: feature_flags.txt

[^15]: event_types.txt

[^16]: env_refs.txt

[^17]: entrypoints.txt

[^18]: deployment_manifest.txt

[^19]: dependencies.txt

[^20]: decorator_catalog.txt

[^21]: config_files.txt

[^22]: async_function_map.txt

