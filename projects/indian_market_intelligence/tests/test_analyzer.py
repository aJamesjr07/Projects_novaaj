from analyzer import AnalysisRow, build_report_rows
from data_fetcher import FeedItem
from ocr_engine import Holding


def test_build_report_rows_deficiency_warning():
    rows = build_report_rows([], [])
    assert len(rows) == 1
    assert rows[0].warning == "Data Deficiency Warning"


def test_build_report_rows_with_data():
    holdings = [Holding(ticker="TCS", quantity=10, confidence=0.95)]
    items = [
        FeedItem(
            source="news",
            author="sample",
            text="Fed rate hike and recession fear rises while India GDP growth remains strong",
            url="https://example.com",
            created_at="2026-03-19T00:00:00Z",
            metadata={},
        )
    ]

    rows = build_report_rows(holdings, items)
    assert len(rows) == 1
    assert rows[0].ticker == "TCS"
    assert rows[0].action in {"Buy", "Hold", "Sell", "Hold (Divergence Opportunity)"}
