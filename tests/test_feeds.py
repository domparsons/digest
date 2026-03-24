from pathlib import Path

from newsdigest.config import FeedConfig
from newsdigest.feeds.rss import RSSFeedSource

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_feed.xml"


def _make_source(url: str = "") -> RSSFeedSource:
    config = FeedConfig(name="Test Feed", url=url, type="rss", category="test")
    return RSSFeedSource(config)


def test_parse_rss_fixture():
    source = _make_source(url=str(FIXTURE_PATH))
    articles = source.fetch()

    assert len(articles) == 3
    assert articles[0].title == "First Article"
    assert articles[0].url == "https://example.com/article-1"
    assert articles[0].source == "Test Feed"
    assert articles[0].category == "test"
    assert articles[0].published is not None


def test_html_stripped_from_summary():
    source = _make_source(url=str(FIXTURE_PATH))
    articles = source.fetch()

    second = articles[1]
    assert "<" not in (second.summary or "")
    assert "HTML content in description" in (second.summary or "")


def test_article_without_date():
    source = _make_source(url=str(FIXTURE_PATH))
    articles = source.fetch()

    third = articles[2]
    assert third.published is None


def test_bad_feed_returns_empty():
    source = _make_source(url="file:///nonexistent/feed.xml")
    articles = source.fetch()
    assert articles == []
