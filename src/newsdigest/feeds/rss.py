import logging
from datetime import datetime
from time import mktime

import feedparser

from newsdigest.config import FeedConfig
from newsdigest.feeds.base import FeedSource
from newsdigest.models import Article

logger = logging.getLogger(__name__)


class RSSFeedSource(FeedSource):
    """Fetch articles from an RSS/Atom feed."""

    def __init__(self, config: FeedConfig) -> None:
        super().__init__(config)

    def fetch(self) -> list[Article]:
        logger.info("Fetching RSS feed: %s (%s)", self.config.name, self.config.url)
        feed = feedparser.parse(self.config.url)

        if feed.bozo and not feed.entries:
            logger.warning(
                "Failed to parse feed %s: %s", self.config.name, feed.bozo_exception
            )
            return []

        articles: list[Article] = []
        for entry in feed.entries:
            url = entry.get("link", "")
            if not url:
                continue

            published = _parse_published(entry)
            summary = _extract_summary(entry)

            articles.append(
                Article(
                    url=url,
                    title=entry.get("title", "(no title)"),
                    source=self.config.name,
                    category=self.config.category,
                    published=published,
                    summary=summary,
                )
            )

        logger.info("Fetched %d articles from %s", len(articles), self.config.name)
        return articles


def _parse_published(entry: feedparser.FeedParserDict) -> datetime | None:
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed:
        try:
            return datetime.fromtimestamp(mktime(published_parsed))
        except (ValueError, OverflowError):
            return None
    return None


def _extract_summary(entry: feedparser.FeedParserDict) -> str | None:
    summary = entry.get("summary", "") or entry.get("description", "")
    if not summary:
        return None
    # Strip HTML tags simply for the summary preview
    import re

    clean = re.sub(r"<[^>]+>", "", summary)
    clean = clean.strip()
    return clean[:200] if clean else None
