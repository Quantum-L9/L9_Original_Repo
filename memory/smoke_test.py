"""
L9 Memory - Smoke Test
Version: 1.0.0

Minimal smoke test to verify memory system is operational.
Run this after server startup to verify:
- Migrations applied
- Memory service initialized
- Packet ingestion works
- Data appears in store
"""

import asyncio
import structlog
import os
import sys
from uuid import uuid4

from memory.substrate_service import get_service
from core.schemas import PacketEnvelopeIn
from memory.ingestion import ingest_packet


logger = structlog.get_logger(__name__)


async def smoke_test() -> dict[str, any]:
    """
    Run smoke test to verify memory system.

    Returns:
        Dict with test results
    """
    results = {
        "status": "unknown",
        "tests": {},
        "errors": [],
    }

    # Test 1: Service initialization
    try:
        database_url = os.getenv("MEMORY_DSN") or os.getenv("DATABASE_URL")
        if not database_url:
            results["errors"].append("MEMORY_DSN/DATABASE_URL not set")
            results["status"] = "failed"
            return results

        service = await get_service()
        results["tests"]["service_initialized"] = True
    except RuntimeError as e:
        results["errors"].append(f"Service not initialized: {e}")
        results["tests"]["service_initialized"] = False
        results["status"] = "failed"
        return results
    except Exception as e:
        results["errors"].append(f"Service check failed: {e}")
        results["tests"]["service_initialized"] = False
        results["status"] = "failed"
        return results

    # Test 2: Health check
    try:
        health = await service.health_check()
        results["tests"]["health_check"] = health.get("status") == "ok"
        if not results["tests"]["health_check"]:
            results["errors"].append(f"Health check failed: {health}")
    except Exception as e:
        results["errors"].append(f"Health check error: {e}")
        results["tests"]["health_check"] = False

    # Test 3: Packet ingestion
    try:
        test_packet = PacketEnvelopeIn(
            packet_type="smoke_test",
            payload={
                "test_id": str(uuid4()),
                "message": "Smoke test packet",
            },
            metadata={"agent": "smoke_test", "test": True},
        )

        result = await ingest_packet(test_packet)
        results["tests"]["packet_ingestion"] = result.status == "ok"
        results["tests"]["packet_id"] = str(result.packet_id)
        results["tests"]["written_tables"] = result.written_tables

        if result.status != "ok":
            results["errors"].append(f"Ingestion failed: {result.error_message}")
    except Exception as e:
        results["errors"].append(f"Packet ingestion error: {e}")
        results["tests"]["packet_ingestion"] = False

    # Test 4: Verify packet in store
    try:
        if results["tests"].get("packet_ingestion"):
            packet_id = results["tests"]["packet_id"]
            packet = await service.get_packet(packet_id)
            results["tests"]["packet_retrieval"] = packet is not None
            if not packet:
                results["errors"].append(f"Packet {packet_id} not found in store")
        else:
            results["tests"]["packet_retrieval"] = False
            results["errors"].append("Skipping retrieval test (ingestion failed)")
    except Exception as e:
        results["errors"].append(f"Packet retrieval error: {e}")
        results["tests"]["packet_retrieval"] = False

    # Determine overall status
    all_passed = all(results["tests"].values())
    results["status"] = "passed" if all_passed else "failed"

    return results


async def main():
    """Main entrypoint for smoke test."""
    results = await smoke_test()

    logger.info("\n" + "=" * 60)
    logger.info("L9 MEMORY SMOKE TEST")
    logger.info("=" * 60)
    logger.info(f"\nStatus: {results['status'].upper()}")
    logger.info("\nTest Results:")
    for test_name, passed in results["tests"].items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {status}: {test_name}")

    if results["errors"]:
        logger.error("\nErrors:")
        for error in results["errors"]:
            logger.error(f"  - {error}")

    logger.info("\n" + "=" * 60)

    # Exit with error code if tests failed
    sys.exit(0 if results["status"] == "passed" else 1)


if __name__ == "__main__":
    asyncio.run(main())





