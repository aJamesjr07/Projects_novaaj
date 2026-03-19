"""Daily Indian Market Intelligence report pipeline entrypoint."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from analyzer import AnalysisRow, build_report_rows
from config import get_settings
from data_fetcher import fetch_all_sources
from export_utils import ensure_output_dir, export_rows_csv, export_rows_json
from ocr_engine import Holding, OCRError, run_ocr
from telegram_formatter import format_telegram_digest


def render_report(rows: List[AnalysisRow]) -> str:
    """Render final text report table.

    Args:
        rows: Analysis rows to render.

    Returns:
        Markdown table as string.
    """
    header = "Ticker | Sentiment | Global Context | Action"
    separator = "---|---|---|---"
    lines = [header, separator]

    for row in rows:
        lines.append(f"{row.ticker} | {row.sentiment} | {row.global_context} | {row.action}")
        if row.warning:
            lines.append(f"Data Deficiency Warning: {row.warning}")

    return "\n".join(lines)


def main() -> None:
    """Run full OCR -> Fetch -> Analyze -> Report pipeline."""
    settings = get_settings()
    image_path = settings.market_report_image_path

    try:
        holdings: List[Holding] = run_ocr(image_path)
    except OCRError as exc:
        print(f"Data Deficiency Warning: OCR stage failed ({exc})")
        holdings = []

    feed_items = fetch_all_sources()
    rows = build_report_rows(holdings=holdings, items=feed_items)

    report = render_report(rows)
    print(report)

    out_dir = (Path(__file__).resolve().parent / settings.report_output_dir).resolve()
    ensure_output_dir(out_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = out_dir / f"daily_report_{timestamp}.md"
    csv_path = out_dir / f"daily_report_{timestamp}.csv"
    json_path = out_dir / f"daily_report_{timestamp}.json"

    md_path.write_text(report, encoding="utf-8")
    export_rows_csv(rows, csv_path)
    export_rows_json(rows, json_path)

    digest = format_telegram_digest(rows)
    digest_path = out_dir / f"telegram_digest_{timestamp}.txt"
    digest_path.write_text(digest, encoding="utf-8")

    print(f"\nReport written to: {md_path}")
    print(f"CSV written to: {csv_path}")
    print(f"JSON written to: {json_path}")
    print(f"Telegram digest written to: {digest_path}")


if __name__ == "__main__":
    main()
