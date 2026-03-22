"""Telegram digest formatter for report summaries."""

from __future__ import annotations

from typing import Sequence

from .analyzer import AnalysisRow


def format_telegram_digest(rows: Sequence[AnalysisRow]) -> str:
    """Format report rows into a compact Telegram-ready digest.

    Args:
        rows: Final report rows.

    Returns:
        Multi-line digest string.
    """
    if not rows:
        return "Data Deficiency Warning: No report rows available."

    lines = ["📊 Bharat Market Pulse", ""]
    for row in rows:
        lines.append(f"• {row.ticker}: {row.action} (confidence {row.confidence:.2f})")
        lines.append(f"  Sentiment: {row.sentiment}")
        lines.append(f"  In simple words: {row.layman_summary}")
        if row.warning:
            lines.append(f"  ⚠️ {row.warning}")
        lines.append("")

    return "\n".join(lines).strip()
