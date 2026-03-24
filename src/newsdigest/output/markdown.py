from datetime import datetime
from pathlib import Path

from newsdigest.models import Article


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
                    meta_parts: list[str] = [article.source]
                    if article.published:
                        meta_parts.append(article.published.strftime("%Y-%m-%d %H:%M"))
                    meta = " · ".join(meta_parts)

                    lines.append(f"### [{article.title}]({article.url})")
                    lines.append(f"*{meta}*")
                    if article.summary:
                        lines.append("")
                        lines.append(f"> {article.summary}")
                    lines.append("")

        lines.append(f"---\n*{len(articles)} new article(s)*\n")
        filepath.write_text("\n".join(lines))
        return filepath
