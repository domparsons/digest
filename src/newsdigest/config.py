from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FeedConfig:
    name: str
    url: str
    type: str
    category: str = ""
    group: str = ""


@dataclass(frozen=True)
class MarkdownOutputConfig:
    enabled: bool = False
    directory: str = "~/newsdigest-output"


@dataclass(frozen=True)
class EmailOutputConfig:
    enabled: bool = False
    recipient: str = ""


@dataclass(frozen=True)
class OutputConfig:
    terminal: bool = True
    markdown: MarkdownOutputConfig = field(default_factory=MarkdownOutputConfig)
    email: EmailOutputConfig = field(default_factory=EmailOutputConfig)


@dataclass(frozen=True)
class DatabaseConfig:
    path: str = "~/.newsdigest/seen.db"


@dataclass(frozen=True)
class RankingConfig:
    enabled: bool = False
    provider: str = "mlx"
    model: str = "mlx-community/Qwen3-4B-Instruct-2507-4bit"
    profile: str = ""


@dataclass(frozen=True)
class Config:
    feeds: list[FeedConfig]
    output: OutputConfig = field(default_factory=OutputConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ranking: RankingConfig = field(default_factory=RankingConfig)

    @property
    def db_path(self) -> Path:
        return Path(self.database.path).expanduser()


def load_config(path: Path) -> Config:
    """Load and validate configuration from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Run 'newsdigest init' to create a default config."
        )

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not raw or "feeds" not in raw:
        raise ValueError("Config must contain a 'feeds' section.")

    feeds = [
        FeedConfig(
            name=f["name"],
            url=f["url"],
            type=f.get("type", "rss"),
            category=f.get("category", ""),
            group=f.get("group", ""),
        )
        for f in raw["feeds"]
    ]

    output_raw = raw.get("output", {})
    output = OutputConfig(
        terminal=output_raw.get("terminal", True),
        markdown=MarkdownOutputConfig(**output_raw.get("markdown", {})),
        email=EmailOutputConfig(**output_raw.get("email", {})),
    )

    db_raw = raw.get("database", {})
    database = DatabaseConfig(**db_raw)

    ranking_raw = raw.get("ranking", {})
    ranking = RankingConfig(
        enabled=ranking_raw.get("enabled", False),
        provider=ranking_raw.get("provider", "mlx"),
        model=ranking_raw.get("model", "mlx-community/Qwen3-4B-Instruct-2507-4bit"),
        profile=ranking_raw.get("profile", ""),
    )

    return Config(feeds=feeds, output=output, database=database, ranking=ranking)


def default_config_path() -> Path:
    return Path("~/.newsdigest/config.yaml").expanduser()
