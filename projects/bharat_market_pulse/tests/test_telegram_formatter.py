from analyzer import AnalysisRow
from telegram_formatter import format_telegram_digest


def test_telegram_digest_non_empty():
    rows = [
        AnalysisRow(
            ticker="INFY",
            sentiment="Global=Bearish | India=Bullish | Divergence Opportunity",
            global_context="Global risk-off may pressure IT exports.",
            action="Hold",
        )
    ]
    digest = format_telegram_digest(rows)
    assert "INFY" in digest
    assert "Bharat Market Pulse" in digest
