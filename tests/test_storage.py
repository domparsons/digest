from datetime import datetime

from newsdigest.models import Article
from newsdigest.storage import ArticleStore


def _make_article(url: str = "https://example.com/1", title: str = "Test") -> Article:
    return Article(
        url=url,
        title=title,
        source="Test Source",
        category="test",
        published=datetime(2024, 1, 1),
        summary="A test article",
    )


def test_filter_new_all_new():
    store = ArticleStore(":memory:")
    articles = [_make_article("https://example.com/1"), _make_article("https://example.com/2")]
    result = store.filter_new(articles)
    assert len(result) == 2


def test_filter_new_excludes_seen():
    store = ArticleStore(":memory:")
    a1 = _make_article("https://example.com/1")
    store.mark_seen([a1])

    articles = [a1, _make_article("https://example.com/2")]
    result = store.filter_new(articles)
    assert len(result) == 1
    assert result[0].url == "https://example.com/2"


def test_filter_new_empty_input():
    store = ArticleStore(":memory:")
    assert store.filter_new([]) == []


def test_mark_seen_idempotent():
    store = ArticleStore(":memory:")
    a1 = _make_article("https://example.com/1")
    store.mark_seen([a1])
    store.mark_seen([a1])  # Should not raise
    assert len(store.recent()) == 1


def test_recent_returns_ordered():
    store = ArticleStore(":memory:")
    a1 = _make_article("https://example.com/1", "First")
    a2 = _make_article("https://example.com/2", "Second")
    store.mark_seen([a1])
    store.mark_seen([a2])

    rows = store.recent(limit=10)
    assert len(rows) == 2
    assert rows[0]["title"] == "Second"  # Most recent first


def test_recent_respects_limit():
    store = ArticleStore(":memory:")
    articles = [_make_article(f"https://example.com/{i}") for i in range(5)]
    store.mark_seen(articles)

    rows = store.recent(limit=3)
    assert len(rows) == 3
