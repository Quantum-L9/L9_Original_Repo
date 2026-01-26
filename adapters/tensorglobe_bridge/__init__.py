"""
TensorGlobe Bridge Adapter

External cognitive accelerator adapter for L9.
Gated by EOS + Accountability. Read-only. Evidence-producing.
"""

from .adapter import TensorGlobeBridgeAdapter
from .schemas import (
    TensorOperation,
    TensorRequest,
    TensorResult,
    TensorResponse,
    TensorRequestPacket,
    TensorResponsePacket,
    AnomalySignal,
)

__all__ = [
    "TensorGlobeBridgeAdapter",
    "TensorOperation",
    "TensorRequest",
    "TensorResult",
    "TensorResponse",
    "TensorRequestPacket",
    "TensorResponsePacket",
    "AnomalySignal",
]
