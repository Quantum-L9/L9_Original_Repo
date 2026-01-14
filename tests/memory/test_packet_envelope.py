import pytest

pytest.skip("Legacy memory substrate system — skipping.", allow_module_level=True)

"""
L9 Tests - PacketEnvelope Focused Tests
Version: 1.0.0
"""


import pytest

from core.schemas import PacketEnvelope, PacketEnvelopeIn
from memory.packet_serializer import (
    envelope_to_dict,
    envelope_from_dict,
    envelope_to_json,
    envelope_from_json,
)


class TestPacketEnvelopeRoundtrip:
    def test_envelope_serialization_roundtrip(self):
        envelope = PacketEnvelope(
            packet_type="event",
            payload={"foo": "bar"},
        )

        as_dict = envelope_to_dict(envelope)
        restored = envelope_from_dict(as_dict)
        assert restored.packet_type == envelope.packet_type
        assert restored.payload == envelope.payload

        as_json = envelope_to_json(envelope)
        restored2 = envelope_from_json(as_json)
        assert restored2.packet_type == envelope.packet_type
        assert restored2.payload == envelope.payload

    def test_packet_in_to_envelope(self):
        packet_in = PacketEnvelopeIn(
            packet_type="event",
            payload={"x": 1},
        )
        envelope = packet_in.to_envelope()
        assert envelope.packet_type == "event"
        assert envelope.payload["x"] == 1
        assert envelope.packet_id is not None
        assert envelope.timestamp is not None
