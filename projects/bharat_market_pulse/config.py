"""Configuration loader for Bharat Market Pulse.

Runtime hardening goals:
- predictable boolean parsing
- safe defaults for optional settings
- graceful behavior when optional credentials are missing
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover

    def load_dotenv() -> bool:
        return False


load_dotenv()

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class Settings:
    """Application runtime settings."""

    x_bearer_token: str
    news_api_key: str
    market_report_image_path: str
    market_report_image_paths: str
    report_output_dir: Path
    use_agent_extract_first: bool
    agent_extract_file_path: str
    use_llm_first: bool
    llm_api_key: str
    llm_model: str
    llm_base_url: str
    llm_timeout_seconds: int


def _parse_bool(value: str | None, default: bool) -> bool:
    """Parse a bool-like env value with explicit, predictable rules."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


def _parse_int(value: str | None, default: int, minimum: int | None = None) -> int:
    """Parse integer env value safely with optional minimum bound."""
    try:
        parsed = int((value or "").strip())
    except (TypeError, ValueError):
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def get_settings() -> Settings:
    """Build settings object from environment variables."""
    return Settings(
        x_bearer_token=os.getenv("X_BEARER_TOKEN", "").strip(),
        news_api_key=os.getenv("NEWS_API_KEY", "").strip(),
        market_report_image_path=os.getenv("MARKET_REPORT_IMAGE_PATH", "portfolio.png").strip(),
        market_report_image_paths=os.getenv("MARKET_REPORT_IMAGE_PATHS", "").strip(),
        report_output_dir=Path(os.getenv("REPORT_OUTPUT_DIR", "reports").strip() or "reports"),
        use_agent_extract_first=_parse_bool(os.getenv("USE_AGENT_EXTRACT_FIRST"), True),
        agent_extract_file_path=os.getenv("AGENT_EXTRACT_FILE_PATH", "./agent_extracted_holdings.json").strip(),
        use_llm_first=_parse_bool(os.getenv("USE_LLM_FIRST"), True),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip() or "https://api.openai.com/v1",
        llm_timeout_seconds=_parse_int(os.getenv("LLM_TIMEOUT_SECONDS"), default=45, minimum=1),
    )


def resolve_image_paths(settings: Settings) -> list[str]:
    """Resolve one or more candidate image paths from settings.

    Returns only non-empty path strings; existence is validated by callers.
    """
    paths = [p.strip() for p in settings.market_report_image_paths.split(",") if p.strip()]
    if paths:
        return paths
    if settings.market_report_image_path.strip():
        return [settings.market_report_image_path.strip()]
    return []
