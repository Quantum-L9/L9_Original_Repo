#!/usr/bin/env python3
"""
Quick test script for Quantum Research Factory endpoint.

Usage:
    # With server running:
    python scripts/test_research_factory.py

    # Or with specific URL:
    L9_BASE_URL=http://localhost:8000 python scripts/test_research_factory.py
"""

import asyncio
import os
import httpx

BASE_URL = os.getenv("L9_BASE_URL", "http://localhost:8000")


async def test_research_endpoint():
    """Test the /research endpoint."""
    print(f"\n🔬 Testing Quantum Research Factory at {BASE_URL}/research\n")

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Test 1: Check server status
        print("1️⃣  Checking server status...")
        try:
            response = await client.get(f"{BASE_URL}/")
            data = response.json()
            print(f"   ✅ Server: {data.get('status')}")
            print(f"   ✅ Version: {data.get('version')}")
            features = data.get("features", {})
            print(
                f"   ✅ Research Factory enabled: {features.get('quantum_research', False)}"
            )
        except Exception as e:
            print(f"   ❌ Failed to connect: {e}")
            return

        # Test 2: Execute research query
        print("\n2️⃣  Executing research query...")
        try:
            response = await client.post(
                f"{BASE_URL}/research",
                json={
                    "query": "What are the key components of an AI operating system?",
                    "user_id": "test_user",
                },
            )

            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Thread ID: {result.get('thread_id')}")
                print(f"   ✅ Refined Goal: {result.get('refined_goal', '')[:80]}...")
                print(f"   ✅ Evidence Count: {result.get('evidence_count', 0)}")
                print(f"   ✅ Quality Score: {result.get('quality_score', 0.0):.2f}")
                print("\n   📝 Summary (first 500 chars):")
                summary = result.get("summary", "No summary")
                print(f"   {summary[:500]}...")
            elif response.status_code == 503:
                print("   ⚠️  Research service not initialized (503)")
                print("   → Check: MEMORY_DSN environment variable set?")
                print("   → Check: Database running?")
            else:
                print(f"   ❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"   ❌ Request failed: {e}")

        # Test 3: Check if Perplexity is configured
        print("\n3️⃣  Checking Perplexity API key...")
        perplexity_key = os.getenv("PERPLEXITY_API_KEY")
        if perplexity_key:
            print(f"   ✅ PERPLEXITY_API_KEY is set (length: {len(perplexity_key)})")
        else:
            print("   ⚠️  PERPLEXITY_API_KEY not set - research will use mock results")
            print("   → Set: export PERPLEXITY_API_KEY='pplx-...'")


async def main():
    print("=" * 60)
    print("   QUANTUM RESEARCH FACTORY - ACTIVATION TEST")
    print("=" * 60)

    await test_research_endpoint()

    print("\n" + "=" * 60)
    print("   TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
