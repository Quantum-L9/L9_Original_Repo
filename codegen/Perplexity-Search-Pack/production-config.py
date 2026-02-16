#!/usr/bin/env python3
"""
Production Configuration & Requirements for Perplexity Super-Prompt System
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Production-Config",
    "module_version": "1.0.0",
    "created_by": "L9_Codegen_Engine",
    "created_at": "2025-12-16T21:54:14Z",
    "updated_at": "2026-01-12T15:56:02Z",
    "layer": "foundation",
    "domain": "code_generation",
    "module_name": "production-config",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["HTTP API", "Perplexity API", "Redis", "S3"],
        "memory_layers": ["semantic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

# ============================================================================
# requirements.txt
# ============================================================================
# Core dependencies for autonomous research agent

# HTTP client with async support
httpx==0.25.2
httpcore==1.1.0

# Retry logic with exponential backoff
tenacity==8.2.3

# Deep learning framework (for architecture implementation)
torch==2.1.1
torchvision==0.16.1  # Vision features for multi-modal

# Transformers for embeddings and encoders
transformers==4.35.2
tokenizers==0.14.1

# Data processing and serialization
numpy==1.26.2
pandas==2.1.3
pydantic==2.5.0

# Async utilities
asyncio==3.4.3
aiofiles==23.2.1

# Testing and quality assurance
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-timeout==2.2.0

# Code quality
black==23.11.0
pylint==3.0.3
mypy==1.7.1
flake8==6.1.0

# Logging and monitoring
python-json-logger==2.0.7
structlog==23.3.0

# Development utilities
ipython==8.18.1
jupyterlab==4.0.9
notebook==7.0.6

# Type hints
typing-extensions==4.8.0

# Environment variables
python-dotenv==1.0.0

# Rate limiting and throttling
pyrate-limiter==3.1.1

# Optional: GPU optimization
# bitsandbytes==0.41.2  # For 8-bit quantization
# flash-attn==2.3.6     # For efficient attention

# ============================================================================
# Model Configuration (model_config.yaml)
# ============================================================================
# YAML format for model hyperparameters

model_config_yaml = """
# Hybrid Sparse-Neural Model Configuration

# Architecture parameters
architecture:
  input_dim: 768                    # Standard transformer dimension
  hidden_dim: 2048                  # FFN intermediate dimension
  num_experts: 8                    # Number of sparse experts
  top_k: 2                          # Top-K experts to activate per sample
  dropout_rate: 0.1                 # Dropout for regularization

# Multi-modal encoders
multimodal:
  text_encoder:
    type: "transformer"
    pretrained: "sentence-transformers/all-MiniLM-L6-v2"
    freeze_layers: false
    output_dim: 768

  vision_encoder:
    type: "vit"
    variant: "vit-base"
    pretrained: true
    output_dim: 1024

  structured_encoder:
    type: "learned_embedding"
    max_features: 1024
    embedding_dim: 512
    output_dim: 768

  fusion_strategy: "attention_weighted"  # Options: attention_weighted, concatenate, gated_add

# Expert configuration
experts:
  architecture: "feed_forward"      # Options: feed_forward, moe, attention
  activation: "gelu"                # Options: gelu, relu, mish
  layer_norm: true
  residual_connection: true

# Gating network
gating:
  type: "top_k"                     # Options: top_k, softmax, sparse_softmax
  k: 2
  expert_capacity: 1.25             # Capacity per expert
  importance_warmup_steps: 1000

# Training hyperparameters
training:
  batch_size: 32
  learning_rate: 0.001
  weight_decay: 0.01
  max_gradient_norm: 1.0
  warmup_steps: 1000
  total_steps: 100000
  gradient_accumulation_steps: 1
  mixed_precision: "fp16"           # Options: fp16, bf16, fp32

# Optimization
optimization:
  optimizer: "adamw"                # Options: adamw, sgd
  scheduler: "cosine"               # Options: cosine, linear, constant
  clip_gradients: true
  clip_value: 1.0

# Regularization
regularization:
  dropout: 0.1
  layer_dropout: 0.1
  zoneout: 0.0                      # Only for RNN layers
  label_smoothing: 0.0              # For classification

# Sparse computation
sparse_computation:
  enable_expert_dropout: true       # Randomly drop experts during training
  expert_dropout_rate: 0.1
  enable_sparse_backprop: true      # Only backprop through active experts
  load_balancing_loss_weight: 0.01  # Auxiliary loss for expert load balancing

# Scaling properties (power-law parameters)
scaling:
  alpha_compute: 0.5                # Scaling exponent for compute
  alpha_model: 0.5                  # Scaling exponent for model size
  target_compute_ratio: 0.7         # Target sparse computation ratio

# Inference configuration
inference:
  batch_size: 64
  max_tokens: 512
  temperature: 0.7
  top_p: 0.95
  top_k: 50
  num_beams: 1                      # 1 = greedy, >1 = beam search
  early_stopping: false

# Deployment
deployment:
  device: "cuda"                    # Options: cuda, cpu, mps
  dtype: "float32"                  # Options: float32, float16, bfloat16
  quantization: null                # Options: int8, int4, null
  use_flash_attention: true
  use_paged_attention: true
  max_batch_size: 128
  num_workers: 8

# Checkpointing and logging
checkpointing:
  save_interval_steps: 1000
  keep_latest_k: 3
  save_optimizer_state: true
  save_gradient_state: false

logging:
  log_level: "INFO"                 # Options: DEBUG, INFO, WARNING, ERROR
  log_format: "json"                # Options: json, text
  log_frequency_steps: 100
  tensorboard_dir: "./logs/tensorboard"
  wandb_project: "hybrid-sparse"    # Leave null to disable W&B
  wandb_entity: null

# Monitoring
monitoring:
  track_expert_utilization: true
  track_compute_efficiency: true
  track_inference_latency: true
  compute_metrics_frequency_steps: 100

# Cache
cache:
  enable_kv_cache: true
  cache_dtype: "float16"
  max_cache_size_gb: 8

# Evaluation
evaluation:
  eval_interval_steps: 500
  eval_dataset_size: 1024
  compute_perplexity: true
  compute_downstream_metrics: true
  downstream_tasks:
    - "qa"
    - "summarization"
    - "entailment"
"""

# ============================================================================
# Deployment Configuration (deployment_config.yaml)

deployment_config_yaml = """
# Deployment Configuration for Production

# Container settings
container:
  image: "hybrid-sparse:latest"
  registry: "docker.io"
  python_version: "3.11"
  base_image: "pytorch/pytorch:2.1.1-cuda12.1-runtime-ubuntu22.04"

# Kubernetes deployment
kubernetes:
  namespace: "ml-inference"
  replicas: 3
  
  # Resource requests and limits
  resources:
    requests:
      cpu: "4"
      memory: "16Gi"
      gpu: "1"
    limits:
      cpu: "8"
      memory: "32Gi"
      gpu: "2"
  
  # Health checks
  liveness_probe:
    http_get:
      path: "/health/live"
      port: 8000
    initial_delay_seconds: 30
    period_seconds: 10
    timeout_seconds: 5
    failure_threshold: 3
  
  readiness_probe:
    http_get:
      path: "/health/ready"
      port: 8000
    initial_delay_seconds: 10
    period_seconds: 5
    timeout_seconds: 3
    failure_threshold: 3
  
  # Scaling
  autoscaling:
    enabled: true
    min_replicas: 2
    max_replicas: 10
    target_cpu_utilization: 70
    target_memory_utilization: 80
    target_request_latency_ms: 100

# Service configuration
service:
  type: "LoadBalancer"              # Options: ClusterIP, NodePort, LoadBalancer
  port: 8000
  target_port: 8000
  protocol: "TCP"
  
  # Rate limiting
  rate_limit:
    enabled: true
    requests_per_second: 100
    burst_size: 200

# API Gateway configuration
api_gateway:
  enabled: true
  timeout_seconds: 120
  max_request_size_mb: 100
  max_response_size_mb: 50
  
  # Caching
  cache:
    enabled: true
    ttl_seconds: 300
    max_size_mb: 1000

# Logging and monitoring
observability:
  logging:
    level: "INFO"
    format: "json"
    destination: "stdout"            # Options: stdout, file, cloud
    retention_days: 30
    
  metrics:
    enabled: true
    prometheus_port: 9090
    scrape_interval_seconds: 15
    
  tracing:
    enabled: true
    backend: "jaeger"                # Options: jaeger, datadog, honeycomb
    sample_rate: 0.1
    
  profiling:
    enabled: false                   # Enable for debugging only
    profile_type: "cpu"              # Options: cpu, memory

# Database configuration
database:
  type: "postgresql"                # Options: postgresql, mongodb, redis
  host: "db.ml-inference.svc.cluster.local"
  port: 5432
  database: "hybrid_sparse"
  
  # Connection pooling
  pool:
    min_size: 5
    max_size: 20
    idle_timeout_seconds: 300
  
  # Replication
  replication:
    enabled: true
    replicas: 2

# Cache layer
cache:
  type: "redis"                     # Options: redis, memcached, in-memory
  host: "redis.ml-inference.svc.cluster.local"
  port: 6379
  database: 0
  
  # Clustering
  cluster:
    enabled: false
    nodes: 3
    replicas: 1

# Security
security:
  authentication:
    enabled: true
    type: "oauth2"                  # Options: oauth2, mTLS, api_key
    provider: "auth0"
  
  authorization:
    enabled: true
    type: "rbac"
  
  encryption:
    in_transit:
      enabled: true
      protocol: "tls1.3"
    at_rest:
      enabled: true
      algorithm: "AES-256-GCM"
  
  rate_limiting:
    enabled: true
    per_user: true
    per_api_key: true

# Model serving
model_serving:
  framework: "vllm"                 # Options: vllm, triton, seldon
  
  # Batching
  batching:
    enabled: true
    batch_size: 32
    max_wait_ms: 100
  
  # Quantization
  quantization:
    enabled: false
    type: "int8"                    # Options: int8, int4, fp16
  
  # Compilation
  compilation:
    enabled: true
    backend: "torch.compile"        # Options: torch.compile, torchscript, onnx

# Disaster recovery
disaster_recovery:
  backup:
    enabled: true
    frequency: "hourly"
    retention_days: 30
    storage: "s3"                   # Options: s3, gcs, azure_blob
    bucket: "hybrid-sparse-backups"
  
  recovery:
    rpo_minutes: 60                 # Recovery Point Objective
    rto_minutes: 15                 # Recovery Time Objective
    test_frequency_days: 7

# Cost optimization
cost_optimization:
  spot_instances:
    enabled: true
    max_interruption_rate: 0.05
  
  auto_shutdown:
    enabled: true
    idle_threshold_minutes: 30
  
  resource_optimization:
    cpu_overcommit_ratio: 1.5
    memory_overcommit_ratio: 1.2

# Update strategy
update_strategy:
  type: "rolling"                   # Options: rolling, blue_green, canary
  max_surge: "25%"
  max_unavailable: "25%"
  
  # Canary deployment
  canary:
    enabled: false
    initial_traffic_percent: 10
    increment_percent: 20
    increment_interval_minutes: 5
"""

# ============================================================================
# Logging Configuration (logging_config.yaml)

logging_config_yaml = """
# Structured Logging Configuration

version: 1
disable_existing_loggers: false

formatters:
  json:
    class: pythonjsonlogger.jsonlogger.JsonFormatter
    format: "%(timestamp)s %(name)s %(levelname)s %(message)s"
  
  text:
    format: "[%(asctime)s] %(name)s - %(levelname)s - %(message)s"

handlers:
  console:
    class: logging.StreamHandler
    formatter: json
    level: INFO
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    formatter: json
    level: DEBUG
    filename: logs/app.log
    maxBytes: 10485760              # 10MB
    backupCount: 10

loggers:
  root:
    level: INFO
    handlers: [console, file]
  
  perplexity_agent:
    level: DEBUG
    handlers: [console, file]
  
  torch:
    level: WARNING
  
  transformers:
    level: INFO
  
  asyncio:
    level: INFO

# Performance metrics logging
metrics:
  inference_latency:
    enabled: true
    histogram_buckets: [10, 50, 100, 250, 500, 1000, 2000, 5000]
  
  expert_utilization:
    enabled: true
    track_per_expert: true
  
  memory_usage:
    enabled: true
    sample_interval_seconds: 60
  
  compute_efficiency:
    enabled: true
    track_sparse_ratio: true
    track_flops: true
"""

# ============================================================================
# Print all configurations

if __name__ == "__main__":
    print("=" * 80)  # noqa: ADR-0019
    print("PERPLEXITY SUPER-PROMPT PRODUCTION CONFIGURATION")  # noqa: ADR-0019
    print("=" * 80)  # noqa: ADR-0019
    
    print("\n[1] requirements.txt")  # noqa: ADR-0019
    print("-" * 80)  # noqa: ADR-0019
    with open("requirements.txt", "r") as f:
        print(f.read())  # noqa: ADR-0019
    
    print("\n[2] model_config.yaml")  # noqa: ADR-0019
    print("-" * 80)  # noqa: ADR-0019
    print(model_config_yaml)  # noqa: ADR-0019
    
    print("\n[3] deployment_config.yaml")  # noqa: ADR-0019
    print("-" * 80)  # noqa: ADR-0019
    print(deployment_config_yaml)  # noqa: ADR-0019
    
    print("\n[4] logging_config.yaml")  # noqa: ADR-0019
    print("-" * 80)  # noqa: ADR-0019
    print(logging_config_yaml)  # noqa: ADR-0019
    
    print("\n" + "=" * 80)  # noqa: ADR-0019
    print("To use these configurations:")  # noqa: ADR-0019
    print("1. Copy requirements.txt to your project root")  # noqa: ADR-0019
    print("2. Save YAML configs to ./config/ directory")  # noqa: ADR-0019
    print("3. Load in your code: yaml.safe_load(open('config/model_config.yaml'))")  # noqa: ADR-0019
    print("=" * 80)  # noqa: ADR-0019

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "COD-FOUN-001",
    "governance_level": "critical",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "auth", "batch-processing", "caching", "cli", "code-generation", "code-quality", "debugging", "foundation", "linting"],
    "keywords": ["production"],
    "business_value": "Utility module for production-config",
    "last_modified": "2026-01-12T15:56:02Z",
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
