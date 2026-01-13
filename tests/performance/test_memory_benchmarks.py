import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from memory.audit_utils import prepare_packet_for_ingest
from memory.substrate_models import PacketEnvelopeIn


@pytest.mark.benchmark
def test_benchmark_prepare_packet_for_ingest(benchmark):
    packet = PacketEnvelopeIn(
        packet_type="event",
        payload={"text": "Benchmark payload with foo@example.com and more text."},
    )

    benchmark(lambda: prepare_packet_for_ingest(packet))
