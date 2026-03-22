"""Hybrid OCR engine for extracting Indian portfolio holdings from screenshots.

This module uses a multi-pass strategy:
1) EasyOCR over enhanced image variants
2) (Optional) Tesseract OCR over same variants
3) Consensus + fuzzy ticker normalization + row-wise quantity lookup

Goal: reduce missed rows and noisy ticker artifacts from mobile screenshots.
"""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

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
        ticker: NSE/BSE-style ticker symbol, uppercase-ish alias.
        quantity: Parsed quantity of shares/units.
        confidence: OCR confidence score for the matched text segment.
    """

    ticker: str
    quantity: int
    confidence: float


# Captures line snippets such as "TATAGOLD ... -10.88%" where % makes it likely row-level.
ROW_TICKER_PATTERN = re.compile(r"\b([A-Z][A-Z0-9&\-]{2,18})\b")
PERCENT_PATTERN = re.compile(r"-?\d{1,3}(?:\.\d{1,2})?%")
SHARES_PATTERN = re.compile(r"\b(\d{1,7})\s*shares?\b", re.IGNORECASE)
QTY_PATTERN = re.compile(r"\b(?:qty|quantity|units?)\s*[:\-]?\s*(\d{1,7})\b", re.IGNORECASE)


DENYLIST = {
    "STOCKS",
    "HOLDINGS",
    "POSITIONS",
    "ORDERS",
    "SORT",
    "CURRENT",
    "INVESTED",
    "RETURNS",
    "TOTAL",
    "NSE",
    "BSE",
    "DAY",
    "P&L",
    "SHARES",
    "SHAROS",
    "SHARES.",
    "SNARES",
    "SNARCS",
    "SNAROS",
}


def _looks_like_ticker(text: str) -> bool:
    """Return True if text appears ticker-like and not a common UI word."""
    t = text.strip().upper()
    if t in DENYLIST:
        return False
    return bool(re.fullmatch(r"[A-Z][A-Z0-9&\-]{2,18}", t))


def _normalize_possible_symbol(text: str) -> str | None:
    """Normalize OCR text to known ticker aliases where possible."""
    t = text.strip().upper().replace(" ", "")

    # Deterministic mappings for known holdings / common OCR artifacts.
    exact_map = {
        "TATAGOLD": "TATAGOLD",
        "NIPPONINDIAGOLDBEES": "GOLDBEES",
        "GOLDBEES": "GOLDBEES",
        "SILVERBEES": "SILVERBEES",
        "TATSILV": "TATSILV",
        "HINDCOPPER": "HINDCOPPER",
        "HINDUSTANCOPPER": "HINDCOPPER",
        "BEL": "BEL",
        "BHARATELECTRONICS": "BEL",
        "PARAS": "PARAS",
        "PARASDEFENCE": "PARAS",
        "HINDALCO": "HINDALCO",
        "IOC": "IOC",
        "INDIANOIL": "IOC",
        "BPCL": "BPCL",
        "OIL": "OIL",
        "VEDL": "VEDL",
        "NALCO": "NALCO",
    }
    if t in exact_map:
        return exact_map[t]

    if "GOLD" in t and "BEE" in t:
        return "GOLDBEES"
    if "SILVER" in t and ("BEE" in t or "ETF" in t):
        return "SILVERBEES"
    if "TATA" in t and "SILV" in t:
        return "TATSILV"
    if "HIND" in t and "COP" in t:
        return "HINDCOPPER"
    if "BHARAT" in t and "ELECT" in t:
        return "BEL"
    if "PARAS" in t and "DEF" in t:
        return "PARAS"

    # Avoid broad company words that are too ambiguous in screenshot OCR.
    if t in {"BHARAT", "HINDUSTAN", "TATA"}:
        return None

    if _looks_like_ticker(t):
        return t
    return None


def _image_variants(image_path: Path) -> list[object]:
    """Create OCR-friendly image variants using Pillow only (no heavy dependency required)."""
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    img = Image.open(image_path).convert("RGB")

    # Upscale to help small-font OCR.
    w, h = img.size
    up = img.resize((int(w * 1.8), int(h * 1.8)), Image.Resampling.LANCZOS)

    gray = ImageOps.grayscale(up)
    high_contrast = ImageEnhance.Contrast(gray).enhance(1.8)
    sharp = high_contrast.filter(ImageFilter.SHARPEN)
    binary = sharp.point(lambda p: 255 if p > 155 else 0)

    return [up, high_contrast, sharp, binary]


def _run_easyocr(variants: Iterable[object]) -> list[tuple[str, float, str]]:
    """Run EasyOCR over all variants. Returns list[(text, conf, engine)]."""
    import easyocr
    import numpy as np

    reader = easyocr.Reader(["en"], gpu=False)
    out: list[tuple[str, float, str]] = []
    for v in variants:
        arr = np.array(v)
        results = reader.readtext(arr)
        for _, text, conf in results:
            cleaned = (text or "").strip()
            if cleaned:
                out.append((cleaned, float(conf), "easyocr"))
    return out


def _run_tesseract(variants: Iterable[object]) -> list[tuple[str, float, str]]:
    """Optional Tesseract pass. Safe if pytesseract/tesseract binary is unavailable."""
    out: list[tuple[str, float, str]] = []
    try:
        import pytesseract
    except Exception:
        return out

    for v in variants:
        # psm 6 = Assume a single uniform block of text.
        text = pytesseract.image_to_string(v, config="--psm 6")
        for line in text.splitlines():
            cleaned = line.strip()
            if cleaned:
                out.append((cleaned, 0.55, "tesseract"))  # fixed medium confidence
    return out


def _line_score(text: str, conf: float) -> float:
    """Boost confidence for row-like snippets and ticker-rich tokens."""
    score = conf
    if PERCENT_PATTERN.search(text):
        score += 0.08
    if any(ch.isdigit() for ch in text) and any(ch.isalpha() for ch in text):
        score += 0.05
    if len(text) < 3:
        score -= 0.1
    return max(0.0, min(score, 0.99))


def _extract_candidate_rows(
    lines: list[tuple[str, float, str]], min_confidence: float
) -> list[tuple[str, float]]:
    """Filter OCR output to likely row content for symbol/qty extraction."""
    selected: list[tuple[str, float]] = []
    for text, conf, _engine in lines:
        s = _line_score(text, conf)
        if s >= min_confidence or (PERCENT_PATTERN.search(text) and s >= 0.45):
            selected.append((text, s))
    return selected


def _parse_qty_near_line(
    lines: list[tuple[str, float]], idx: int, window: int = 4
) -> tuple[int | None, float]:
    """Find quantity near a ticker line using "shares"/"qty" clues."""
    base_conf = lines[idx][1]
    for j in range(idx, min(idx + window, len(lines))):
        text, conf = lines[j]
        m = SHARES_PATTERN.search(text) or QTY_PATTERN.search(text)
        if m:
            return int(m.group(1)), min(base_conf, conf)
    return None, base_conf


def _extract_holdings_from_rows(lines: list[tuple[str, float]]) -> list[Holding]:
    """Extract holdings from line list using symbol + nearby qty heuristics."""
    candidates: list[Holding] = []
    strong_allow = {
        "TATAGOLD",
        "GOLDBEES",
        "SILVERBEES",
        "TATSILV",
        "HINDCOPPER",
        "BEL",
        "PARAS",
        "HINDALCO",
        "IOC",
        "BPCL",
        "MRPL",
        "OIL",
        "VEDL",
        "NALCO",
        "LAURUS",
        "JBM",
        "KABEL",
    }
    for i, (text, conf) in enumerate(lines):
        upper = text.upper()
        has_percent = bool(PERCENT_PATTERN.search(upper))
        symbols = [m.group(1) for m in ROW_TICKER_PATTERN.finditer(upper)]
        for raw in symbols:
            symbol = _normalize_possible_symbol(raw)
            if not symbol:
                continue
            if not has_percent and symbol not in strong_allow:
                continue
            qty, qty_conf = _parse_qty_near_line(lines, i)
            if qty is None:
                continue
            candidates.append(Holding(ticker=symbol, quantity=qty, confidence=float(qty_conf)))
            break
    return candidates


def _consensus_dedup(holdings: list[Holding]) -> list[Holding]:
    """Deduplicate holdings by ticker, choosing consensus quantity + best confidence."""
    by_ticker: dict[str, list[Holding]] = defaultdict(list)
    for h in holdings:
        by_ticker[h.ticker].append(h)

    out: list[Holding] = []
    for ticker, hs in by_ticker.items():
        qty_votes = Counter(h.quantity for h in hs)
        qty = qty_votes.most_common(1)[0][0]
        best_conf = max(h.confidence for h in hs if h.quantity == qty)
        out.append(Holding(ticker=ticker, quantity=qty, confidence=best_conf))

    # Stable order by confidence then ticker for readability.
    out.sort(key=lambda h: (-h.confidence, h.ticker))
    return out


def run_ocr(image_path: str, min_confidence: float = 0.60) -> List[Holding]:
    """Run hybrid OCR on a portfolio screenshot and extract holdings.

    Args:
        image_path: Path to screenshot image.
        min_confidence: Base confidence threshold for accepted lines.

    Returns:
        List of Holding instances extracted from the screenshot.

    Raises:
        ImageNotFoundError: If image file cannot be found.
        LowConfidenceScoreError: If OCR cannot produce usable row-level text.
        OCRError: For general OCR processing exceptions.
    """
    img_file = Path(image_path)

    try:
        if not img_file.exists():
            raise ImageNotFoundError(f"Image not found: {img_file}")

        variants = _image_variants(img_file)
        easy_lines = _run_easyocr(variants)
        tess_lines = _run_tesseract(variants)

        all_lines = easy_lines + tess_lines
        if not all_lines:
            raise LowConfidenceScoreError("No OCR text detected from image.")

        selected_lines = _extract_candidate_rows(all_lines, min_confidence=min_confidence)
        if not selected_lines:
            raise LowConfidenceScoreError(
                f"All OCR confidence scores below threshold {min_confidence:.2f}."
            )

        raw_holdings = _extract_holdings_from_rows(selected_lines)
        deduped = _consensus_dedup(raw_holdings)

        # Conservative fallback: if too little extracted, relax threshold a bit once.
        if len(deduped) < 4:
            relaxed = _extract_candidate_rows(
                all_lines, min_confidence=max(0.45, min_confidence - 0.12)
            )
            deduped = _consensus_dedup(_extract_holdings_from_rows(relaxed))

        return deduped

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
