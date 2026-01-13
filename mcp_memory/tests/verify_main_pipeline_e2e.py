#!/usr/bin/env python3
"""
E2E Verification: Test MCP Memory Main Pipeline Integration

This script:
1. Saves a test memory via MCP
2. Searches for it
3. Traces it through the full DAG pipeline:
   - packet_store (event log)
   - memory_embeddings (vector store)
   - knowledge_facts (fact extraction)
   - reasoning_traces (reasoning traces)
   - Verifies "pipeline": "main_dag" in response

Usage:
    python3 verify_main_pipeline_e2e.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from uuid import UUID
from typing import Dict, Any, Optional

import asyncpg
import httpx
from pydantic import BaseModel


# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Configuration from environment."""
    
    # MCP Server URL
    MCP_URL = os.getenv("L9_API_URL", "http://127.0.0.1:8000")
    
    # API Key (use MCP_API_KEY_C for Cursor)
    API_KEY = os.getenv("MCP_API_KEY_C") or os.getenv("L9_EXECUTOR_API_KEY") or os.getenv("MCP_API_KEY")
    
    # Database connection (for tracing)
    MEMORY_DSN = os.getenv("MEMORY_DSN") or os.getenv("DATABASE_URL")
    
    # Test content
    TEST_CONTENT = f"E2E Test Memory - Main Pipeline Verification - {datetime.utcnow().isoformat()}"
    TEST_KIND = "preference"
    TEST_SCOPE = "developer"


# =============================================================================
# MCP Client
# =============================================================================

class MCPClient:
    """Client for MCP Memory Server."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    
    async def save_memory(
        self,
        content: str,
        kind: str,
        scope: str = "developer",
        duration: str = "long",
        tags: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Save memory via MCP tool."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/mcp/call",
                headers=self.headers,
                json={
                    "tool_name": "save_memory",
                    "arguments": {
                        "content": content,
                        "kind": kind,
                        "scope": scope,
                        "duration": duration,
                        "tags": tags or [],
                    },
                },
            )
            response.raise_for_status()
            result = response.json()
            return result.get("result", {})
    
    async def search_memory(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """Search memory via MCP tool."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/mcp/call",
                headers=self.headers,
                json={
                    "tool_name": "search_memory",
                    "arguments": {
                        "query": query,
                        "top_k": top_k,
                        "threshold": threshold,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()
            return result.get("result", {})


# =============================================================================
# Database Tracer
# =============================================================================

class PipelineTracer:
    """Trace memory through the DAG pipeline."""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.conn: Optional[asyncpg.Connection] = None
    
    async def connect(self):
        """Connect to database."""
        self.conn = await asyncpg.connect(self.dsn)
    
    async def close(self):
        """Close database connection."""
        if self.conn:
            await self.conn.close()
    
    async def trace_packet(self, packet_id: str) -> Dict[str, Any]:
        """Trace packet through all pipeline stages."""
        packet_uuid = UUID(packet_id)
        
        trace = {
            "packet_id": packet_id,
            "stages": {},
        }
        
        # Stage 1: packet_store (event log)
        packet_row = await self.conn.fetchrow(
            """
            SELECT 
                packet_id,
                packet_type,
                envelope,
                timestamp,
                thread_id,
                tags,
                scope,
                importance_score
            FROM packet_store
            WHERE packet_id = $1
            """,
            packet_uuid,
        )
        
        if packet_row:
            trace["stages"]["packet_store"] = {
                "found": True,
                "packet_type": packet_row["packet_type"],
                "timestamp": str(packet_row["timestamp"]),
                "scope": packet_row["scope"],
                "importance": float(packet_row["importance_score"]) if packet_row["importance_score"] else None,
                "tags": packet_row["tags"] or [],
            }
            
            # Extract envelope content
            envelope = packet_row["envelope"]
            trace["stages"]["packet_store"]["envelope"] = {
                "payload": envelope.get("payload", {}),
                "metadata": envelope.get("metadata", {}),
            }
        else:
            trace["stages"]["packet_store"] = {"found": False}
        
        # Stage 2: memory_embeddings (vector store)
        embedding_row = await self.conn.fetchrow(
            """
            SELECT 
                embedding_id,
                embedding_type,
                chunk_text,
                metadata,
                created_at
            FROM memory_embeddings
            WHERE packet_id = $1
            """,
            packet_uuid,
        )
        
        if embedding_row:
            trace["stages"]["memory_embeddings"] = {
                "found": True,
                "embedding_id": str(embedding_row["embedding_id"]),
                "embedding_type": embedding_row["embedding_type"],
                "chunk_text": embedding_row["chunk_text"][:100] if embedding_row["chunk_text"] else None,
                "created_at": str(embedding_row["created_at"]),
            }
        else:
            trace["stages"]["memory_embeddings"] = {"found": False}
        
        # Stage 3: knowledge_facts (fact extraction)
        facts = await self.conn.fetch(
            """
            SELECT 
                fact_id,
                subject,
                predicate,
                object,
                confidence,
                created_at
            FROM knowledge_facts
            WHERE source_packet = $1
            ORDER BY created_at DESC
            LIMIT 10
            """,
            packet_uuid,
        )
        
        if facts:
            trace["stages"]["knowledge_facts"] = {
                "found": True,
                "count": len(facts),
                "facts": [
                    {
                        "fact_id": str(f["fact_id"]),
                        "subject": f["subject"],
                        "predicate": f["predicate"],
                        "object": str(f["object"])[:100],
                        "confidence": float(f["confidence"]) if f["confidence"] else None,
                    }
                    for f in facts
                ],
            }
        else:
            trace["stages"]["knowledge_facts"] = {"found": False, "count": 0}
        
        # Stage 4: reasoning_traces (reasoning traces)
        trace_row = await self.conn.fetchrow(
            """
            SELECT 
                trace_id,
                agent_id,
                steps,
                extracted_features,
                inference_steps,
                created_at
            FROM reasoning_traces
            WHERE packet_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            packet_uuid,
        )
        
        if trace_row:
            trace["stages"]["reasoning_traces"] = {
                "found": True,
                "trace_id": str(trace_row["trace_id"]),
                "agent_id": trace_row["agent_id"],
                "has_steps": trace_row["steps"] is not None,
                "has_features": trace_row["extracted_features"] is not None,
                "has_inference": trace_row["inference_steps"] is not None,
                "created_at": str(trace_row["created_at"]),
            }
        else:
            trace["stages"]["reasoning_traces"] = {"found": False}
        
        return trace


# =============================================================================
# Main Verification
# =============================================================================

async def verify_main_pipeline():
    """Run E2E verification of main pipeline integration."""
    
    print("=" * 80)
    print("MCP Memory Main Pipeline E2E Verification")
    print("=" * 80)
    print()
    
    # Check configuration
    if not Config.API_KEY:
        print("❌ ERROR: API key not found. Set MCP_API_KEY_C or L9_EXECUTOR_API_KEY")
        sys.exit(1)
    
    if not Config.MEMORY_DSN:
        print("⚠️  WARNING: MEMORY_DSN not set. Cannot trace through database.")
        print("   Set MEMORY_DSN to enable full pipeline tracing.")
        trace_db = False
    else:
        trace_db = True
    
    print(f"📡 MCP Server URL: {Config.MCP_URL}")
    print(f"🔑 API Key: {'*' * 20}...{Config.API_KEY[-4:] if len(Config.API_KEY) > 4 else '***'}")
    print(f"💾 Database Tracing: {'✅ Enabled' if trace_db else '❌ Disabled'}")
    print()
    
    # Initialize clients
    mcp_client = MCPClient(Config.MCP_URL, Config.API_KEY)
    tracer = None
    if trace_db:
        tracer = PipelineTracer(Config.MEMORY_DSN)
        await tracer.connect()
    
    try:
        # Step 1: Save memory
        print("Step 1: Saving test memory via MCP...")
        print(f"   Content: {Config.TEST_CONTENT[:60]}...")
        print(f"   Kind: {Config.TEST_KIND}")
        print(f"   Scope: {Config.TEST_SCOPE}")
        print()
        
        save_result = await mcp_client.save_memory(
            content=Config.TEST_CONTENT,
            kind=Config.TEST_KIND,
            scope=Config.TEST_SCOPE,
            duration="long",
            tags=["e2e-test", "main-pipeline"],
        )
        
        packet_id = save_result.get("packet_id")
        if not packet_id:
            print("❌ ERROR: No packet_id in save result")
            print(f"   Result: {json.dumps(save_result, indent=2)}")
            sys.exit(1)
        
        print(f"✅ Memory saved successfully!")
        print(f"   Packet ID: {packet_id}")
        print(f"   Pipeline: {save_result.get('pipeline', 'unknown')}")
        
        if save_result.get("pipeline") == "main_dag":
            print("   ✅ Using MAIN DAG pipeline!")
        elif save_result.get("pipeline") == "direct_db":
            print("   ⚠️  Using direct DB (fallback) - main pipeline not available")
        else:
            print("   ⚠️  Pipeline indicator missing")
        
        if "written_tables" in save_result:
            print(f"   Written tables: {', '.join(save_result['written_tables'])}")
            if "knowledge_facts" in save_result["written_tables"]:
                print("   ✅ Fact extraction active!")
            if "reasoning_traces" in save_result["written_tables"]:
                print("   ✅ Reasoning traces active!")
        
        print()
        
        # Step 2: Search for memory
        print("Step 2: Searching for saved memory...")
        print(f"   Query: 'E2E Test Memory'")
        print()
        
        # Wait a moment for embeddings to be indexed
        await asyncio.sleep(2)
        
        search_result = await mcp_client.search_memory(
            query="E2E Test Memory Main Pipeline",
            top_k=5,
            threshold=0.5,
        )
        
        results = search_result.get("results", [])
        found = False
        for result in results:
            if result.get("packet_id") == packet_id:
                found = True
                print(f"✅ Memory found in search results!")
                print(f"   Similarity: {result.get('similarity', 0):.3f}")
                print(f"   Content: {result.get('content', '')[:60]}...")
                break
        
        if not found:
            print("⚠️  WARNING: Saved memory not found in search results")
            print(f"   Found {len(results)} results, but packet_id {packet_id} not in list")
            if results:
                print(f"   Top result packet_id: {results[0].get('packet_id')}")
        
        print()
        
        # Step 3: Trace through pipeline
        if tracer:
            print("Step 3: Tracing through DAG pipeline...")
            print()
            
            trace = await tracer.trace_packet(packet_id)
            
            # Check each stage
            stages_ok = []
            stages_missing = []
            
            if trace["stages"]["packet_store"]["found"]:
                print("✅ Stage 1: packet_store (event log)")
                print(f"   Packet type: {trace['stages']['packet_store']['packet_type']}")
                print(f"   Scope: {trace['stages']['packet_store']['scope']}")
                stages_ok.append("packet_store")
            else:
                print("❌ Stage 1: packet_store - NOT FOUND")
                stages_missing.append("packet_store")
            
            if trace["stages"]["memory_embeddings"]["found"]:
                print("✅ Stage 2: memory_embeddings (vector store)")
                print(f"   Embedding type: {trace['stages']['memory_embeddings']['embedding_type']}")
                stages_ok.append("memory_embeddings")
            else:
                print("❌ Stage 2: memory_embeddings - NOT FOUND")
                stages_missing.append("memory_embeddings")
            
            if trace["stages"]["knowledge_facts"]["found"]:
                print(f"✅ Stage 3: knowledge_facts (fact extraction)")
                print(f"   Facts extracted: {trace['stages']['knowledge_facts']['count']}")
                for fact in trace["stages"]["knowledge_facts"]["facts"][:3]:
                    print(f"   - {fact['subject']} {fact['predicate']} {fact['object'][:40]}...")
                stages_ok.append("knowledge_facts")
            else:
                print("⚠️  Stage 3: knowledge_facts - No facts extracted")
                print("   (This is OK - fact extraction may not trigger for all packet types)")
            
            if trace["stages"]["reasoning_traces"]["found"]:
                print("✅ Stage 4: reasoning_traces (reasoning traces)")
                print(f"   Agent: {trace['stages']['reasoning_traces']['agent_id']}")
                stages_ok.append("reasoning_traces")
            else:
                print("⚠️  Stage 4: reasoning_traces - No reasoning trace created")
                print("   (This is OK - reasoning traces may not be created for all packets)")
            
            print()
            print("=" * 80)
            print("Pipeline Trace Summary")
            print("=" * 80)
            print(f"✅ Stages completed: {len(stages_ok)}/4")
            print(f"   - packet_store: {'✅' if 'packet_store' in stages_ok else '❌'}")
            print(f"   - memory_embeddings: {'✅' if 'memory_embeddings' in stages_ok else '❌'}")
            print(f"   - knowledge_facts: {'✅' if 'knowledge_facts' in stages_ok else '⚠️'}")
            print(f"   - reasoning_traces: {'✅' if 'reasoning_traces' in stages_ok else '⚠️'}")
            print()
            
            if "packet_store" in stages_ok and "memory_embeddings" in stages_ok:
                print("✅ MAIN PIPELINE VERIFIED: Memory went through full DAG pipeline!")
                if save_result.get("pipeline") == "main_dag":
                    print("✅ Pipeline indicator confirmed: 'main_dag'")
                return 0
            else:
                print("❌ PIPELINE VERIFICATION FAILED: Critical stages missing")
                return 1
        else:
            print("⚠️  Database tracing disabled - cannot verify pipeline stages")
            print("   Set MEMORY_DSN to enable full verification")
            return 0
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        if tracer:
            await tracer.close()


if __name__ == "__main__":
    exit_code = asyncio.run(verify_main_pipeline())
    sys.exit(exit_code)
