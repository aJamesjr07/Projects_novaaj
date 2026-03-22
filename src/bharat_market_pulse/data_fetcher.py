"""Data fetcher for Bharat Market Pulse sources (social, news, official feeds)."""

from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List

import requests

from .config import get_settings

logger = logging.getLogger(__name__)

TWITTER_PILLARS = [
    "deepakshenoy",
    "SamirArora",
    "Indiacharts",
    "CNBCTV18Live",
]

REDDIT_PILLARS = [
    "IndiaInvestments",
    "IndianStreetBets",
]

SOURCE_RELIABILITY = {
    "official": 0.96,
    "news": 0.82,
    "twitter": 0.50,
    "reddit": 0.38,
}


@dataclass
class FeedItem:
    source: str
    author: str
    text: str
    url: str
    created_at: str
    metadata: Dict[str, str]


def with_exponential_backoff(
    fn: Callable[[], requests.Response],
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
) -> requests.Response:
    """Execute an HTTP call with exponential backoff on rate limits."""
    delay = initial_delay
    for attempt in range(max_retries + 1):
        response = fn()
        if response.status_code != 429:
            response.raise_for_status()
            return response

        if attempt == max_retries:
            response.raise_for_status()

        retry_after = response.headers.get("Retry-After")
        sleep_for = float(retry_after) if retry_after else delay
        time.sleep(min(sleep_for, max_delay))
        delay = min(delay * 2, max_delay)

    raise requests.HTTPError("Unexpected backoff control flow.")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_low_quality_news_text(text: str) -> bool:
    t = (text or "").strip().lower()
    if len(t) < 35:
        return True
    noisy_patterns = [
        r"advice thread",
        r"daily discussion",
        r"click here",
        r"sponsored",
        r"subscribe now",
        r"market wrap(?!.*(nifty|sensex|rbi|policy))",
    ]
    return any(re.search(p, t) for p in noisy_patterns)


def _make_item(
    source: str, author: str, text: str, url: str, created_at: str, **metadata: str
) -> FeedItem:
    reliability = SOURCE_RELIABILITY.get(source, 0.5)
    payload = {
        "reliability": f"{reliability:.2f}",
        **{k: str(v) for k, v in metadata.items()},
    }
    return FeedItem(
        source=source,
        author=author,
        text=text,
        url=url,
        created_at=created_at,
        metadata=payload,
    )


def fetch_twitter_items(limit_per_account: int = 5) -> List[FeedItem]:
    bearer_token = get_settings().x_bearer_token
    if not bearer_token:
        logger.info("X_BEARER_TOKEN not configured; skipping Twitter fetch.")
        return []

    headers = {"Authorization": f"Bearer {bearer_token}"}
    items: List[FeedItem] = []

    for username in TWITTER_PILLARS:
        user_url = f"https://api.twitter.com/2/users/by/username/{username}"
        user_resp = with_exponential_backoff(
            lambda: requests.get(user_url, headers=headers, timeout=15)
        )
        user_id = user_resp.json().get("data", {}).get("id")
        if not user_id:
            continue

        tweets_url = (
            f"https://api.twitter.com/2/users/{user_id}/tweets"
            f"?max_results={max(5, min(100, limit_per_account))}&tweet.fields=created_at"
        )
        tweets_resp = with_exponential_backoff(
            lambda: requests.get(tweets_url, headers=headers, timeout=15)
        )
        tweets_data = tweets_resp.json().get("data", [])

        for t in tweets_data[:limit_per_account]:
            tweet_id = t.get("id", "")
            text = t.get("text", "")
            if not text:
                continue
            items.append(
                _make_item(
                    source="twitter",
                    author=f"@{username}",
                    text=text,
                    url=f"https://x.com/{username}/status/{tweet_id}"
                    if tweet_id
                    else f"https://x.com/{username}",
                    created_at=t.get("created_at", _utc_now()),
                    pillar="indian_market",
                    region="india",
                )
            )

    return items


def fetch_reddit_items(limit_per_subreddit: int = 10) -> List[FeedItem]:
    headers = {"User-Agent": "bharat-market-pulse/1.0"}
    items: List[FeedItem] = []

    for sub in REDDIT_PILLARS:
        url = f"https://www.reddit.com/r/{sub}/new.json?limit={limit_per_subreddit}"
        resp = with_exponential_backoff(lambda: requests.get(url, headers=headers, timeout=15))
        children = resp.json().get("data", {}).get("children", [])

        for child in children:
            data = child.get("data", {})
            text = (data.get("title", "") + "\n" + data.get("selftext", "")).strip()
            if not text:
                continue
            created_utc = data.get("created_utc")
            created_at = (
                datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
                if created_utc
                else _utc_now()
            )
            permalink = data.get("permalink", "")

            items.append(
                _make_item(
                    source="reddit",
                    author=f"r/{sub}",
                    text=text,
                    url=f"https://reddit.com{permalink}"
                    if permalink
                    else f"https://reddit.com/r/{sub}",
                    created_at=created_at,
                    pillar="indian_market",
                    region="india",
                )
            )

    return items


def fetch_news_items(
    query: str = "India stock market OR RBI OR NSE OR BSE OR earnings OR results",
    page_size: int = 20,
) -> List[FeedItem]:
    api_key = get_settings().news_api_key
    if not api_key:
        logger.info("NEWS_API_KEY not configured; skipping market news fetch.")
        return []

    trusted_domains = (
        "economictimes.indiatimes.com,livemint.com,business-standard.com,moneycontrol.com,"
        "reuters.com,bloomberg.com,cnbctv18.com"
    )
    endpoint = (
        "https://newsapi.org/v2/everything"
        f"?q={query}&language=en&pageSize={page_size}&sortBy=publishedAt"
        f"&domains={trusted_domains}&apiKey={api_key}"
    )

    resp = with_exponential_backoff(lambda: requests.get(endpoint, timeout=20))
    articles = resp.json().get("articles", [])

    items: List[FeedItem] = []
    for article in articles:
        title = article.get("title", "")
        description = article.get("description", "")
        text = (title + "\n" + (description or "")).strip()
        if not text or _is_low_quality_news_text(text):
            continue
        items.append(
            _make_item(
                source="news",
                author=article.get("source", {}).get("name", "news"),
                text=text,
                url=article.get("url", ""),
                created_at=article.get("publishedAt", _utc_now()),
                pillar="indian_market",
                region="mixed",
            )
        )

    return items


def fetch_official_rss_items(limit_per_feed: int = 8) -> List[FeedItem]:
    feeds = [
        ("SEBI", "https://www.sebi.gov.in/sebirss.xml"),
    ]
    items: List[FeedItem] = []

    for author, url in feeds:
        try:
            resp = with_exponential_backoff(lambda: requests.get(url, timeout=20))
            root = ET.fromstring(resp.text)
            channel = root.find("channel")
            if channel is None:
                continue
            for item in channel.findall("item")[:limit_per_feed]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = (item.findtext("pubDate") or _utc_now()).strip()
                if not title:
                    continue
                items.append(
                    _make_item(
                        source="official",
                        author=author,
                        text=title,
                        url=link,
                        created_at=pub_date,
                        pillar="regulatory",
                        region="india",
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Official RSS fetch failed for %s: %s", author, exc)
            continue

    return items


def fetch_global_event_items(page_size: int = 10) -> List[FeedItem]:
    api_key = get_settings().news_api_key
    if not api_key:
        logger.info("NEWS_API_KEY not configured; skipping global event fetch.")
        return []

    query = 'Fed OR "US inflation" OR "US jobs" OR "crude oil" OR "dollar index" OR "bond yields" OR "US treasury yields"'
    trusted_domains = "reuters.com,bloomberg.com,cnbc.com,ft.com,wsj.com"
    endpoint = (
        "https://newsapi.org/v2/everything"
        f"?q={query}&language=en&pageSize={page_size}&sortBy=publishedAt"
        f"&domains={trusted_domains}&apiKey={api_key}"
    )

    resp = with_exponential_backoff(lambda: requests.get(endpoint, timeout=20))
    articles = resp.json().get("articles", [])

    items: List[FeedItem] = []
    for article in articles:
        title = article.get("title", "")
        description = article.get("description", "")
        text = (title + "\n" + (description or "")).strip()
        if not text or _is_low_quality_news_text(text):
            continue
        items.append(
            _make_item(
                source="news",
                author=article.get("source", {}).get("name", "global_news"),
                text=text,
                url=article.get("url", ""),
                created_at=article.get("publishedAt", _utc_now()),
                pillar="global_event",
                region="global",
            )
        )

    return items


def _safe_fetch(label: str, fn: Callable[[], List[FeedItem]]) -> List[FeedItem]:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s fetch failed; continuing degraded mode: %s", label, exc)
        return []


def fetch_all_sources() -> List[FeedItem]:
    """Fetch and combine all configured sources with graceful degradation."""
    items: List[FeedItem] = []
    official = _safe_fetch("official", fetch_official_rss_items)
    news = _safe_fetch("news", lambda: fetch_news_items(page_size=30))
    global_news = _safe_fetch("global_news", lambda: fetch_global_event_items(page_size=15))
    twitter = _safe_fetch("twitter", lambda: fetch_twitter_items(limit_per_account=2))
    reddit = _safe_fetch("reddit", lambda: fetch_reddit_items(limit_per_subreddit=2))

    items.extend(official)
    items.extend(news)
    items.extend(global_news)
    items.extend(twitter)
    items.extend(reddit[:4])
    return items


def main() -> None:
    items = fetch_all_sources()
    if not items:
        print("Data Deficiency Warning: No source items fetched. Check API keys / connectivity.")
        return

    counts: Dict[str, int] = {}
    for item in items:
        counts[item.source] = counts.get(item.source, 0) + 1

    print("Fetched items by source:")
    for src, count in counts.items():
        print(f"- {src}: {count}")


if __name__ == "__main__":
    main()
