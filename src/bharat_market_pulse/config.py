"""Configuration loader for the Indian Market Intelligence pipeline."""

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


@dataclass(frozen=True)
class Settings:
    """Application runtime settings.

    Attributes:
        x_bearer_token: X/Twitter API bearer token.
        news_api_key: News API key.
        market_report_image_path: Path to input portfolio screenshot.
        market_report_image_paths: Optional comma-separated list of screenshot paths.
        report_output_dir: Directory for generated report artifacts.
        use_agent_extract_first: Use agent-extracted local JSON before other methods.
        agent_extract_file_path: JSON file path containing extracted holdings.
        use_llm_first: Enable LLM-first extraction before OCR fallback.
        llm_api_key: API key for vision model provider.
        llm_model: Vision model id.
        llm_base_url: OpenAI-compatible base URL.
        llm_timeout_seconds: LLM request timeout.
    """

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


def get_settings() -> Settings:
    """Build settings object from environment variables.

    Returns:
        Settings dataclass populated from .env or process environment.
    """
    use_llm_first = os.getenv("USE_LLM_FIRST", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    use_agent_extract_first = os.getenv(
        "USE_AGENT_EXTRACT_FIRST", "true"
    ).strip().lower() in {"1", "true", "yes", "on"}

    return Settings(
        x_bearer_token=os.getenv("X_BEARER_TOKEN", ""),
        news_api_key=os.getenv("NEWS_API_KEY", ""),
        market_report_image_path=os.getenv("MARKET_REPORT_IMAGE_PATH", "portfolio.png"),
        market_report_image_paths=os.getenv("MARKET_REPORT_IMAGE_PATHS", ""),
        report_output_dir=Path(os.getenv("REPORT_OUTPUT_DIR", "./reports")),
        use_agent_extract_first=use_agent_extract_first,
        agent_extract_file_path=os.getenv(
            "AGENT_EXTRACT_FILE_PATH", "./agent_extracted_holdings.json"
        ),
        use_llm_first=use_llm_first,
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "45")),
    )
