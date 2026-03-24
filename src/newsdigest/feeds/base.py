from abc import ABC, abstractmethod

from newsdigest.config import FeedConfig
from newsdigest.models import Article


class FeedSource(ABC):
    """Abstract base class for feed sources."""

    def __init__(self, config: FeedConfig) -> None:
        self.config = config

    @abstractmethod
    def fetch(self) -> list[Article]:
        """Fetch articles from this feed source."""
        ...
