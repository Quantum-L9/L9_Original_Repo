"""
Runtime Governance Layer: Enforce law at execution time.

Provides:
- Enforcement engine: Apply rules to operations
- CA router: Route coding agent requests through gates
- Escalation: Bubble up to L when needed
"""



from dev_layer.runtime import enforcement

__all__ = ["enforcement"]
