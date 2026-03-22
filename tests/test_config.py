from bharat_market_pulse.config import get_settings

def test_config_loads():
    settings = get_settings()
    assert settings is not None
