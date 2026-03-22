from bharat_market_pulse.analyzer import AnalysisBundle, AnalysisRow
from bharat_market_pulse.report_pipeline import main, render_report


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
    assert "not financial advice" in out.lower()


def test_render_report_with_empty_inputs():
    bundle = AnalysisBundle(rows=[], global_events=[])
    out = render_report(bundle)
    assert "Data Deficiency Warning" in out


def test_main_degraded_mode_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("MARKET_REPORT_IMAGE_PATH", "")
    monkeypatch.setenv("MARKET_REPORT_IMAGE_PATHS", "")
    monkeypatch.setenv("USE_AGENT_EXTRACT_FIRST", "false")
    monkeypatch.setenv("USE_LLM_FIRST", "false")

    # Degraded, deterministic stubs.
    monkeypatch.setattr("bharat_market_pulse.report_pipeline.fetch_all_sources", lambda: [])
    monkeypatch.setattr(
        "bharat_market_pulse.report_pipeline.collect_seed_news", lambda limit=10: []
    )

    main()

    output_dir = tmp_path / "reports"
    assert output_dir.exists()
    assert any(p.suffix == ".md" for p in output_dir.iterdir())
