from bharat_market_pulse.config import get_settings, resolve_image_paths


def test_config_loads_defaults(monkeypatch):
    monkeypatch.delenv("USE_LLM_FIRST", raising=False)
    monkeypatch.delenv("USE_AGENT_EXTRACT_FIRST", raising=False)
    monkeypatch.delenv("MARKET_REPORT_IMAGE_PATH", raising=False)
    monkeypatch.delenv("MARKET_REPORT_IMAGE_PATHS", raising=False)

    settings = get_settings()
    assert settings is not None
    assert settings.use_llm_first is True
    assert settings.use_agent_extract_first is True
    assert settings.market_report_image_path == "portfolio.png"


def test_boolean_parsing(monkeypatch):
    monkeypatch.setenv("USE_LLM_FIRST", "off")
    monkeypatch.setenv("USE_AGENT_EXTRACT_FIRST", "0")
    settings = get_settings()
    assert settings.use_llm_first is False
    assert settings.use_agent_extract_first is False


def test_image_path_resolution(monkeypatch):
    monkeypatch.setenv("MARKET_REPORT_IMAGE_PATHS", "a.png, b.png , ,c.png")
    settings = get_settings()
    assert resolve_image_paths(settings) == ["a.png", "b.png", "c.png"]
