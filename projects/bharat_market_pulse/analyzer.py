"""Analysis engine for Bharat Market Pulse (India context + global events + citations).

Phase B upgrade:
- Adds lightweight entity-relation graph extraction from feed text.
- Uses graph evidence to produce ticker-specific impact context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence

from data_fetcher import FeedItem
from ocr_engine import Holding


INDIA_IT_TICKERS = {"TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"}
BANKING_TICKERS = {"HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK"}
DEFENSIVE_TICKERS = {"ICICIPHARM", "SUNPHARMA", "DIVISLAB", "DRREDDY", "LAURUS"}
GOLD_TICKERS = {"GOLDBEES", "TATAGOLD"}
SILVER_TICKERS = {"SILVERBEES", "TATSILV"}
METAL_TICKERS = {"HINDALCO", "HINDCOPPER", "VEDL", "NALCO"}
ENERGY_TICKERS = {"IOC", "BPCL", "OIL", "MRPL"}
DEFENCE_TICKERS = {"BEL", "PARAS"}

GLOBAL_BEARISH_KEYWORDS = {
    "fed hike",
    "rate hike",
    "recession",
    "geopolitical risk",
    "inflation spike",
    "risk-off",
    "bond yields up",
    "crude rises",
    "selloff",
    "blood bath",
}
GLOBAL_BULLISH_KEYWORDS = {
    "rate cut",
    "soft landing",
    "risk-on",
    "liquidity easing",
    "inflation cools",
    "rally",
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
    """Final intelligence row for report output."""

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


@dataclass
class RelationEvidence:
    """Single extracted market relation from source text."""

    entity: str
    relation: str
    polarity: str  # bullish / bearish / neutral
    reason: str
    source: str
    url: str
    reliability: float


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _sentiment_labels(global_score: int, india_score: int) -> str:
    global_label = "Bullish" if global_score > 0 else "Bearish" if global_score < 0 else "Neutral"
    india_label = "Bullish" if india_score > 0 else "Bearish" if india_score < 0 else "Neutral"
    divergence = global_score < 0 and india_score > 0
    sentiment = f"Global={global_label} | India={india_label}"
    if divergence:
        sentiment += " | Divergence Opportunity"
    return sentiment


def score_global_sentiment(items: Sequence[FeedItem]) -> int:
    score = 0
    for item in items:
        text = item.text.lower()
        if _contains_any(text, GLOBAL_BEARISH_KEYWORDS):
            score -= 1
        if _contains_any(text, GLOBAL_BULLISH_KEYWORDS):
            score += 1
    return score


def score_india_domestic_sentiment(items: Sequence[FeedItem]) -> int:
    score = 0
    for item in items:
        text = item.text.lower()
        if _contains_any(text, INDIA_BULLISH_KEYWORDS):
            score += 1
        if _contains_any(text, INDIA_BEARISH_KEYWORDS):
            score -= 1
    return score


def _ticker_entities(ticker: str) -> set[str]:
    t = ticker.upper()
    entities = {t}
    if t in GOLD_TICKERS:
        entities |= {"gold", "precious_metals", "safe_haven", "commodity"}
    if t in SILVER_TICKERS:
        entities |= {"silver", "precious_metals", "commodity"}
    if t in METAL_TICKERS:
        entities |= {"base_metals", "metals", "commodity"}
    if t in ENERGY_TICKERS:
        entities |= {"oil", "crude", "energy", "refining"}
    if t in DEFENCE_TICKERS:
        entities |= {"defence", "government_orders", "capex"}
    if t in DEFENSIVE_TICKERS:
        entities |= {"pharma", "defensive"}
    if t in INDIA_IT_TICKERS:
        entities |= {"it_services", "usd", "exports"}
    if t in BANKING_TICKERS:
        entities |= {"rates", "liquidity", "credit"}
    return entities


def _extract_entity_relations(items: Sequence[FeedItem]) -> list[RelationEvidence]:
    """Build a lightweight knowledge graph from feed text.

    We keep this deterministic (keyword-driven) for reliability and cost control.
    """
    patterns = [
        # entity, include_terms, relation, polarity, reason
        ("gold", {"gold", "goldbees", "safe haven"}, "benefits_from_uncertainty", "bullish", "Gold demand tends to rise in risk-off phases."),
        ("silver", {"silver", "silverbees", "industrial metal"}, "volatile_on_risk_shift", "neutral", "Silver reacts to both risk sentiment and industrial demand."),
        ("base_metals", {"aluminium", "aluminum", "copper", "metal prices", "lme"}, "sensitive_to_growth_cycle", "neutral", "Base metals track global growth and China demand cues."),
        ("oil", {"crude", "oil", "brent", "wti"}, "drives_energy_margin_risk", "bearish", "Rising crude can pressure refiners/OMCs on margin timing."),
        ("defence", {"defence", "defense", "order win", "ministry of defence", "contract"}, "supported_by_order_flow", "bullish", "Order inflows can support defence names."),
        ("rates", {"fed", "rate", "bond yield", "yields"}, "impacts_risk_appetite", "bearish", "Higher rates/yields can reduce equity risk appetite."),
        ("usd", {"dollar", "dxy", "rupee", "inr"}, "fx_sensitivity", "neutral", "Currency moves can shift import/export profitability."),
        ("pharma", {"fda", "usfda", "drug", "formulation"}, "defensive_resilience", "bullish", "Pharma can hold relatively better in uncertain phases."),
        ("capex", {"capex", "infrastructure", "government spending"}, "supports_domestic_cyclicals", "bullish", "Domestic capex cycle supports industrial demand."),
    ]

    out: list[RelationEvidence] = []
    for item in items:
        text = item.text.lower()
        rel = float(item.metadata.get("reliability", "0.5"))
        for entity, terms, relation, polarity, reason in patterns:
            if any(term in text for term in terms):
                out.append(
                    RelationEvidence(
                        entity=entity,
                        relation=relation,
                        polarity=polarity,
                        reason=reason,
                        source=f"{item.author} ({item.source})",
                        url=item.url,
                        reliability=rel,
                    )
                )
    return out


def _rank_relevant_evidence(ticker: str, graph: Sequence[RelationEvidence], limit: int = 2) -> list[RelationEvidence]:
    entities = _ticker_entities(ticker)
    matches = [g for g in graph if g.entity in entities]
    matches.sort(key=lambda x: x.reliability, reverse=True)
    return matches[:limit]


def infer_direct_impact(ticker: str, global_score: int, graph: Sequence[RelationEvidence]) -> str:
    evidence = _rank_relevant_evidence(ticker, graph, limit=2)
    if evidence:
        lines = [f"{e.reason} ({e.source})" for e in evidence]
        return " | ".join(lines)

    # fallback to old deterministic sector map if no graph evidence
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


def classify_action(global_score: int, india_score: int, graph_evidence: Sequence[RelationEvidence]) -> str:
    """Classify action into Buy/Hold/Sell without price targets.

    Graph evidence gently tilts final action when macro signals are mixed.
    """
    bullish = sum(1 for e in graph_evidence if e.polarity == "bullish")
    bearish = sum(1 for e in graph_evidence if e.polarity == "bearish")

    if global_score < 0 and india_score < 0:
        return "Sell"
    if global_score > 0 and india_score > 0:
        return "Buy"

    if bullish >= bearish + 1:
        return "Buy"
    if bearish >= bullish + 1:
        return "Hold"
    return "Hold"


def _select_citations(items: Sequence[FeedItem], limit: int = 3) -> List[str]:
    ranked = sorted(items, key=lambda x: float(x.metadata.get("reliability", "0.5")), reverse=True)
    citations: List[str] = []
    for item in ranked[:limit]:
        if item.url:
            citations.append(f"{item.author} ({item.source}) - {item.url}")
    return citations


def _confidence(items: Sequence[FeedItem], graph_hits: int) -> float:
    if not items:
        return 0.0
    avg_rel = sum(float(i.metadata.get("reliability", "0.5")) for i in items) / len(items)
    volume_bonus = min(len(items) / 20.0, 0.12)
    graph_bonus = min(graph_hits * 0.03, 0.12)
    return max(0.0, min(avg_rel + volume_bonus + graph_bonus, 1.0))


def _layman_summary(ticker: str, action: str, sentiment: str, context: str) -> str:
    return (
        f"For {ticker}, today looks {sentiment}. Main takeaway: {context} "
        f"Simple action for now: {action}."
    )


def extract_global_events(items: Sequence[FeedItem], limit: int = 5) -> List[str]:
    high_impact_terms = {"fed", "rate", "inflation", "crude", "oil", "bond", "yields", "dollar", "war"}

    candidates = [
        i for i in items
        if i.metadata.get("pillar") == "global_event"
        or _contains_any(i.text.lower(), GLOBAL_BEARISH_KEYWORDS | GLOBAL_BULLISH_KEYWORDS)
    ]

    def _score(item: FeedItem) -> float:
        rel = float(item.metadata.get("reliability", "0.5"))
        text = item.text.lower()
        bonus = 0.2 if any(t in text for t in high_impact_terms) else 0.0
        return rel + bonus

    ranked = sorted(candidates, key=_score, reverse=True)
    out: List[str] = []
    for item in ranked[:limit]:
        headline = item.text.split("\n", 1)[0].strip()
        if not headline:
            continue

        text = item.text.lower()
        level = "High" if any(t in text for t in high_impact_terms) else "Medium"
        if "crude" in text or "oil" in text:
            why = "May impact inflation and import-heavy sectors in India."
        elif "fed" in text or "rate" in text or "yields" in text:
            why = "Can shift global risk appetite and affect Indian equity flows."
        elif "dollar" in text:
            why = "May affect INR and exporters/importers differently."
        else:
            why = "Could influence overall market sentiment."

        out.append(f"[{level}] {headline} ({item.author}) — {why} | Source: {item.url}")
    return out


def build_analysis_bundle(holdings: Sequence[Holding], items: Sequence[FeedItem]) -> AnalysisBundle:
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

    graph = _extract_entity_relations(items)

    rows: List[AnalysisRow] = []
    for h in holdings:
        rel_evidence = _rank_relevant_evidence(h.ticker, graph, limit=3)
        context = infer_direct_impact(h.ticker, global_score, graph)
        action = classify_action(global_score, india_score, rel_evidence)

        row_citations: List[str] = []
        for ev in rel_evidence[:3]:
            if ev.url:
                row_citations.append(f"{ev.source} - {ev.url}")
        if not row_citations:
            row_citations = _select_citations(items)

        conf = _confidence(items, graph_hits=len(rel_evidence))
        rows.append(
            AnalysisRow(
                ticker=h.ticker,
                sentiment=sentiment_label,
                global_context=context,
                action=action,
                confidence=round(conf, 2),
                layman_summary=_layman_summary(h.ticker, action, sentiment_label, context),
                citations=row_citations,
            )
        )

    return AnalysisBundle(rows=rows, global_events=extract_global_events(items))


def build_report_rows(holdings: Sequence[Holding], items: Sequence[FeedItem]) -> List[AnalysisRow]:
    return build_analysis_bundle(holdings, items).rows


def main() -> None:
    bundle = build_analysis_bundle([], [])
    for r in bundle.rows:
        if r.warning:
            print(r.warning)
        print(f"{r.ticker} | {r.sentiment} | {r.global_context} | {r.action}")


if __name__ == "__main__":
    main()
