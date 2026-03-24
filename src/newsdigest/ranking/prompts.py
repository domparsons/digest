import json

from newsdigest.models import Article

_SYSTEM_TEMPLATE = """\
You are a news ranking assistant. Your job is to rank articles by relevance and importance \
for a specific reader.

Reader profile:
{profile}

Tier definitions:
- "highlight": Genuinely significant events only. New model releases, major product launches, \
acquisitions, big policy shifts, breakthroughs. Expect 0-3 per day across all feeds.
- "notable": Worth knowing about. Interesting technical posts, meaningful tool updates, \
industry trends, solid analysis pieces.
- "routine": Everything else. Minor updates, incremental news, rumour pieces, listicles, \
opinion fluff.

Return ONLY valid JSON with this exact structure. No markdown fences, no preamble, \
no trailing text:
{{
  "rankings": [
    {{
      "index": 0,
      "tier": "highlight",
      "score": 95,
      "summary": "One-line summary of why this article matters"
    }}
  ]
}}

Every article in the input must appear in rankings. Score 1-100 within each tier."""


def build_system_prompt(profile: str) -> str:
    return _SYSTEM_TEMPLATE.format(profile=profile.strip() or "General tech reader.")


def build_user_message(articles: list[Article]) -> str:
    items = []
    for i, a in enumerate(articles):
        item: dict = {
            "index": i,
            "title": a.title,
            "source": a.source,
            "published": a.published.strftime("%Y-%m-%d") if a.published else "unknown",
        }
        if a.summary:
            item["summary"] = a.summary[:200]
        items.append(item)
    return json.dumps(items, indent=2)
