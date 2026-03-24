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
