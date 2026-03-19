"""Data fetcher for Indian market intelligence sources (X/Twitter + Reddit + News)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional

import requests

from config import get_settings


TWITTER_PILLARS = [
    "deepakshenoy",      # Macro
    "SamirArora",        # Global/India sentiment
    "Indiacharts",       # Technical
    "CNBCTV18Live",      # Breaking News
]

REDDIT_PILLARS = [
    "IndiaInvestments",  # Fundamental
    "IndianStreetBets",  # Retail hype
]


@dataclass
class FeedItem:
    """Unified feed item object.

    Attributes:
        source: Origin source (twitter/reddit/news).
        author: Account/subreddit/agency identity.
        text: Post headline/body.
        url: Canonical link.
        created_at: UTC timestamp string.
        metadata: Optional source-specific metadata.
    """

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
    """Execute an HTTP call with exponential backoff on rate limits.

    Args:
        fn: Zero-argument function that executes and returns a Response.
        max_retries: Maximum retry attempts.
        initial_delay: Initial backoff delay in seconds.
        max_delay: Maximum delay cap in seconds.

    Returns:
        Successful HTTP response object.

    Raises:
        requests.HTTPError: If request still fails after retries.
    """
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
    """Return current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def fetch_twitter_items(limit_per_account: int = 5) -> List[FeedItem]:
    """Fetch latest posts from configured X/Twitter pillars.

    Args:
        limit_per_account: Number of posts to retrieve per account.

    Returns:
        List of FeedItem from pillar accounts.

    Notes:
        Requires X API bearer token in `X_BEARER_TOKEN` and a valid
        API tier with recent tweet read access.
    """
    bearer_token = get_settings().x_bearer_token
    if not bearer_token:
        return []

    headers = {"Authorization": f"Bearer {bearer_token}"}
    items: List[FeedItem] = []

    for username in TWITTER_PILLARS:
        # Step 1: Resolve user id.
        user_url = f"https://api.twitter.com/2/users/by/username/{username}"

        user_resp = with_exponential_backoff(lambda: requests.get(user_url, headers=headers, timeout=15))
        user_data = user_resp.json().get("data", {})
        user_id = user_data.get("id")
        if not user_id:
            continue

        # Step 2: Fetch latest tweets.
        tweets_url = (
            f"https://api.twitter.com/2/users/{user_id}/tweets"
            f"?max_results={max(5, min(100, limit_per_account))}&tweet.fields=created_at"
        )
        tweets_resp = with_exponential_backoff(lambda: requests.get(tweets_url, headers=headers, timeout=15))
        tweets_data = tweets_resp.json().get("data", [])

        for t in tweets_data[:limit_per_account]:
            tweet_id = t.get("id", "")
            text = t.get("text", "")
            created_at = t.get("created_at", _utc_now())
            if not text:
                continue
            items.append(
                FeedItem(
                    source="twitter",
                    author=f"@{username}",
                    text=text,
                    url=f"https://x.com/{username}/status/{tweet_id}" if tweet_id else f"https://x.com/{username}",
                    created_at=created_at,
                    metadata={"pillar": "indian_market"},
                )
            )

    return items


def fetch_reddit_items(limit_per_subreddit: int = 10) -> List[FeedItem]:
    """Fetch latest Reddit posts from configured pillar subreddits.

    Args:
        limit_per_subreddit: Number of recent hot/new posts to retrieve.

    Returns:
        List of FeedItem from Reddit.

    Notes:
        Uses Reddit public JSON endpoints for MVP read-only ingestion.
    """
    headers = {"User-Agent": "indian-market-intelligence-bot/1.0"}
    items: List[FeedItem] = []

    for sub in REDDIT_PILLARS:
        url = f"https://www.reddit.com/r/{sub}/new.json?limit={limit_per_subreddit}"
        resp = with_exponential_backoff(lambda: requests.get(url, headers=headers, timeout=15))
        children = resp.json().get("data", {}).get("children", [])

        for child in children:
            data = child.get("data", {})
            title = data.get("title", "")
            selftext = data.get("selftext", "")
            permalink = data.get("permalink", "")
            created_utc = data.get("created_utc")
            created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat() if created_utc else _utc_now()

            text = (title + "\n" + selftext).strip()
            if not text:
                continue

            items.append(
                FeedItem(
                    source="reddit",
                    author=f"r/{sub}",
                    text=text,
                    url=f"https://reddit.com{permalink}" if permalink else f"https://reddit.com/r/{sub}",
                    created_at=created_at,
                    metadata={"pillar": "indian_market"},
                )
            )

    return items


def fetch_news_items(query: str = "India stock market", page_size: int = 20) -> List[FeedItem]:
    """Fetch market-relevant news items from NewsAPI.

    Args:
        query: Query text for market filtering.
        page_size: Maximum number of articles.

    Returns:
        List of FeedItem from news API.

    Notes:
        Requires NEWS_API_KEY environment variable.
    """
    api_key = get_settings().news_api_key
    if not api_key:
        return []

    endpoint = (
        "https://newsapi.org/v2/everything"
        f"?q={query}&language=en&pageSize={page_size}&sortBy=publishedAt&apiKey={api_key}"
    )

    resp = with_exponential_backoff(lambda: requests.get(endpoint, timeout=20))
    articles = resp.json().get("articles", [])

    items: List[FeedItem] = []
    for article in articles:
        title = article.get("title", "")
        description = article.get("description", "")
        text = (title + "\n" + (description or "")).strip()
        if not text:
            continue
        items.append(
            FeedItem(
                source="news",
                author=article.get("source", {}).get("name", "news"),
                text=text,
                url=article.get("url", ""),
                created_at=article.get("publishedAt", _utc_now()),
                metadata={"pillar": "indian_market"},
            )
        )

    return items


def fetch_all_sources() -> List[FeedItem]:
    """Fetch and combine all configured social and news sources.

    Returns:
        Unified list of FeedItem objects from all active sources.
    """
    items: List[FeedItem] = []
    items.extend(fetch_twitter_items())
    items.extend(fetch_reddit_items())
    items.extend(fetch_news_items())
    return items


def main() -> None:
    """Run source fetch and print counts by source."""
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
