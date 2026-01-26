"""
TensorGlobe Bridge Adapter

External cognitive accelerator adapter for L9.
Gated by EOS + Accountability. Read-only. Evidence-producing.
"""

from .adapter import TensorGlobeBridgeAdapter
from .schemas import (
    AnomalySignal,
    TensorOperation,
    TensorRequest,
    TensorRequestPacket,
    TensorResponse,
    TensorResponsePacket,
    TensorResult,
)

__all__ = [
    "AnomalySignal",
    "TensorGlobeBridgeAdapter",
    "TensorOperation",
    "TensorRequest",
    "TensorRequestPacket",
    "TensorResponse",
    "TensorResponsePacket",
    "TensorResult",
]
