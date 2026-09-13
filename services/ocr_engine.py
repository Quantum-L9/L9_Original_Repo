"""
L9 OCR Engine
=============

Optical Character Recognition using Tesseract OCR.

Version: 1.0.0
"""


import contextlib
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

try:
    import pytesseract
    from PIL import Image

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("pytesseract/Pillow not installed. OCR disabled.")


def ocr_image(path: str) -> dict[str, Any]:
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
                    with contextlib.suppress(ValueError, TypeError):
                        confidences.append(float(conf))
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


def ocr_pdf_first_page(path: str) -> dict[str, Any]:
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
                with contextlib.suppress(Exception):
                    temp_image.unlink()

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


# Runtime execution trace - updated automatically on every execution
