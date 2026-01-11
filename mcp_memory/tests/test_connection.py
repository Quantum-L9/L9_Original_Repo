#!/usr/bin/env python3
"""Test PostgreSQL and OpenAI connections."""

import asyncio
import os
import sys


async def main():
    print("Testing connections...")

    # Test PostgreSQL
    try:
        import asyncpg

        dsn = os.getenv("MEMORY_DSN", "postgresql://postgres@127.0.0.1:5432/l9_memory")
        conn = await asyncpg.connect(dsn)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        print(f"✓ PostgreSQL: Connected (result={result})")
    except Exception as e:
        print(f"✗ PostgreSQL: {e}")
        sys.exit(1)

    # Test OpenAI
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model="text-embedding-3-small", input="test"
        )
        print(f"✓ OpenAI: Connected (dim={len(response.data[0].embedding)})")
    except Exception as e:
        print(f"✗ OpenAI: {e}")
        sys.exit(1)

    print("\n✅ All connections successful!")


if __name__ == "__main__":
    asyncio.run(main())
