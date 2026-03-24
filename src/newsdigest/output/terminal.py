from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from newsdigest.models import Article, RankedArticle

_DATE_MIN = datetime.min

_TIER_ORDER = ["highlight", "notable", "routine"]
_TIER_LABELS = {
    "highlight": "★  HIGHLIGHTS",
    "notable": "NOTABLE",
    "routine": "ROUTINE",
}
_TIER_BORDER = {
    "highlight": "yellow",
    "notable": "default",
    "routine": "dim",
}


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

        by_source: dict[str, list[Article]] = {}
        for article in articles:
            by_source.setdefault(article.source, []).append(article)

        for source, source_articles in by_source.items():
            source_articles.sort(key=lambda a: a.published or _DATE_MIN, reverse=True)
            self.console.print(f"[bold cyan]{source}[/bold cyan]")
            self.console.print()

            for article in source_articles:
                self.console.print(self._article_panel(article))

            self.console.print()

        self.console.rule(f"[dim]{len(articles)} new article(s)[/dim]")
        self.console.print()

    def render_ranked(
        self,
        ranked: list[RankedArticle],
        *,
        title: str = "News Digest",
        warnings: list[str] | None = None,
    ) -> None:
        if not ranked:
            self.console.print("[dim]No new articles.[/dim]")
            return

        self.console.print()
        self.console.rule(f"[bold]{title}[/bold]")

        by_tier: dict[str, list[RankedArticle]] = {t: [] for t in _TIER_ORDER}
        for ra in ranked:
            by_tier.setdefault(ra.tier, []).append(ra)

        total = 0
        for tier in _TIER_ORDER:
            tier_articles = sorted(by_tier[tier], key=lambda r: r.score, reverse=True)
            if not tier_articles:
                continue

            label = _TIER_LABELS.get(tier, tier.upper())
            self.console.print()
            if tier == "highlight":
                self.console.print(f"[bold yellow]{label}[/bold yellow]")
            else:
                self.console.print(f"[bold]{label}[/bold]")
            self.console.print()

            for ra in tier_articles:
                self.console.print(self._ranked_panel(ra))

            total += len(tier_articles)

        self.console.print()
        self.console.rule(f"[dim]{total} article(s)[/dim]")

        if warnings:
            self.console.print()
            self.console.print("[dim]Ranking unavailable for some providers:[/dim]")
            for w in warnings:
                self.console.print(f"  [dim]• {w}[/dim]")

        self.console.print()

    # -- internal helpers --

    def _article_panel(self, article: Article, border_style: str = "default") -> Panel:
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

        return Panel(body, title=title_text, title_align="left", border_style=border_style)

    def _ranked_panel(self, ra: RankedArticle) -> Panel:
        border = _TIER_BORDER.get(ra.tier, "default")
        article = ra.article
        title_text = Text(article.title, style="bold")

        meta_parts: list[str] = [article.source]
        if article.category:
            meta_parts.append(article.category)
        if article.published:
            meta_parts.append(article.published.strftime("%Y-%m-%d %H:%M"))
        meta = " · ".join(meta_parts)

        body = f"[dim]{meta}[/dim]\n"
        body += f"[link={article.url}]{article.url}[/link]"
        # Show LLM summary only when it differs meaningfully from the title
        if ra.summary and ra.summary.strip().lower() != article.title.strip().lower():
            body += f"\n{ra.summary}"

        return Panel(body, title=title_text, title_align="left", border_style=border)
