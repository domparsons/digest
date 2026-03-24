import sqlite3
from datetime import datetime
from pathlib import Path

from newsdigest.models import Article

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_articles (
    url TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    published TEXT,
    first_seen TEXT NOT NULL
);
"""


class ArticleStore:
    """SQLite-backed store for tracking seen articles."""

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        if isinstance(db_path, Path):
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(db_path))
        else:
            self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def filter_new(self, articles: list[Article]) -> list[Article]:
        """Return only articles that have not been seen before."""
        if not articles:
            return []
        urls = {a.url for a in articles}
        placeholders = ",".join("?" for _ in urls)
        cursor = self._conn.execute(
            f"SELECT url FROM seen_articles WHERE url IN ({placeholders})",
            list(urls),
        )
        seen_urls = {row[0] for row in cursor.fetchall()}
        return [a for a in articles if a.url not in seen_urls]

    def mark_seen(self, articles: list[Article]) -> None:
        """Record articles as seen."""
        now = datetime.now().isoformat()
        self._conn.executemany(
            "INSERT OR IGNORE INTO seen_articles "
            "(url, title, source, category, published, first_seen) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    a.url,
                    a.title,
                    a.source,
                    a.category,
                    a.published.isoformat() if a.published else None,
                    now,
                )
                for a in articles
            ],
        )
        self._conn.commit()

    def recent(self, limit: int = 20) -> list[dict[str, str | None]]:
        """Return the most recently seen articles."""
        cursor = self._conn.execute(
            "SELECT url, title, source, category, published, first_seen "
            "FROM seen_articles ORDER BY first_seen DESC LIMIT ?",
            (limit,),
        )
        return [
            {
                "url": row[0],
                "title": row[1],
                "source": row[2],
                "category": row[3],
                "published": row[4],
                "first_seen": row[5],
            }
            for row in cursor.fetchall()
        ]

    def since(self, since: datetime) -> list[dict[str, str | None]]:
        """Return articles published on or after the given datetime.

        Only includes articles with a known published date — articles without
        one are excluded since we can't reliably place them in time.
        """
        cursor = self._conn.execute(
            "SELECT url, title, source, category, published, first_seen "
            "FROM seen_articles WHERE published IS NOT NULL AND published >= ? "
            "ORDER BY published DESC",
            (since.isoformat(),),
        )
        return [
            {
                "url": row[0],
                "title": row[1],
                "source": row[2],
                "category": row[3],
                "published": row[4],
                "first_seen": row[5],
            }
            for row in cursor.fetchall()
        ]

    def close(self) -> None:
        self._conn.close()
