"""OCR engine for extracting Indian stock tickers and quantities from portfolio screenshots."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

ERROR_LOG_PATH = Path(__file__).resolve().parent / "error_log.txt"


logging.basicConfig(
    filename=ERROR_LOG_PATH,
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


class OCRError(Exception):
    """Base exception for OCR-related failures."""


class ImageNotFoundError(OCRError):
    """Raised when the target image does not exist."""


class LowConfidenceScoreError(OCRError):
    """Raised when OCR confidence is below required threshold."""


@dataclass
class Holding:
    """Represents a parsed portfolio holding.

    Attributes:
        ticker: NSE/BSE-style ticker symbol, uppercase.
        quantity: Parsed quantity of shares.
        confidence: OCR confidence score for the matched text segment.
    """

    ticker: str
    quantity: int
    confidence: float


TICKER_QTY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9&\-]{1,14})\b\s*(?:x|qty|quantity|shares|:)?\s*(\d{1,7})\b", re.IGNORECASE)


def extract_holdings_from_text(text: str, confidence: float) -> List[Holding]:
    """Extract ticker/quantity pairs from OCR text.

    Args:
        text: OCR text block.
        confidence: Confidence score for this OCR text block.

    Returns:
        List of parsed Holding objects.
    """
    holdings: List[Holding] = []
    for match in TICKER_QTY_PATTERN.finditer(text.upper()):
        ticker, qty = match.groups()
        holdings.append(Holding(ticker=ticker, quantity=int(qty), confidence=confidence))
    return holdings


def run_ocr(image_path: str, min_confidence: float = 0.60) -> List[Holding]:
    """Run OCR on a portfolio screenshot and extract holdings.

    Args:
        image_path: Path to the screenshot image.
        min_confidence: Minimum acceptable OCR confidence threshold.

    Returns:
        List of Holding instances extracted from the screenshot.

    Raises:
        ImageNotFoundError: If image file cannot be found.
        LowConfidenceScoreError: If all OCR lines are below threshold.
        OCRError: For general OCR processing exceptions.
    """
    img_file = Path(image_path)

    try:
        if not img_file.exists():
            raise ImageNotFoundError(f"Image not found: {img_file}")

        import easyocr

        reader = easyocr.Reader(["en"], gpu=False)
        results = reader.readtext(str(img_file))

        if not results:
            raise LowConfidenceScoreError("No OCR text detected from image.")

        valid_blocks = [(text, conf) for _, text, conf in results if conf >= min_confidence]
        if not valid_blocks:
            raise LowConfidenceScoreError(
                f"All OCR confidence scores below threshold {min_confidence:.2f}."
            )

        holdings: List[Holding] = []
        for text, conf in valid_blocks:
            holdings.extend(extract_holdings_from_text(text=text, confidence=float(conf)))

        return holdings

    except (ImageNotFoundError, LowConfidenceScoreError):
        logging.exception("OCR validation error.")
        raise
    except Exception as exc:  # pragma: no cover
        logging.exception("Unexpected OCR engine failure.")
        raise OCRError(f"OCR processing failed: {exc}") from exc


def main() -> None:
    """Entrypoint for OCR testing from command line."""
    sample_image = "portfolio.png"
    try:
        holdings = run_ocr(sample_image)
        if not holdings:
            print("Data Deficiency Warning: No ticker/quantity pairs extracted from OCR.")
            return

        print("Extracted Holdings:")
        for h in holdings:
            print(f"- {h.ticker}: {h.quantity} (conf={h.confidence:.2f})")
    except OCRError as exc:
        print(f"OCR failed: {exc}")


if __name__ == "__main__":
    main()
