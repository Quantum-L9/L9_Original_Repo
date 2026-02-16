#!/usr/bin/env python3
"""
Semantic Code Index Builder for L9

Extracts functions/classes from Python code and builds FAISS semantic search index
using OpenAI embeddings.

Usage:
    export OPENAI_API_KEY=your_key
    python tools/code_index/build_semantic_index.py
    python tools/code_index/build_semantic_index.py --rebuild
    python tools/code_index/build_semantic_index.py --help

Part of GMP Phase 2 - Enhancement 2
"""

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import faiss
import numpy as np
import structlog
from openai import OpenAI

logger = structlog.get_logger()


@dataclass
class CodeSymbol:
    """Represents a function or class in the codebase."""

    name: str
    type: Literal["function", "class", "method"]
    file_path: str
    line_number: int
    signature: str
    docstring: str
    body_preview: str
    adr_tags: list[str]
    test_coverage: bool


class CodeExtractor(ast.NodeVisitor):
    """AST visitor to extract functions and classes."""

    def __init__(self, file_path: Path, repo_root: Path):
        self.file_path = file_path
        self.repo_root = repo_root
        self.symbols: list[CodeSymbol] = []
        self.current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class definition."""
        docstring = ast.get_docstring(node) or ""

        # Check for ADR tags in docstring
        adr_tags = self._extract_adr_tags(docstring)

        # Check test coverage
        test_coverage = self._has_test_coverage(node.name)

        symbol = CodeSymbol(
            name=node.name,
            type="class",
            file_path=str(self.file_path.relative_to(self.repo_root)),
            line_number=node.lineno,
            signature=f"class {node.name}",
            docstring=docstring,
            body_preview=self._get_body_preview(node),
            adr_tags=adr_tags,
            test_coverage=test_coverage,
        )
        self.symbols.append(symbol)

        # Visit methods
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Extract function/method definition."""
        docstring = ast.get_docstring(node) or ""
        adr_tags = self._extract_adr_tags(docstring)
        test_coverage = self._has_test_coverage(node.name)

        # Build signature
        args = ", ".join(arg.arg for arg in node.args.args)
        returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        signature = f"def {node.name}({args}){returns}"

        symbol_type = "method" if self.current_class else "function"

        symbol = CodeSymbol(
            name=node.name,
            type=symbol_type,
            file_path=str(self.file_path.relative_to(self.repo_root)),
            line_number=node.lineno,
            signature=signature,
            docstring=docstring,
            body_preview=self._get_body_preview(node),
            adr_tags=adr_tags,
            test_coverage=test_coverage,
        )
        self.symbols.append(symbol)

        self.generic_visit(node)

    def _extract_adr_tags(self, docstring: str) -> list[str]:
        """Extract ADR references from docstring."""
        tags = []
        for line in docstring.splitlines():
            if "ADR-" in line.upper():
                # Extract ADR-XXXX pattern
                import re

                matches = re.findall(r"ADR-\d{4}", line.upper())
                tags.extend(matches)
        return list(set(tags))

    def _has_test_coverage(self, name: str) -> bool:
        """Check if tests exist for this symbol."""
        test_file = self.repo_root / "tests" / f"test_{self.file_path.stem}.py"
        if not test_file.exists():
            return False

        try:
            test_content = test_file.read_text()
            return f"test_{name}" in test_content or f'"{name}"' in test_content
        except Exception:
            return False

    def _get_body_preview(self, node: ast.AST) -> str:
        """Get first 5 lines of function/class body."""
        try:
            source_lines = ast.get_source_segment(self.file_path.read_text(), node)
            if source_lines:
                lines = source_lines.splitlines()[:5]
                return "\n".join(lines)
        except Exception:
            logger.debug("build_semantic_index.body_preview_failed")
        return ""


def extract_symbols_from_file(file_path: Path, repo_root: Path) -> list[CodeSymbol]:
    """Parse Python file and extract code symbols.

    Args:
        file_path: Path to Python file
        repo_root: Repository root directory

    Returns:
        List of extracted code symbols
    """
    try:
        content = file_path.read_text()
        tree = ast.parse(content, filename=str(file_path))

        extractor = CodeExtractor(file_path, repo_root)
        extractor.visit(tree)

        return extractor.symbols

    except SyntaxError as e:
        logger.warning("syntax_error", file=str(file_path), error=str(e))
        return []
    except Exception as e:
        logger.error("extraction_failed", file=str(file_path), error=str(e))
        return []


def generate_embedding(text: str, client: OpenAI) -> np.ndarray:
    """Generate embedding for text using OpenAI API.

    Args:
        text: Input text
        client: OpenAI client

    Returns:
        1536-dimensional embedding vector
    """
    try:
        response = client.embeddings.create(model="text-embedding-3-small", input=text)
        return np.array(response.data[0].embedding, dtype=np.float32)

    except Exception as e:
        logger.error("embedding_failed", error=str(e))
        # Return zero vector on failure
        return np.zeros(1536, dtype=np.float32)


def build_faiss_index(
    symbols: list[CodeSymbol], client: OpenAI
) -> tuple[faiss.Index, list[CodeSymbol]]:
    """Build FAISS index from code symbols.

    Args:
        symbols: List of code symbols
        client: OpenAI client

    Returns:
        Tuple of (FAISS index, symbol metadata)
    """
    logger.info("generating_embeddings", count=len(symbols))

    # Generate embeddings
    embeddings = []
    valid_symbols = []

    for i, symbol in enumerate(symbols):
        if i % 100 == 0:
            logger.info("embedding_progress", current=i, total=len(symbols))

        # Create rich text for embedding
        text = (
            f"{symbol.name} {symbol.signature} {symbol.docstring} {symbol.body_preview}"
        )
        embedding = generate_embedding(text, client)

        if not np.all(embedding == 0):
            embeddings.append(embedding)
            valid_symbols.append(symbol)

    logger.info("embeddings_generated", count=len(embeddings))

    # Build FAISS index
    dimension = 1536
    embeddings_matrix = np.array(embeddings, dtype=np.float32)

    # Normalize for cosine similarity (using inner product)
    faiss.normalize_L2(embeddings_matrix)

    # Create index
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_matrix)

    logger.info("index_built", vectors=index.ntotal)

    return index, valid_symbols


def save_index(
    index: faiss.Index, metadata: list[CodeSymbol], output_dir: Path
) -> None:
    """Save FAISS index and metadata to disk.

    Args:
        index: FAISS index
        metadata: List of code symbols
        output_dir: Output directory
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save FAISS index
    index_path = output_dir / "embeddings.faiss"
    faiss.write_index(index, str(index_path))
    logger.info("index_saved", path=str(index_path))

    # Save metadata
    metadata_path = output_dir / "symbol_metadata.json"
    metadata_dict = {
        "symbols": [asdict(s) for s in metadata],
        "total_symbols": len(metadata),
        "dimensions": index.d,
    }
    metadata_path.write_text(json.dumps(metadata_dict, indent=2))
    logger.info("metadata_saved", path=str(metadata_path))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build semantic search index for L9 codebase"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path("."), help="Repository root directory"
    )
    parser.add_argument(
        "--rebuild", action="store_true", help="Rebuild index even if it exists"
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output_dir = repo_root / "reports" / "code_index"

    # Check if index exists
    if not args.rebuild and (output_dir / "embeddings.faiss").exists():
        logger.info("index_exists", path=str(output_dir))
        print(f"✅ Index already exists at {output_dir}")
        print("   Use --rebuild to regenerate")
        return 0

    # Initialize OpenAI client
    try:
        client = OpenAI()  # Reads OPENAI_API_KEY from env
    except Exception as e:
        logger.error("openai_init_failed", error=str(e))
        print(f"❌ Failed to initialize OpenAI client: {e}")
        print("   Set OPENAI_API_KEY environment variable")
        return 1

    # Extract symbols from all Python files
    logger.info("extracting_symbols", repo=str(repo_root))
    all_symbols = []

    for py_file in repo_root.rglob("*.py"):
        # Skip tests and cache
        if any(
            part.startswith(("test_", "tests", "__pycache__", "."))
            for part in py_file.parts
        ):
            continue

        symbols = extract_symbols_from_file(py_file, repo_root)
        all_symbols.extend(symbols)

    logger.info("symbols_extracted", count=len(all_symbols))

    # Build index
    index, valid_symbols = build_faiss_index(all_symbols, client)

    # Save
    save_index(index, valid_symbols, output_dir)

    # Print summary
    cost_estimate = (
        len(valid_symbols) * 0.00003
    )  # $0.03 per 1M tokens, ~1 token per symbol
    print("\n✅ Semantic Code Index Built")
    print(f"   Symbols indexed: {len(valid_symbols)}")
    print(f"   Index: {output_dir / 'embeddings.faiss'}")
    print(f"   Metadata: {output_dir / 'symbol_metadata.json'}")
    print(f"   Estimated cost: ${cost_estimate:.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
