"""Daily Bharat Market Pulse pipeline entrypoint."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from agent_extractor import load_agent_extracted_holdings
from analyzer import AnalysisBundle, build_analysis_bundle
from config import get_settings, resolve_image_paths
from data_fetcher import fetch_all_sources
from export_utils import ensure_output_dir, export_rows_csv, export_rows_json
from llm_extractor import LLMExtractorSettings, run_llm_extraction
from news_collector import collect_seed_news
from ocr_engine import Holding, OCRError, run_ocr
from swarm_engine import SwarmOutcome, run_swarm_debate
from telegram_formatter import format_telegram_digest

logger = logging.getLogger(__name__)


@dataclass
class RunSummary:
    holdings_count: int = 0
    extraction_method: str = "none"
    sources_fetched_count: int = 0
    warnings: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)


def _setup_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )


def _merge_holdings(existing: List[Holding], incoming: List[Holding]) -> List[Holding]:
    """Merge holdings by ticker, keeping highest confidence entry."""
    merged = {h.ticker: h for h in existing}
    for h in incoming:
        prev = merged.get(h.ticker)
        if prev is None or h.confidence > prev.confidence:
            merged[h.ticker] = h
    return list(merged.values())


def render_report(bundle: AnalysisBundle, swarm: SwarmOutcome | None = None) -> str:
    """Render a friendly, descriptive daily report with sources."""
    rows = bundle.rows
    lines = ["# Bharat Market Pulse - Daily Report", ""]

    lines.append("## Quick Read (30 seconds)")
    if rows and rows[0].ticker != "N/A":
        hold_count = sum(1 for r in rows if r.action == "Hold")
        buy_count = sum(1 for r in rows if r.action == "Buy")
        sell_count = sum(1 for r in rows if r.action == "Sell")
        avg_conf = sum(r.confidence for r in rows) / max(len(rows), 1)
        lines.append(
            f"- Today we reviewed **{len(rows)} holdings**. Actions: **Buy {buy_count}**, **Hold {hold_count}**, **Sell {sell_count}**."
        )
        lines.append(
            f"- Overall confidence is **{avg_conf:.2f}** (higher = better source backing)."
        )
    else:
        lines.append(
            "- Not enough reliable input to generate a confident portfolio view today."
        )
    lines.append("")

    if rows and rows[0].ticker != "N/A":
        lines.append("## What This Means For You (Simple)")
        buys = [r.ticker for r in rows if r.action == "Buy"]
        holds = [r.ticker for r in rows if r.action == "Hold"]
        sells = [r.ticker for r in rows if r.action == "Sell"]
        lines.append(
            f"- **Add/accumulate watchlist:** {', '.join(buys) if buys else 'None today'}"
        )
        lines.append(f"- **Hold/monitor:** {', '.join(holds) if holds else 'None'}")
        lines.append(
            f"- **Reduce/exit watchlist:** {', '.join(sells) if sells else 'None today'}"
        )
        lines.append(
            "- Focus on risk control first; act only on high-confidence, catalyst-backed signals."
        )
        lines.append("")

    if swarm is not None:
        lines.append("## Swarm View (4-Agent Predictive Sandbox)")
        lines.append(
            f"- Consensus: **{swarm.consensus_label}** ({swarm.consensus_score:+.2f}) | Confidence: **{swarm.confidence_1_to_10}/10**"
        )
        lines.append(f"- Sanity Guard: {swarm.sanity.reason}")
        for n in swarm.notes[:3]:
            lines.append(f"- {n}")
        lines.append("")

    lines.append("## Important Global Events (and why you should care)")
    if bundle.global_events:
        for e in bundle.global_events:
            lines.append(f"- {e}")
    else:
        lines.append(
            "- No high-priority global trigger detected from available sources in this run."
        )
    lines.append("")

    lines.append("## Portfolio Action Table")
    lines.append("Ticker | Sentiment | Global Context | Action | Confidence")
    lines.append("---|---|---|---|---")
    for row in rows:
        safe_sentiment = row.sentiment.replace("|", "/")
        safe_context = row.global_context.replace("|", ";")
        lines.append(
            f"{row.ticker} | {safe_sentiment} | {safe_context} | {row.action} | {row.confidence:.2f}"
        )
    lines.append("")

    lines.append("## In Simple Words")
    for row in rows:
        lines.append(f"- **{row.ticker}:** {row.layman_summary}")
        if row.warning:
            lines.append(f"  - ⚠️ Data Deficiency Warning: {row.warning}")
    lines.append("")

    all_citations: List[str] = []
    for row in rows:
        all_citations.extend(row.citations)

    unique_citations = list(dict.fromkeys(all_citations))
    lines.append("## Sources")
    if unique_citations:
        for c in unique_citations:
            lines.append(f"- {c}")
    else:
        lines.append("- Data Deficiency Warning: No reliable sources available today.")

    lines.append("")
    lines.append(
        "_Disclaimer: This is a research-assist portfolio monitoring report, not financial advice. Results depend on source quality and extraction quality._"
    )

    return "\n".join(lines)


def _emit_summary(summary: RunSummary) -> None:
    logger.info("Run Summary")
    logger.info("- holdings extracted: %d", summary.holdings_count)
    logger.info("- extraction method: %s", summary.extraction_method)
    logger.info("- sources fetched: %d", summary.sources_fetched_count)
    logger.info("- warnings: %d", len(summary.warnings))
    for warning in summary.warnings:
        logger.warning("  warning: %s", warning)
    logger.info("- output files: %d", len(summary.output_files))
    for path in summary.output_files:
        logger.info("  %s", path)


def main() -> None:
    """Run extraction -> fetch -> analysis -> swarm -> report with graceful degradation."""
    _setup_logging()
    settings = get_settings()
    image_paths = resolve_image_paths(settings)
    summary = RunSummary()

    if not image_paths:
        summary.warnings.append(
            "No image paths configured; extraction will rely on agent JSON only."
        )

    holdings: List[Holding] = []

    if settings.use_agent_extract_first:
        holdings = load_agent_extracted_holdings(settings.agent_extract_file_path)
        if holdings:
            summary.extraction_method = "agent_json"
            logger.info("Agent JSON extraction loaded: %d holdings.", len(holdings))

    if not holdings and settings.use_llm_first:
        llm_settings = LLMExtractorSettings(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        for image_path in image_paths:
            try:
                parsed = run_llm_extraction(image_path, llm_settings)
                holdings = _merge_holdings(holdings, parsed)
            except Exception as exc:  # noqa: BLE001
                warning = f"LLM extraction unavailable/failed for {image_path} ({exc})"
                summary.warnings.append(warning)
                logger.warning(warning)
        if holdings:
            summary.extraction_method = "llm"
            logger.info("LLM extraction succeeded: %d merged holdings parsed.", len(holdings))

    if not holdings:
        for image_path in image_paths:
            try:
                parsed = run_ocr(image_path)
                holdings = _merge_holdings(holdings, parsed)
            except OCRError as exc:
                warning = f"OCR failed for {image_path} ({exc})"
                summary.warnings.append(warning)
                logger.warning("Data Deficiency Warning: %s", warning)
        if holdings:
            summary.extraction_method = "ocr"
            logger.info("OCR fallback parsed: %d merged holdings.", len(holdings))

    if not holdings:
        summary.extraction_method = "none"
        summary.warnings.append(
            "No holdings extracted; generating report with deficiency warnings."
        )

    feed_items = fetch_all_sources()
    summary.sources_fetched_count = len(feed_items)
    if not feed_items:
        summary.warnings.append("No feed items fetched; report confidence may be low.")

    bundle = build_analysis_bundle(holdings=holdings, items=feed_items)

    seeds = collect_seed_news(limit=10)
    if not seeds:
        summary.warnings.append("No trusted seed news available for swarm debate.")
    swarm = run_swarm_debate(seeds, rounds=3, baseline_volatility=0.25)

    report = render_report(bundle, swarm=swarm)
    print(report)

    out_dir = (Path(__file__).resolve().parent / settings.report_output_dir).resolve()
    ensure_output_dir(out_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = out_dir / f"daily_report_{timestamp}.md"
    csv_path = out_dir / f"daily_report_{timestamp}.csv"
    json_path = out_dir / f"daily_report_{timestamp}.json"

    md_path.write_text(report, encoding="utf-8")
    export_rows_csv(bundle.rows, csv_path)
    export_rows_json(bundle.rows, json_path)

    digest = format_telegram_digest(bundle.rows)
    digest_path = out_dir / f"telegram_digest_{timestamp}.txt"
    digest_path.write_text(digest, encoding="utf-8")

    summary.holdings_count = len(holdings)
    summary.output_files.extend([
        str(md_path),
        str(csv_path),
        str(json_path),
        str(digest_path),
    ])

    _emit_summary(summary)


if __name__ == "__main__":
    main()
