"""
L9 PDF Engine
=============

PDF parsing and extraction using pypdf/pdfplumber.

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Pdf Engine",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "services",
    "module_name": "pdf_engine",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": ["OpenAI API"],
        "memory_layers": [],
        "imported_by": ["services.slack_files"],
    },
}
# ============================================================================

import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Try pdfplumber first (better for forms), fallback to pypdf
try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

if not PDFPLUMBER_AVAILABLE and not PYPDF_AVAILABLE:
    logger.warning("Neither pdfplumber nor pypdf installed. PDF extraction disabled.")


def extract_pdf(path: str, summarize: bool = True) -> dict[str, Any]:
    """
    Extract text and metadata from PDF.

    Args:
        path: Path to PDF file
        summarize: Whether to generate LLM summary

    Returns:
        {
            "text": <full text>,
            "pages": [<page texts>],
            "summary": <LLM summarized>,
            "fields": {...}  # if form fields detected
        }
    """
    if not PDFPLUMBER_AVAILABLE and not PYPDF_AVAILABLE:
        return {
            "text": "",
            "pages": [],
            "summary": "",
            "error": "PDF libraries not available - install pdfplumber or pypdf",
        }

    try:
        full_text = ""
        pages = []
        fields = {}

        # Try pdfplumber first (better for forms)
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(path) as pdf:
                    for _i, page in enumerate(pdf.pages):
                        page_text = page.extract_text() or ""
                        pages.append(page_text)
                        full_text += page_text + "\n"

                    # Check for form fields
                    if pdf.metadata:
                        # Try to extract form fields
                        try:
                            for page in pdf.pages:
                                form_fields = page.extract_tables()
                                if form_fields:
                                    # Extract form-like structures
                                    for table in form_fields:
                                        if len(table) > 0 and len(table[0]) == 2:
                                            # Looks like key-value pairs
                                            for row in table:
                                                if len(row) >= 2:
                                                    key = (
                                                        str(row[0]).strip()
                                                        if row[0]
                                                        else ""
                                                    )
                                                    value = (
                                                        str(row[1]).strip()
                                                        if row[1]
                                                        else ""
                                                    )
                                                    if key and value:
                                                        fields[key] = value
                        except Exception:
                            logger.debug("pdf_engine.table_extraction_failed")
            except Exception as e:
                logger.warning(f"pdfplumber extraction failed: {e}, trying pypdf")
                PDFPLUMBER_AVAILABLE = False  # Force fallback

        # Fallback to pypdf
        if not PDFPLUMBER_AVAILABLE and PYPDF_AVAILABLE:
            reader = PdfReader(path)
            for _i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                pages.append(page_text)
                full_text += page_text + "\n"

        # Generate summary using LLM if requested
        summary = ""
        if summarize and full_text.strip():
            try:
                from openai import OpenAI

                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                # Truncate if too long
                text_for_summary = full_text[:8000]  # Limit to avoid token limits

                response = client.chat.completions.create(
                    model=os.getenv("L9_LLM_MODEL", "gpt-4o-mini"),
                    messages=[
                        {
                            "role": "system",
                            "content": "Summarize this PDF content in 2-3 sentences.",
                        },
                        {"role": "user", "content": text_for_summary},
                    ],
                    temperature=0.3,
                    max_tokens=200,
                )

                summary = response.choices[0].message.content.strip()
                logger.info(f"Generated PDF summary for {path}")
            except Exception as e:
                logger.warning(f"Failed to generate PDF summary: {e}")

        result = {"text": full_text.strip(), "pages": pages, "summary": summary}

        if fields:
            result["fields"] = fields

        logger.info(f"Extracted {len(pages)} pages from PDF {path}")
        return result

    except Exception as e:
        logger.error(f"PDF extraction failed for {path}: {e}", exc_info=True)
        return {"text": "", "pages": [], "summary": "", "error": str(e)}


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "engine", "llm", "logging", "messaging", "operations", "services"],
    "keywords": ["engine", "extract", "pdf"],
    "business_value": "Utility module for pdf engine",
    "last_modified": "2026-01-07T13:35:58Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
