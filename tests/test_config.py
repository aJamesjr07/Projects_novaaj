from bharat_market_pulse.config import get_settings


def test_get_settings_defaults(monkeypatch):
    monkeypatch.delenv("USE_LLM_FIRST", raising=False)
    monkeypatch.delenv("USE_AGENT_EXTRACT_FIRST", raising=False)
    s = get_settings()
    assert s.use_llm_first is True
    assert s.use_agent_extract_first is True
    assert str(s.report_output_dir) == "reports"
