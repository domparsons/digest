import logging
import shutil
from pathlib import Path

import click

from newsdigest.config import Config, FeedConfig, default_config_path, load_config
from newsdigest.feeds.rss import RSSFeedSource
from newsdigest.models import Article
from newsdigest.output.email import EmailOutput
from newsdigest.output.markdown import MarkdownOutput
from newsdigest.output.terminal import TerminalOutput
from newsdigest.storage import ArticleStore

logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=False),
    default=None,
    help="Path to config file (default: ~/.newsdigest/config.yaml)",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def main(ctx: click.Context, config_path: str | None, verbose: bool) -> None:
    """News Digest — fetch, deduplicate, and deliver news articles."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = Path(config_path) if config_path else default_config_path()


@main.command()
@click.pass_context
def fetch(ctx: click.Context) -> None:
    """Fetch all feeds, deduplicate, and output via configured channels."""
    config = _load_config(ctx)
    store = ArticleStore(config.db_path)

    try:
        all_articles = _fetch_all_feeds(config.feeds)
        new_articles = store.filter_new(all_articles)
        store.mark_seen(new_articles)
        _deliver(config, new_articles)
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
            terminal.console.print(
                f"  [bold]{row['title']}[/bold] — [dim]{row['source']}[/dim]"
            )
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
            # Write a minimal default config inline
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
            )
        click.echo(f"Created config: {config_path}")

    click.echo(f"Database directory: {config_dir}")
    click.echo("Edit your config, then run: newsdigest fetch")


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


def _deliver(config: Config, articles: list[Article]) -> None:
    if config.output.terminal:
        TerminalOutput().render(articles)

    if config.output.markdown.enabled:
        md = MarkdownOutput(config.output.markdown.directory)
        filepath = md.render(articles)
        click.echo(f"Markdown digest written to: {filepath}")

    if config.output.email.enabled:
        try:
            EmailOutput(config.output.email.recipient).render(articles)
        except Exception as e:
            logger.error("Failed to send email: %s", e)
            click.echo(f"Warning: Failed to send email: {e}")
