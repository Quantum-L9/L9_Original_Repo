#!/usr/bin/env python3
"""
L9 Chat Transcript Ingestion Script
====================================

Parses chat transcripts (ChatGPT, Claude, etc.) and ingests them into
the L9 memory substrate (PostgreSQL + pgvector).

Features:
- Parses "You said:" / "ChatGPT said:" / "Human:" / "Assistant:" formats
- Creates conversation records with message sequence
- Chunks messages for embedding (configurable chunk size)
- Stores in packetstore with proper lineage

Usage:
    python scripts/memory/ingest_chat_transcript.py <transcript_path>
    python scripts/memory/ingest_chat_transcript.py --help

Examples:
    python scripts/memory/ingest_chat_transcript.py docs/chat_history.md
    python scripts/memory/ingest_chat_transcript.py --chunk-size 5000 docs/chat.md
    python scripts/memory/ingest_chat_transcript.py --dry-run docs/chat.md
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid5

import structlog

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = structlog.get_logger(__name__)

# UUID namespace for deterministic IDs
CHAT_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@dataclass
class Message:
    """Parsed chat message."""

    seq: int
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime | None = None


@dataclass
class Chunk:
    """Chunk of messages for embedding."""

    chunk_id: str
    conversation_id: str
    start_seq: int
    end_seq: int
    text: str
    message_count: int


def sha256(s: str) -> str:
    """Generate SHA256 hash of string."""
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


def generate_deterministic_id(identifier: str) -> UUID:
    """Generate deterministic UUID from string."""
    return uuid5(CHAT_NAMESPACE, identifier)


# Role marker patterns (order matters - more specific first)
ROLE_PATTERNS = [
    # ChatGPT export format
    (r"^You said:\s*$", "user"),
    (r"^ChatGPT said:\s*$", "assistant"),
    # Claude format
    (r"^Human:\s*$", "user"),
    (r"^Assistant:\s*$", "assistant"),
    # Generic format
    (r"^User:\s*$", "user"),
    (r"^AI:\s*$", "assistant"),
    (r"^System:\s*$", "system"),
]


def parse_transcript(content: str) -> list[Message]:
    """
    Parse chat transcript into messages.

    Supports multiple formats:
    - ChatGPT: "You said:" / "ChatGPT said:"
    - Claude: "Human:" / "Assistant:"
    - Generic: "User:" / "AI:"

    Args:
        content: Raw markdown content

    Returns:
        List of Message objects with seq, role, content
    """
    # Normalize line endings
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Build combined pattern
    pattern_parts = [f"({p[0]})" for p in ROLE_PATTERNS]
    combined_pattern = "|".join(pattern_parts)
    full_pattern = f"({combined_pattern})"

    # Find all marker positions
    matches = list(re.finditer(full_pattern, content, flags=re.MULTILINE))

    if not matches:
        logger.warning("No role markers found in transcript")
        return []

    messages: list[Message] = []

    for i, match in enumerate(matches):
        # Get content between this marker and the next
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        msg_content = content[start:end].strip()

        if not msg_content:
            continue

        # Determine role from matched pattern
        marker_text = match.group(0).strip()
        role = "unknown"

        for pattern, role_name in ROLE_PATTERNS:
            if re.match(pattern, marker_text, flags=re.MULTILINE):
                role = role_name
                break

        messages.append(
            Message(
                seq=len(messages) + 1,
                role=role,
                content=msg_content,
            )
        )

    logger.info(f"Parsed {len(messages)} messages from transcript")
    return messages


def chunk_messages(
    messages: list[Message],
    max_chars: int = 8000,
    overlap_messages: int = 1,
) -> list[Chunk]:
    """
    Chunk messages for embedding.

    Args:
        messages: List of parsed messages
        max_chars: Maximum characters per chunk
        overlap_messages: Number of messages to overlap between chunks

    Returns:
        List of Chunk objects
    """
    if not messages:
        return []

    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_len = 0
    start_seq = 1

    def format_message(m: Message) -> str:
        return f"#SEQ:{m.seq}\nROLE:{m.role}\n{m.content}"

    def flush_buffer():
        nonlocal buffer, buffer_len, start_seq
        if not buffer:
            return

        chunk_text = "\n\n".join(buffer).strip()

        # Extract end_seq from last message
        last_entry = buffer[-1]
        end_seq_match = re.search(r"^#SEQ:(\d+)", last_entry)
        end_seq = int(end_seq_match.group(1)) if end_seq_match else start_seq

        chunk_id = f"chunk_{sha256(chunk_text)[:16]}_{start_seq}_{end_seq}"

        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                conversation_id="",  # Set later
                start_seq=start_seq,
                end_seq=end_seq,
                text=chunk_text,
                message_count=len(buffer),
            )
        )

        # Keep overlap messages for context
        if overlap_messages > 0 and len(buffer) > overlap_messages:
            buffer = buffer[-overlap_messages:]
            buffer_len = sum(len(b) for b in buffer)
            start_seq = end_seq - overlap_messages + 1
        else:
            buffer = []
            buffer_len = 0
            start_seq = end_seq + 1

    for msg in messages:
        entry = format_message(msg)

        if buffer_len + len(entry) > max_chars and buffer:
            flush_buffer()

        if not buffer:
            start_seq = msg.seq

        buffer.append(entry)
        buffer_len += len(entry)

    # Flush remaining
    flush_buffer()

    logger.info(f"Created {len(chunks)} chunks from {len(messages)} messages")
    return chunks


async def ingest_to_memory(
    transcript_path: str,
    messages: list[Message],
    chunks: list[Chunk],
    dry_run: bool = False,
) -> tuple[str, int, int]:
    """
    Ingest transcript into L9 memory substrate.

    Args:
        transcript_path: Path to source file
        messages: Parsed messages
        chunks: Chunked messages
        dry_run: If True, don't actually write to database

    Returns:
        Tuple of (conversation_id, message_count, chunk_count)
    """
    from config.rls_config import get_rls_config
    from memory.substrate_repository import SubstrateRepository

    title = Path(transcript_path).name
    conversation_id = f"conv_{sha256(title)[:16]}"

    # Update chunk conversation_ids
    for chunk in chunks:
        chunk.conversation_id = conversation_id

    if dry_run:
        logger.info(
            "DRY RUN - would ingest",
            conversation_id=conversation_id,
            messages=len(messages),
            chunks=len(chunks),
        )
        return conversation_id, len(messages), len(chunks)

    # Get repository
    database_url = os.environ.get(
        "DATABASE_URL",
        os.environ.get(
            "PG_DSN", "postgresql://l9_user:password@localhost:5432/l9_memory"
        ),
    )

    repo = SubstrateRepository(database_url)
    await repo.initialize()

    rls_config = get_rls_config()

    try:
        async with repo.acquire() as conn:
            # Insert conversation metadata as a packet
            conv_packet_id = generate_deterministic_id(f"{conversation_id}_metadata")

            await conn.execute(
                """
                INSERT INTO packet_store (
                    packet_id, packet_type, envelope, timestamp,
                    scope, tenant_id, org_id, user_id, tags
                )
                VALUES ($1, $2, $3, $4, $5, $6::uuid, $7::uuid, $8::uuid, $9)
                ON CONFLICT (packet_id) DO UPDATE SET
                    envelope = EXCLUDED.envelope,
                    timestamp = EXCLUDED.timestamp
                """,
                conv_packet_id,
                "chat_conversation",
                {
                    "conversation_id": conversation_id,
                    "title": title,
                    "source": transcript_path,
                    "message_count": len(messages),
                    "chunk_count": len(chunks),
                    "parser": "ingest_chat_transcript.py",
                },
                datetime.now(timezone.utc),
                "shared",
                rls_config.tenant_uuid,
                rls_config.org_uuid,
                rls_config.user_uuid,
                ["chat_transcript", "conversation"],
            )

            # Insert messages as packets
            parent_id = conv_packet_id
            for msg in messages:
                msg_packet_id = generate_deterministic_id(
                    f"{conversation_id}_msg_{msg.seq}"
                )

                await conn.execute(
                    """
                    INSERT INTO packet_store (
                        packet_id, packet_type, envelope, timestamp,
                        parent_ids, scope, tenant_id, org_id, user_id, tags
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7::uuid, $8::uuid, $9::uuid, $10)
                    ON CONFLICT (packet_id) DO UPDATE SET
                        envelope = EXCLUDED.envelope,
                        timestamp = EXCLUDED.timestamp
                    """,
                    msg_packet_id,
                    "chat_message",
                    {
                        "conversation_id": conversation_id,
                        "seq": msg.seq,
                        "role": msg.role,
                        "content": msg.content,
                        "content_sha256": sha256(msg.content),
                    },
                    datetime.now(timezone.utc),
                    [parent_id],  # Link to conversation
                    "shared",
                    rls_config.tenant_uuid,
                    rls_config.org_uuid,
                    rls_config.user_uuid,
                    ["chat_message", msg.role],
                )

            # Insert chunks as packets (for embedding)
            for chunk in chunks:
                chunk_packet_id = generate_deterministic_id(
                    f"{conversation_id}_chunk_{chunk.start_seq}_{chunk.end_seq}"
                )

                await conn.execute(
                    """
                    INSERT INTO packet_store (
                        packet_id, packet_type, envelope, timestamp,
                        scope, tenant_id, org_id, user_id, tags
                    )
                    VALUES ($1, $2, $3, $4, $5, $6::uuid, $7::uuid, $8::uuid, $9)
                    ON CONFLICT (packet_id) DO UPDATE SET
                        envelope = EXCLUDED.envelope,
                        timestamp = EXCLUDED.timestamp
                    """,
                    chunk_packet_id,
                    "chat_chunk",
                    {
                        "conversation_id": conversation_id,
                        "chunk_id": chunk.chunk_id,
                        "start_seq": chunk.start_seq,
                        "end_seq": chunk.end_seq,
                        "message_count": chunk.message_count,
                        "chunk_text": chunk.text,
                        "source_file": transcript_path,
                    },
                    datetime.now(timezone.utc),
                    "shared",
                    rls_config.tenant_uuid,
                    rls_config.org_uuid,
                    rls_config.user_uuid,
                    ["chat_chunk", "for_embedding"],
                )

        logger.info(
            "Ingestion complete",
            conversation_id=conversation_id,
            messages=len(messages),
            chunks=len(chunks),
        )

    finally:
        await repo.close()

    return conversation_id, len(messages), len(chunks)


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Ingest chat transcripts into L9 memory substrate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "transcript_path",
        help="Path to chat transcript file (markdown)",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=8000,
        help="Maximum characters per chunk (default: 8000)",
    )

    parser.add_argument(
        "--overlap",
        type=int,
        default=1,
        help="Number of messages to overlap between chunks (default: 1)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse only, don't write to database",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = "DEBUG" if args.verbose else "INFO"
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog, log_level)
        ),
    )

    # Validate file exists
    transcript_path = Path(args.transcript_path)
    if not transcript_path.exists():
        logger.error(f"File not found: {transcript_path}")
        sys.exit(1)

    # Read and parse
    content = transcript_path.read_text(encoding="utf-8", errors="ignore")
    messages = parse_transcript(content)

    if not messages:
        logger.error("No messages parsed from transcript")
        sys.exit(1)

    # Chunk
    chunks = chunk_messages(
        messages,
        max_chars=args.chunk_size,
        overlap_messages=args.overlap,
    )

    # Ingest
    conversation_id, msg_count, chunk_count = asyncio.run(
        ingest_to_memory(
            str(transcript_path),
            messages,
            chunks,
            dry_run=args.dry_run,
        )
    )

    # Summary
    print(f"\n{'DRY RUN: ' if args.dry_run else ''}Ingestion Summary")
    print(f"{'=' * 40}")
    print(f"Conversation ID: {conversation_id}")
    print(f"Messages:        {msg_count}")
    print(f"Chunks:          {chunk_count}")
    print(f"Source:          {transcript_path}")


if __name__ == "__main__":
    main()
