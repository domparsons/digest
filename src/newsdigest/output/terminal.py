from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from newsdigest.models import Article


class TerminalOutput:
    """Render a digest to the terminal using rich."""

    def __init__(self) -> None:
        self.console = Console()

    def render(self, articles: list[Article]) -> None:
        if not articles:
            self.console.print("[dim]No new articles.[/dim]")
            return

        self.console.print()
        self.console.rule("[bold]News Digest[/bold]")
        self.console.print()

        # Group by category
        by_category: dict[str, list[Article]] = {}
        for article in articles:
            key = article.category or "Uncategorised"
            by_category.setdefault(key, []).append(article)

        for category, cat_articles in by_category.items():
            self.console.print(f"[bold cyan]{category.upper()}[/bold cyan]")
            self.console.print()

            for article in cat_articles:
                title_text = Text(article.title, style="bold")
                meta_parts: list[str] = [article.source]
                if article.published:
                    meta_parts.append(article.published.strftime("%Y-%m-%d %H:%M"))
                meta = " · ".join(meta_parts)

                body = f"[dim]{meta}[/dim]\n[link={article.url}]{article.url}[/link]"
                if article.summary:
                    body += f"\n{article.summary}"

                self.console.print(Panel(body, title=title_text, title_align="left"))

            self.console.print()

        self.console.rule(f"[dim]{len(articles)} new article(s)[/dim]")
        self.console.print()
