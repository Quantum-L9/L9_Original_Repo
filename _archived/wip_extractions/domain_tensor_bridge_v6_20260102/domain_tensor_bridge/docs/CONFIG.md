# Configuration

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `L9_REDIS_URL` | Redis connection | - |
| `L9_POSTGRES_URL` | Postgres connection | - |
| `L9_NEO4J_URL` | Neo4j connection | - |
| `L9_HYPERGRAPH_URL` | HyperGraphDB connection | - |
| `L9_TENSOR_URL` | TensorAIOS endpoint | - |
| `L9_WORLD_MODEL_URL` | World model endpoint | - |

## Reasoning Configuration

```python
reasoning_config = {
    "modes": ["symbolic", "causal", "analogical", "reflective"],
    "mode_weights": {
        "symbolic": 0.30,
        "causal": 0.25,
        "analogical": 0.20,
        "reflective": 0.25,
    },
    "confidence_threshold": 0.5,
    "escalation_threshold": 0.3,
}
```

## Batch Configuration

```python
tensor_config = {
    "batch_size": 10,
    "timeout_seconds": 30,
    "max_retries": 3,
}
```


