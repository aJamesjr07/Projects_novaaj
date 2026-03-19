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
        report_output_dir: Directory for generated report artifacts.
    """

    x_bearer_token: str
    news_api_key: str
    market_report_image_path: str
    report_output_dir: Path


def get_settings() -> Settings:
    """Build settings object from environment variables.

    Returns:
        Settings dataclass populated from .env or process environment.
    """
    return Settings(
        x_bearer_token=os.getenv("X_BEARER_TOKEN", ""),
        news_api_key=os.getenv("NEWS_API_KEY", ""),
        market_report_image_path=os.getenv("MARKET_REPORT_IMAGE_PATH", "portfolio.png"),
        report_output_dir=Path(os.getenv("REPORT_OUTPUT_DIR", "./reports")),
    )
