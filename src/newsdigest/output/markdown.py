from datetime import datetime
from pathlib import Path

from newsdigest.models import Article, RankedArticle

_TIER_ORDER = ["highlight", "notable", "routine"]
_TIER_LABELS = {"highlight": "Highlights", "notable": "Notable", "routine": "Routine"}


class MarkdownOutput:
    """Write a digest to a Markdown file."""

    def __init__(self, directory: str) -> None:
        self.directory = Path(directory).expanduser()

    def render(self, articles: list[Article]) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        filename = f"digest-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        filepath = self.directory / filename

        lines: list[str] = [f"# News Digest — {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]

        if not articles:
            lines.append("No new articles.")
        else:
            by_category: dict[str, list[Article]] = {}
            for article in articles:
                key = article.category or "Uncategorised"
                by_category.setdefault(key, []).append(article)

            for category, cat_articles in by_category.items():
                lines.append(f"## {category.title()}")
                lines.append("")
                for article in cat_articles:
                    lines.extend(self._article_lines(article))

        lines.append(f"---\n*{len(articles)} new article(s)*\n")
        filepath.write_text("\n".join(lines))
        return filepath

    def render_ranked(self, ranked: list[RankedArticle]) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        filename = f"digest-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        filepath = self.directory / filename

        lines: list[str] = [f"# News Digest — {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]

        if not ranked:
            lines.append("No new articles.")
        else:
            by_tier: dict[str, list[RankedArticle]] = {t: [] for t in _TIER_ORDER}
            for ra in ranked:
                by_tier.setdefault(ra.tier, []).append(ra)

            total = 0
            for tier in _TIER_ORDER:
                tier_articles = sorted(by_tier[tier], key=lambda r: r.score, reverse=True)
                if not tier_articles:
                    continue
                lines.append(f"## {_TIER_LABELS.get(tier, tier.title())}")
                lines.append("")
                for ra in tier_articles:
                    lines.extend(self._ranked_article_lines(ra))
                total += len(tier_articles)

            lines.append(f"---\n*{total} article(s)*\n")

        filepath.write_text("\n".join(lines))
        return filepath

    def _article_lines(self, article: Article) -> list[str]:
        meta_parts: list[str] = [article.source]
        if article.published:
            meta_parts.append(article.published.strftime("%Y-%m-%d %H:%M"))
        meta = " · ".join(meta_parts)
        lines = [f"### [{article.title}]({article.url})", f"*{meta}*"]
        if article.summary:
            lines += ["", f"> {article.summary}"]
        lines.append("")
        return lines

    def _ranked_article_lines(self, ra: RankedArticle) -> list[str]:
        article = ra.article
        meta_parts: list[str] = [article.source]
        if article.category:
            meta_parts.append(article.category)
        if article.published:
            meta_parts.append(article.published.strftime("%Y-%m-%d %H:%M"))
        meta = " · ".join(meta_parts)
        lines = [f"### [{article.title}]({article.url})", f"*{meta}*"]
        if ra.summary and ra.summary.strip().lower() != article.title.strip().lower():
            lines += ["", f"> {ra.summary}"]
        lines.append("")
        return lines
