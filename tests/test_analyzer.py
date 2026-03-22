from bharat_market_pulse.analyzer import score_global_sentiment
from bharat_market_pulse.data_fetcher import FeedItem


def test_score_global_sentiment_bearish():
    item = FeedItem(source="news", author="x", text="Fed hike and risk-off mood", url="u", published_at="", metadata={})
    assert score_global_sentiment([item]) < 0
