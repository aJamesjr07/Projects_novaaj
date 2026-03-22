"""Phase S1: trusted seed-news collection for predictive sandbox.

Collects and tags high-quality market news for downstream simulation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .data_fetcher import (
    FeedItem,
    fetch_global_event_items,
    fetch_news_items,
    fetch_official_rss_items,
)


LOG_PATH = Path(__file__).resolve().parent / "logs" / "system_errors.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


@dataclass(frozen=True)
class SeedNews:
    """High-quality news item used as simulation seed."""

    title: str
    source: str
    url: str
    tag: str
    reliability: float


def _tag_text(text: str) -> str:
    t = text.lower()
    if any(k in t for k in {"repo", "rbi", "policy", "mpc"}):
        return "policy"
    if any(k in t for k in {"results", "earnings", "guidance", "order"}):
        return "company"
    if any(k in t for k in {"oil", "crude", "yields", "fed", "inflation", "dollar"}):
        return "macro"
    if any(k in t for k in {"metal", "pharma", "defence", "bank", "it"}):
        return "sector"
    return "market"


def _to_seed(item: FeedItem) -> SeedNews:
    title = item.text.split("\n", 1)[0].strip() or item.text.strip()
    return SeedNews(
        title=title,
        source=f"{item.author} ({item.source})",
        url=item.url,
        tag=_tag_text(item.text),
        reliability=float(item.metadata.get("reliability", "0.5")),
    )


def collect_seed_news(limit: int = 12) -> List[SeedNews]:
    """Collect high-quality seed news from official + trusted news sources.

    Args:
        limit: Max returned seed items.

    Returns:
        Ranked list of SeedNews for simulation.
    """
    try:
        raw: List[FeedItem] = []
        raw.extend(fetch_official_rss_items(limit_per_feed=10))
        raw.extend(fetch_news_items(page_size=30))
        raw.extend(fetch_global_event_items(page_size=20))

        trusted = [i for i in raw if i.source in {"official", "news"} and i.url]
        ranked = sorted(
            trusted,
            key=lambda x: float(x.metadata.get("reliability", "0.5")),
            reverse=True,
        )

        seeds: List[SeedNews] = []
        seen_titles: set[str] = set()
        for item in ranked:
            seed = _to_seed(item)
            key = seed.title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            seeds.append(seed)
            if len(seeds) >= limit:
                break

        logging.info("Collected %d seed news items.", len(seeds))
        return seeds
    except Exception as exc:
        logging.exception("news_collector failed: %s", exc)
        return []


if __name__ == "__main__":
    seeds = collect_seed_news()
    print(f"Collected {len(seeds)} seed items")
    for s in seeds[:5]:
        print(f"- [{s.tag}] {s.title} | {s.source}")
