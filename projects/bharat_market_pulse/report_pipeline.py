"""Daily Bharat Market Pulse pipeline entrypoint."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from agent_extractor import load_agent_extracted_holdings
from analyzer import AnalysisBundle, AnalysisRow, build_analysis_bundle
from config import get_settings
from data_fetcher import fetch_all_sources
from export_utils import ensure_output_dir, export_rows_csv, export_rows_json
from llm_extractor import LLMExtractorSettings, run_llm_extraction
from ocr_engine import Holding, OCRError, run_ocr
from telegram_formatter import format_telegram_digest


def render_report(bundle: AnalysisBundle) -> str:
    """Render a friendly, descriptive daily report with sources.

    Args:
        bundle: Analysis bundle with rows and global events.

    Returns:
        Markdown report string.
    """
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
        lines.append(f"- Overall confidence is **{avg_conf:.2f}** (higher = better source backing).")
    else:
        lines.append("- Not enough reliable input to generate a confident portfolio view today.")
    lines.append("")

    lines.append("## Important Global Events (and why you should care)")
    if bundle.global_events:
        for e in bundle.global_events:
            lines.append(f"- {e}")
    else:
        lines.append("- No high-priority global trigger detected from available sources in this run.")
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

    return "\n".join(lines)


def main() -> None:
    """Run agent-json -> LLM -> OCR extraction, then fetch/analyze/report."""
    settings = get_settings()
    image_path = settings.market_report_image_path

    holdings: List[Holding] = []

    if settings.use_agent_extract_first:
        holdings = load_agent_extracted_holdings(settings.agent_extract_file_path)
        if holdings:
            print(f"Agent JSON extraction loaded: {len(holdings)} holdings.")

    if not holdings and settings.use_llm_first:
        try:
            llm_settings = LLMExtractorSettings(
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                base_url=settings.llm_base_url,
                timeout_seconds=settings.llm_timeout_seconds,
            )
            holdings = run_llm_extraction(image_path, llm_settings)
            print(f"LLM extraction succeeded: {len(holdings)} holdings parsed.")
        except Exception as exc:
            print(f"LLM extraction unavailable/failed, falling back to OCR ({exc})")

    if not holdings:
        try:
            holdings = run_ocr(image_path)
            print(f"OCR fallback parsed: {len(holdings)} holdings.")
        except OCRError as exc:
            print(f"Data Deficiency Warning: OCR stage failed ({exc})")
            holdings = []

    feed_items = fetch_all_sources()
    bundle = build_analysis_bundle(holdings=holdings, items=feed_items)

    report = render_report(bundle)
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

    print(f"\nReport written to: {md_path}")
    print(f"CSV written to: {csv_path}")
    print(f"JSON written to: {json_path}")
    print(f"Telegram digest written to: {digest_path}")


if __name__ == "__main__":
    main()
