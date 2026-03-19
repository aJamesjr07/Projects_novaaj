"""Daily Indian Market Intelligence report pipeline entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import List

from analyzer import AnalysisRow, build_report_rows
from data_fetcher import fetch_all_sources
from ocr_engine import Holding, OCRError, run_ocr


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
    image_path = "portfolio.png"

    try:
        holdings: List[Holding] = run_ocr(image_path)
    except OCRError as exc:
        print(f"Data Deficiency Warning: OCR stage failed ({exc})")
        holdings = []

    feed_items = fetch_all_sources()
    rows = build_report_rows(holdings=holdings, items=feed_items)

    report = render_report(rows)
    print(report)

    output_path = Path(__file__).resolve().parent / "daily_report.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"\nReport written to: {output_path}")


if __name__ == "__main__":
    main()
