from newsdigest.feeds.base import FeedSource
from newsdigest.models import Article


class ScraperFeedSource(FeedSource):
    """Placeholder for HTML scraping feed source. Not implemented in v1."""

    def fetch(self) -> list[Article]:
        raise NotImplementedError(
            f"HTML scraping is not implemented yet. Feed: {self.config.name}"
        )
