from bharat_market_pulse.analyzer import AnalysisBundle, AnalysisRow
from bharat_market_pulse.report_pipeline import render_report


def test_render_pipeline_output_contains_header():
    row = AnalysisRow(
        ticker="INFY",
        sentiment="Global=Neutral | India=Bullish",
        global_context="Stable",
        action="Hold",
        confidence=0.8,
        layman_summary="Watch and hold.",
        citations=["https://example.com"],
    )
    bundle = AnalysisBundle(rows=[row], global_events=["Fed pauses"])
    out = render_report(bundle)
    assert "Bharat Market Pulse - Daily Report" in out
