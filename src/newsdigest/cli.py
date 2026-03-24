import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import click

from newsdigest.config import Config, FeedConfig, default_config_path, load_config
from newsdigest.feeds.rss import RSSFeedSource
from newsdigest.models import Article, RankedArticle
from newsdigest.output.email import EmailOutput
from newsdigest.output.markdown import MarkdownOutput
from newsdigest.output.terminal import TerminalOutput
from newsdigest.ranking import rank_articles
from newsdigest.storage import ArticleStore

logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False),
    default=None,
    help="Path to config file (default: ~/.newsdigest/config.yaml)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--no-rank", is_flag=True, help="Skip LLM ranking even if configured")
@click.pass_context
def main(ctx: click.Context, config_path: str | None, verbose: bool, no_rank: bool) -> None:
    """News Digest — fetch, deduplicate, and deliver news articles."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = Path(config_path) if config_path else default_config_path()
    if ctx.invoked_subcommand is None:
        ctx.invoke(yesterday, blog=True, news=False, no_rank=no_rank)


@main.command()
@click.option("--blog", is_flag=True, help="Only fetch blog feeds")
@click.option("--news", is_flag=True, help="Only fetch news feeds")
@click.option("--no-rank", is_flag=True, help="Skip LLM ranking even if configured")
@click.pass_context
def fetch(ctx: click.Context, blog: bool, news: bool, no_rank: bool) -> None:
    """Fetch all feeds, deduplicate, and output via configured channels."""
    config = _load_config(ctx)
    feeds = _filter_feeds(config.feeds, blog=blog, news=news)
    store = ArticleStore(config.db_path)

    try:
        all_articles = _fetch_all_feeds(feeds)
        new_articles = store.filter_new(all_articles)
        store.mark_seen(new_articles)
        _deliver(config, new_articles, no_rank=no_rank)
    finally:
        store.close()


@main.command("list-feeds")
@click.pass_context
def list_feeds(ctx: click.Context) -> None:
    """Show configured feeds."""
    config = _load_config(ctx)
    terminal = TerminalOutput()
    terminal.console.print()
    for feed in config.feeds:
        cat = f" [{feed.category}]" if feed.category else ""
        terminal.console.print(f"  [bold]{feed.name}[/bold]{cat} ({feed.type})")
        terminal.console.print(f"    [dim]{feed.url}[/dim]")
    terminal.console.print()


@main.command()
@click.option("--limit", "-n", default=20, help="Number of recent articles to show")
@click.pass_context
def history(ctx: click.Context, limit: int) -> None:
    """Show recently seen articles."""
    config = _load_config(ctx)
    store = ArticleStore(config.db_path)

    try:
        rows = store.recent(limit)
        terminal = TerminalOutput()
        if not rows:
            terminal.console.print("[dim]No articles in history.[/dim]")
            return

        terminal.console.print()
        for row in rows:
            terminal.console.print(f"  [bold]{row['title']}[/bold] — [dim]{row['source']}[/dim]")
            terminal.console.print(f"    [link={row['url']}]{row['url']}[/link]")
            terminal.console.print(f"    [dim]Seen: {row['first_seen']}[/dim]")
        terminal.console.print()
    finally:
        store.close()


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Create default config file and database directory."""
    config_path: Path = ctx.obj["config_path"]
    config_dir = config_path.parent

    config_dir.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        click.echo(f"Config already exists: {config_path}")
    else:
        example = Path(__file__).parent.parent.parent / "config.example.yaml"
        if example.exists():
            shutil.copy(example, config_path)
        else:
            config_path.write_text(
                "feeds:\n"
                "  - name: Hacker News\n"
                "    url: https://hnrss.org/frontpage\n"
                "    type: rss\n"
                "    category: tech\n"
                "\n"
                "output:\n"
                "  terminal: true\n"
                "  markdown:\n"
                "    enabled: false\n"
                "    directory: ~/newsdigest-output\n"
                "  email:\n"
                "    enabled: false\n"
                "    recipient: user@example.com\n"
                "\n"
                "database:\n"
                "  path: ~/.newsdigest/seen.db\n"
                "\n"
                "ranking:\n"
                "  enabled: false\n"
                "  provider: mlx\n"
                "  model: mlx-community/Qwen3-4B-Instruct-2507-4bit\n"
                "  profile: |\n"
                "    General tech reader interested in software, AI, and Apple.\n"
            )
        click.echo(f"Created config: {config_path}")

    click.echo(f"Database directory: {config_dir}")
    click.echo("Edit your config, then run: news fetch")


@main.command()
@click.option("--blog", is_flag=True, help="Only show blog feeds")
@click.option("--news", is_flag=True, help="Only show news feeds")
@click.option("--no-rank", is_flag=True, help="Skip LLM ranking even if configured")
@click.pass_context
def today(ctx: click.Context, blog: bool, news: bool, no_rank: bool) -> None:
    """Show articles from today."""
    _show_since(ctx, days=0, label="today", blog=blog, news=news, no_rank=no_rank)


@main.command()
@click.option("--blog", is_flag=True, help="Only show blog feeds")
@click.option("--news", is_flag=True, help="Only show news feeds")
@click.option("--no-rank", is_flag=True, help="Skip LLM ranking even if configured")
@click.pass_context
def yesterday(ctx: click.Context, blog: bool, news: bool, no_rank: bool) -> None:
    """Show articles from today and yesterday."""
    _show_since(ctx, days=1, label="yesterday and today", blog=blog, news=news, no_rank=no_rank)


@main.command()
@click.option("--blog", is_flag=True, help="Only show blog feeds")
@click.option("--news", is_flag=True, help="Only show news feeds")
@click.option("--no-rank", is_flag=True, help="Skip LLM ranking even if configured")
@click.pass_context
def week(ctx: click.Context, blog: bool, news: bool, no_rank: bool) -> None:
    """Show articles from the past 7 days."""
    _show_since(ctx, days=7, label="the past week", blog=blog, news=news, no_rank=no_rank)


@main.command()
@click.option("--blog", is_flag=True, help="Only show blog feeds")
@click.option("--news", is_flag=True, help="Only show news feeds")
@click.option("--no-rank", is_flag=True, help="Skip LLM ranking even if configured")
@click.pass_context
def month(ctx: click.Context, blog: bool, news: bool, no_rank: bool) -> None:
    """Show articles from the past 30 days."""
    _show_since(ctx, days=30, label="the past month", blog=blog, news=news, no_rank=no_rank)


def _show_since(
    ctx: click.Context,
    *,
    days: int,
    label: str,
    blog: bool = False,
    news: bool = False,
    no_rank: bool = False,
) -> None:
    config = _load_config(ctx)
    store = ArticleStore(config.db_path)

    try:
        start_of_today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        since = start_of_today - timedelta(days=days)

        allowed_sources: set[str] | None = None
        if blog or news:
            feeds = _filter_feeds(config.feeds, blog=blog, news=news)
            allowed_sources = {f.name for f in feeds}

        rows = store.since(since)
        articles = [
            Article(
                url=row["url"] or "",
                title=row["title"] or "",
                source=row["source"] or "",
                category=row["category"] or "",
                published=datetime.fromisoformat(row["published"]) if row["published"] else None,
                summary=None,
            )
            for row in rows
            if allowed_sources is None or row["source"] in allowed_sources
        ]

        _deliver(config, articles, no_rank=no_rank, title=f"Articles from {label}")
    finally:
        store.close()


def _filter_feeds(
    feeds: list[FeedConfig], *, blog: bool = False, news: bool = False
) -> list[FeedConfig]:
    """Filter feeds by group. If neither flag is set, return all feeds."""
    if not blog and not news:
        return feeds
    allowed: set[str] = set()
    if blog:
        allowed.add("blog")
    if news:
        allowed.add("news")
    return [f for f in feeds if f.group in allowed]


def _load_config(ctx: click.Context) -> Config:
    config_path: Path = ctx.obj["config_path"]
    try:
        return load_config(config_path)
    except FileNotFoundError as e:
        raise click.ClickException(str(e)) from None
    except ValueError as e:
        raise click.ClickException(f"Invalid config: {e}") from None


def _fetch_all_feeds(feeds: list[FeedConfig]) -> list[Article]:
    all_articles: list[Article] = []
    for feed_config in feeds:
        if feed_config.type == "rss":
            source = RSSFeedSource(feed_config)
        elif feed_config.type == "scrape":
            click.echo(f"Warning: Scraping not implemented, skipping {feed_config.name}")
            continue
        else:
            click.echo(
                f"Warning: Unknown feed type '{feed_config.type}', skipping {feed_config.name}"
            )
            continue

        try:
            articles = source.fetch()
            all_articles.extend(articles)
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", feed_config.name, e)
            click.echo(f"Warning: Failed to fetch {feed_config.name}: {e}")

    return all_articles


def _deliver(
    config: Config,
    articles: list[Article],
    *,
    no_rank: bool = False,
    title: str = "News Digest",
) -> None:
    ranked: list[RankedArticle] | None = None
    warnings: list[str] = []

    if not no_rank and config.ranking.enabled:
        ranked, warnings = rank_articles(articles, config.ranking)
        if ranked is None and warnings:
            for w in warnings:
                click.echo(f"Warning: {w}")

    terminal = TerminalOutput()
    if config.output.terminal:
        if ranked is not None:
            terminal.render_ranked(ranked, title=title, warnings=warnings or None)
        else:
            terminal.render(articles, title=title)

    if config.output.markdown.enabled:
        md = MarkdownOutput(config.output.markdown.directory)
        filepath = md.render_ranked(ranked) if ranked is not None else md.render(articles)
        click.echo(f"Markdown digest written to: {filepath}")

    if config.output.email.enabled:
        try:
            email = EmailOutput(config.output.email.recipient)
            if ranked is not None:
                email.render_ranked(ranked)
            else:
                email.render(articles)
        except Exception as e:
            logger.error("Failed to send email: %s", e)
            click.echo(f"Warning: Failed to send email: {e}")
