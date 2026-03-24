from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from newsdigest.models import Article

_DATE_MIN = datetime.min


class TerminalOutput:
    """Render a digest to the terminal using rich."""

    def __init__(self) -> None:
        self.console = Console()

    def render(self, articles: list[Article], *, title: str = "News Digest") -> None:
        if not articles:
            self.console.print("[dim]No new articles.[/dim]")
            return

        self.console.print()
        self.console.rule(f"[bold]{title}[/bold]")
        self.console.print()

        # Group by source, then sort by date (newest first) within each
        by_source: dict[str, list[Article]] = {}
        for article in articles:
            by_source.setdefault(article.source, []).append(article)

        for source, source_articles in by_source.items():
            source_articles.sort(key=lambda a: a.published or _DATE_MIN, reverse=True)
            self.console.print(f"[bold cyan]{source}[/bold cyan]")
            self.console.print()

            for article in source_articles:
                title_text = Text(article.title, style="bold")
                meta_parts: list[str] = []
                if article.category:
                    meta_parts.append(article.category)
                if article.published:
                    meta_parts.append(article.published.strftime("%Y-%m-%d %H:%M"))
                meta = " · ".join(meta_parts)

                body = ""
                if meta:
                    body = f"[dim]{meta}[/dim]\n"
                body += f"[link={article.url}]{article.url}[/link]"
                if article.summary:
                    body += f"\n{article.summary}"

                self.console.print(Panel(body, title=title_text, title_align="left"))

            self.console.print()

        self.console.rule(f"[dim]{len(articles)} new article(s)[/dim]")
        self.console.print()
