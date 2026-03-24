# news

Fetches articles from RSS feeds, deduplicates them, and outputs a ranked digest in the terminal — tiered into Highlights, Notable, and Routine using a local MLX model or the Claude API.

## Setup

```sh
git clone <repo>
cd digest
uv sync
news init
```

`init` creates `~/.newsdigest/config.yaml` and the SQLite database. Edit the config to add your feeds and configure ranking.

## Config

`~/.newsdigest/config.yaml`

```yaml
feeds:
  - name: Hacker News
    url: https://hnrss.org/frontpage
    type: rss
    category: tech
    group: news        # "news" or "blog" — used with --news / --blog flags

  - name: Anthropic Engineering
    url: https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml
    type: rss
    category: ai
    group: blog

output:
  terminal: true
  markdown:
    enabled: false
    directory: ~/newsdigest-output
  email:
    enabled: false
    recipient: you@example.com

database:
  path: ~/.newsdigest/seen.db

ranking:
  enabled: true
  provider: mlx                                      # "mlx" or "claude"
  model: mlx-community/Qwen3-4B-Instruct-2507-4bit  # any MLX-compatible HF model
  profile: |
    Software engineer interested in AI/ML tooling, Apple ecosystem,
    Rust, Java, fintech. Less interested in gaming, crypto, social media.
```

**Environment variables:**

| Var | When needed |
|-----|-------------|
| `HF_TOKEN` | Private HuggingFace models, or to avoid rate limits on first download |
| `ANTHROPIC_API_KEY` | Required when `provider: claude` |
| `NEWSDIGEST_SMTP_HOST/PORT/USER/PASS` | Required when email output is enabled |

## Usage

```sh
news                        # default: yesterday --blog (with ranking if configured)
news --no-rank              # same, skip ranking

news fetch                  # fetch all feeds, mark new articles as seen
news fetch --blog           # blog feeds only
news fetch --news           # news feeds only

news today                  # articles published today
news yesterday              # today + yesterday
news week                   # past 7 days
news month                  # past 30 days

news today --blog           # filter by feed group
news today --no-rank        # skip ranking for this run

news history                # last 20 seen articles
news history -n 50          # last 50
news list-feeds             # show configured feeds
```

All time-range commands (`today`, `yesterday`, `week`, `month`) read from the local database by published date — they don't hit the network. Use `news fetch` to pull new articles first.

When ranking is enabled, output is grouped into three tiers sorted by relevance score. On first use with an MLX model, the model downloads from HuggingFace (~2–4GB). Subsequent runs load from the local cache.

## Scheduling

To run `news fetch` automatically, create a launchd plist at `~/Library/LaunchAgents/com.newsdigest.fetch.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.newsdigest.fetch</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>-c</string>
    <string>~/.local/bin/news fetch</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>8</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/tmp/newsdigest.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/newsdigest.err</string>
</dict>
</plist>
```

Load it with:

```sh
launchctl load ~/Library/LaunchAgents/com.newsdigest.fetch.plist
```
