"""
L9 OCR Engine
=============

Optical Character Recognition using Tesseract OCR.

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Ocr Engine",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-14T12:48:58Z",
    "updated_at": "2026-01-07T13:35:58Z",
    "layer": "operations",
    "domain": "services",
    "module_name": "ocr_engine",
    "type": "engine",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["services.slack_files"],
    },
}
# ============================================================================

import structlog
from typing import Dict, Any
from pathlib import Path

logger = structlog.get_logger(__name__)

try:
    from PIL import Image
    import pytesseract

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract/Pillow not installed. OCR disabled.")


def ocr_image(path: str) -> Dict[str, Any]:
    """
    Extract text from image using OCR.

    Args:
        path: Path to image file (PNG, JPG, etc.)

    Returns:
        {
            "text": <extracted text>,
            "tokens": <list of words>,
            "confidence": <average confidence score>,
            "engine": "tesseract"
        }
    """
    if not OCR_AVAILABLE:
        return {
            "text": "",
            "tokens": [],
            "confidence": 0.0,
            "engine": "tesseract",
            "error": "OCR not available - install pytesseract and Pillow",
        }

    try:
        # Load image
        image = Image.open(path)

        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Perform OCR with detailed data
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Extract text
        text = pytesseract.image_to_string(image)

        # Extract tokens and confidence scores
        tokens = []
        confidences = []

        for i, word in enumerate(ocr_data.get("text", [])):
            if word.strip():
                conf = ocr_data.get("conf", [])[i]
                if conf != "-1":  # -1 means no confidence data
                    try:
                        confidences.append(float(conf))
                    except (ValueError, TypeError):
                        pass
                tokens.append(word.strip())

        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        logger.info(
            f"OCR extracted {len(tokens)} tokens from {path} (confidence: {avg_confidence:.1f}%)"
        )

        return {
            "text": text.strip(),
            "tokens": tokens,
            "confidence": avg_confidence,
            "engine": "tesseract",
        }

    except Exception as e:
        logger.error(f"OCR failed for {path}: {e}", exc_info=True)
        return {
            "text": "",
            "tokens": [],
            "confidence": 0.0,
            "engine": "tesseract",
            "error": str(e),
        }


def ocr_pdf_first_page(path: str) -> Dict[str, Any]:
    """
    Extract text from first page of PDF using screenshot fallback.

    Args:
        path: Path to PDF file

    Returns:
        OCR result dict
    """
    if not OCR_AVAILABLE:
        return {
            "text": "",
            "tokens": [],
            "confidence": 0.0,
            "engine": "tesseract",
            "error": "OCR not available",
        }

    try:
        # Try to convert first page to image
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(path, first_page=1, last_page=1)
            if images:
                # Save temporary image
                temp_image = Path(path).parent / f"{Path(path).stem}_page1.png"
                images[0].save(str(temp_image))

                # OCR the image
                result = ocr_image(str(temp_image))

                # Clean up temp file
                try:
                    temp_image.unlink()
                except Exception:
                    pass

                return result
        except ImportError:
            logger.warning("pdf2image not installed. PDF OCR fallback disabled.")
        except Exception as e:
            logger.warning(f"PDF to image conversion failed: {e}")

        # Fallback: return empty result
        return {
            "text": "",
            "tokens": [],
            "confidence": 0.0,
            "engine": "tesseract",
            "error": "PDF conversion failed",
        }

    except Exception as e:
        logger.error(f"PDF OCR failed for {path}: {e}", exc_info=True)
        return {
            "text": "",
            "tokens": [],
            "confidence": 0.0,
            "engine": "tesseract",
            "error": str(e),
        }


# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "SER-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["engine", "filesystem", "logging", "operations", "services"],
    "keywords": ["engine", "first", "image", "ocr", "page", "pdf"],
    "business_value": "Utility module for ocr engine",
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
