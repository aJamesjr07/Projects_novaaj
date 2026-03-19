"""Analysis engine for global-vs-Indian context and action recommendation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

from data_fetcher import FeedItem
from ocr_engine import Holding


INDIA_IT_TICKERS = {"TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"}
BANKING_TICKERS = {"HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK"}

GLOBAL_BEARISH_KEYWORDS = {
    "fed hike",
    "rate hike",
    "recession",
    "geopolitical risk",
    "inflation spike",
    "risk-off",
    "bond yields up",
}
GLOBAL_BULLISH_KEYWORDS = {
    "rate cut",
    "soft landing",
    "risk-on",
    "liquidity easing",
    "inflation cools",
}

INDIA_BULLISH_KEYWORDS = {
    "gdp growth",
    "capex",
    "fii inflow",
    "dii buying",
    "policy support",
    "record high",
}
INDIA_BEARISH_KEYWORDS = {
    "rupee weakness",
    "fii outflow",
    "fiscal stress",
    "monsoon risk",
    "regulatory overhang",
    "guidance cut",
}


@dataclass
class AnalysisRow:
    """Final intelligence row for report output.

    Attributes:
        ticker: Portfolio ticker.
        sentiment: Combined sentiment label.
        global_context: Most relevant macro/global context snippet.
        action: Suggested action bucket (Buy/Hold/Sell).
        warning: Optional data deficiency warning.
    """

    ticker: str
    sentiment: str
    global_context: str
    action: str
    warning: str = ""


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    """Check if any keyword appears in text."""
    t = text.lower()
    return any(k in t for k in keywords)


def score_global_sentiment(items: Sequence[FeedItem]) -> int:
    """Score global sentiment from fetched items.

    Args:
        items: Feed items from all sources.

    Returns:
        Integer sentiment score: positive (bullish), negative (bearish), zero (neutral).
    """
    score = 0
    for item in items:
        text = item.text.lower()
        if _contains_any(text, GLOBAL_BEARISH_KEYWORDS):
            score -= 1
        if _contains_any(text, GLOBAL_BULLISH_KEYWORDS):
            score += 1
    return score


def score_india_domestic_sentiment(items: Sequence[FeedItem]) -> int:
    """Score India-specific domestic sentiment from fetched items.

    Args:
        items: Feed items from all sources.

    Returns:
        Integer domestic sentiment score.
    """
    score = 0
    for item in items:
        text = item.text.lower()
        if _contains_any(text, INDIA_BULLISH_KEYWORDS):
            score += 1
        if _contains_any(text, INDIA_BEARISH_KEYWORDS):
            score -= 1
    return score


def infer_direct_impact(ticker: str, global_score: int) -> str:
    """Map global context impact to Indian sectors and tickers.

    Args:
        ticker: Portfolio ticker symbol.
        global_score: Global sentiment score.

    Returns:
        Human-readable direct impact summary.
    """
    t = ticker.upper()
    if t in INDIA_IT_TICKERS and global_score < 0:
        return "Global risk-off may pressure IT exports (USD demand, client spending caution)."
    if t in BANKING_TICKERS and global_score < 0:
        return "Higher global risk aversion can tighten financial conditions for banks."
    if t in INDIA_IT_TICKERS and global_score > 0:
        return "Global risk-on can support IT demand sentiment and valuations."
    return "No strong direct sector mapping from current global signals."


def classify_action(global_score: int, india_score: int) -> str:
    """Classify portfolio action into Buy/Hold/Sell without price targets.

    Args:
        global_score: Global sentiment score.
        india_score: Domestic India sentiment score.

    Returns:
        Action class string.
    """
    if global_score < 0 and india_score > 0:
        return "Hold (Divergence Opportunity)"
    if global_score > 0 and india_score > 0:
        return "Buy"
    if global_score < 0 and india_score < 0:
        return "Sell"
    return "Hold"


def build_report_rows(holdings: Sequence[Holding], items: Sequence[FeedItem]) -> List[AnalysisRow]:
    """Build final report rows for each extracted ticker.

    Args:
        holdings: OCR-extracted portfolio holdings.
        items: Unified social/news feed items.

    Returns:
        List of AnalysisRow suitable for report rendering.
    """
    if not holdings or not items:
        return [
            AnalysisRow(
                ticker="N/A",
                sentiment="N/A",
                global_context="Insufficient input data.",
                action="Hold",
                warning="Data Deficiency Warning",
            )
        ]

    global_score = score_global_sentiment(items)
    india_score = score_india_domestic_sentiment(items)

    if global_score > 0:
        global_label = "Bullish"
    elif global_score < 0:
        global_label = "Bearish"
    else:
        global_label = "Neutral"

    if india_score > 0:
        india_label = "Bullish"
    elif india_score < 0:
        india_label = "Bearish"
    else:
        india_label = "Neutral"

    divergence = global_score < 0 and india_score > 0
    sentiment_label = f"Global={global_label} | India={india_label}"
    if divergence:
        sentiment_label += " | Divergence Opportunity"

    rows: List[AnalysisRow] = []
    for h in holdings:
        context = infer_direct_impact(h.ticker, global_score)
        action = classify_action(global_score, india_score)
        rows.append(
            AnalysisRow(
                ticker=h.ticker,
                sentiment=sentiment_label,
                global_context=context,
                action=action,
            )
        )

    return rows


def main() -> None:
    """Demo main for analyzer module with deficiency-safe behavior."""
    rows = build_report_rows([], [])
    for r in rows:
        if r.warning:
            print(r.warning)
        print(f"{r.ticker} | {r.sentiment} | {r.global_context} | {r.action}")


if __name__ == "__main__":
    main()
