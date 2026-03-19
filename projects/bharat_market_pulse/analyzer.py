"""Analysis engine for Bharat Market Pulse (India context + global events + citations)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence

from data_fetcher import FeedItem
from ocr_engine import Holding


INDIA_IT_TICKERS = {"TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"}
BANKING_TICKERS = {"HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK"}
DEFENSIVE_TICKERS = {"ICICIPHARM", "SUNPHARMA", "DIVISLAB", "DRREDDY"}
GOLD_TICKERS = {"GOLDBEES"}

GLOBAL_BEARISH_KEYWORDS = {
    "fed hike",
    "rate hike",
    "recession",
    "geopolitical risk",
    "inflation spike",
    "risk-off",
    "bond yields up",
    "crude rises",
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
        confidence: 0-1 confidence score based on source quality and volume.
        layman_summary: Simple, plain-English explanation.
        citations: List of source citations used for this row.
        warning: Optional data deficiency warning.
    """

    ticker: str
    sentiment: str
    global_context: str
    action: str
    confidence: float = 0.0
    layman_summary: str = ""
    citations: List[str] = field(default_factory=list)
    warning: str = ""


@dataclass
class AnalysisBundle:
    """Bundle containing report rows plus global event highlights."""

    rows: List[AnalysisRow]
    global_events: List[str]


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    """Check if any keyword appears in text."""
    t = text.lower()
    return any(k in t for k in keywords)


def score_global_sentiment(items: Sequence[FeedItem]) -> int:
    """Score global sentiment from fetched items."""
    score = 0
    for item in items:
        text = item.text.lower()
        if _contains_any(text, GLOBAL_BEARISH_KEYWORDS):
            score -= 1
        if _contains_any(text, GLOBAL_BULLISH_KEYWORDS):
            score += 1
    return score


def score_india_domestic_sentiment(items: Sequence[FeedItem]) -> int:
    """Score India-specific domestic sentiment from fetched items."""
    score = 0
    for item in items:
        text = item.text.lower()
        if _contains_any(text, INDIA_BULLISH_KEYWORDS):
            score += 1
        if _contains_any(text, INDIA_BEARISH_KEYWORDS):
            score -= 1
    return score


def infer_direct_impact(ticker: str, global_score: int) -> str:
    """Map global context impact to Indian sectors and tickers."""
    t = ticker.upper()
    if t in INDIA_IT_TICKERS and global_score < 0:
        return "Global stress can slow overseas tech demand, so Indian IT may stay under pressure."
    if t in BANKING_TICKERS and global_score < 0:
        return "Higher global risk can tighten liquidity and weigh on banking sentiment."
    if t in DEFENSIVE_TICKERS:
        return "Pharma/defensive names usually hold up better during uncertain global phases."
    if t in GOLD_TICKERS:
        return "Gold often acts as a safety cushion when global uncertainty rises."
    if t in INDIA_IT_TICKERS and global_score > 0:
        return "Better global risk mood can support IT spending expectations."
    return "No strong direct sector mapping from current global signals."


def classify_action(global_score: int, india_score: int) -> str:
    """Classify action into Buy/Hold/Sell without price targets."""
    if global_score < 0 and india_score > 0:
        return "Hold"
    if global_score > 0 and india_score > 0:
        return "Buy"
    if global_score < 0 and india_score < 0:
        return "Sell"
    return "Hold"


def _sentiment_labels(global_score: int, india_score: int) -> str:
    """Build combined sentiment label string."""
    global_label = "Bullish" if global_score > 0 else "Bearish" if global_score < 0 else "Neutral"
    india_label = "Bullish" if india_score > 0 else "Bearish" if india_score < 0 else "Neutral"
    divergence = global_score < 0 and india_score > 0
    sentiment = f"Global={global_label} | India={india_label}"
    if divergence:
        sentiment += " | Divergence Opportunity"
    return sentiment


def _select_citations(items: Sequence[FeedItem], limit: int = 3) -> List[str]:
    """Select top citations by reliability.

    Args:
        items: Available feed items.
        limit: Maximum citations.

    Returns:
        Citation strings with source and URL.
    """
    ranked = sorted(items, key=lambda x: float(x.metadata.get("reliability", "0.5")), reverse=True)
    citations: List[str] = []
    for item in ranked[:limit]:
        if item.url:
            citations.append(f"{item.author} ({item.source}) - {item.url}")
    return citations


def _confidence(items: Sequence[FeedItem]) -> float:
    """Compute confidence from source quality and count.

    Args:
        items: Input feed items.

    Returns:
        Confidence score between 0 and 1.
    """
    if not items:
        return 0.0
    avg_rel = sum(float(i.metadata.get("reliability", "0.5")) for i in items) / len(items)
    volume_bonus = min(len(items) / 20.0, 0.15)
    return max(0.0, min(avg_rel + volume_bonus, 1.0))


def _layman_summary(ticker: str, action: str, sentiment: str, context: str) -> str:
    """Generate plain-English summary line for non-technical users."""
    return (
        f"For {ticker}, today looks {sentiment}. Main takeaway: {context} "
        f"Simple action for now: {action}."
    )


def extract_global_events(items: Sequence[FeedItem], limit: int = 5) -> List[str]:
    """Extract top global event headlines for report context."""
    candidates = [
        i for i in items
        if i.metadata.get("pillar") == "global_event" or _contains_any(i.text.lower(), GLOBAL_BEARISH_KEYWORDS | GLOBAL_BULLISH_KEYWORDS)
    ]
    ranked = sorted(candidates, key=lambda x: float(x.metadata.get("reliability", "0.5")), reverse=True)
    out: List[str] = []
    for item in ranked[:limit]:
        headline = item.text.split("\n", 1)[0].strip()
        if headline:
            out.append(f"{headline} ({item.author})")
    return out


def build_analysis_bundle(holdings: Sequence[Holding], items: Sequence[FeedItem]) -> AnalysisBundle:
    """Build rows plus global events bundle.

    Args:
        holdings: OCR holdings.
        items: Feed items.

    Returns:
        AnalysisBundle with rows and global events.
    """
    if not holdings or not items:
        return AnalysisBundle(
            rows=[
                AnalysisRow(
                    ticker="N/A",
                    sentiment="N/A",
                    global_context="Insufficient input data.",
                    action="Hold",
                    warning="Data Deficiency Warning",
                    confidence=0.0,
                    layman_summary="Not enough reliable data to produce a confident update today.",
                    citations=[],
                )
            ],
            global_events=[],
        )

    global_score = score_global_sentiment(items)
    india_score = score_india_domestic_sentiment(items)
    sentiment_label = _sentiment_labels(global_score, india_score)
    citations = _select_citations(items)
    confidence = _confidence(items)

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
                confidence=round(confidence, 2),
                layman_summary=_layman_summary(h.ticker, action, sentiment_label, context),
                citations=citations,
            )
        )

    return AnalysisBundle(rows=rows, global_events=extract_global_events(items))


def build_report_rows(holdings: Sequence[Holding], items: Sequence[FeedItem]) -> List[AnalysisRow]:
    """Compatibility wrapper returning only rows."""
    return build_analysis_bundle(holdings, items).rows


def main() -> None:
    """Demo main for analyzer module with deficiency-safe behavior."""
    bundle = build_analysis_bundle([], [])
    for r in bundle.rows:
        if r.warning:
            print(r.warning)
        print(f"{r.ticker} | {r.sentiment} | {r.global_context} | {r.action}")


if __name__ == "__main__":
    main()
