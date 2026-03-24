from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Article:
    url: str
    title: str
    source: str
    category: str
    published: datetime | None
    summary: str | None


@dataclass(frozen=True)
class RankedArticle:
    article: Article
    tier: str   # "highlight", "notable", "routine"
    score: int  # 1-100, higher is more relevant
    summary: str  # LLM-generated one-line summary
