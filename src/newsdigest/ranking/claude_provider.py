import json
import logging
import os
import re

from newsdigest.models import Article, RankedArticle
from newsdigest.ranking.base import build_ranked_articles
from newsdigest.ranking.prompts import build_system_prompt, build_user_message

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_MODEL = "claude-3-5-haiku-20241022"


class ClaudeRanker:
    def rank(
        self, articles: list[Article], profile: str
    ) -> tuple[list[RankedArticle] | None, list[str]]:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None, ["ANTHROPIC_API_KEY not set — skipping Claude ranking"]

        try:
            import anthropic
        except ImportError:
            return None, ["anthropic package not installed (pip install anthropic)"]

        system = build_system_prompt(profile)
        user_msg = build_user_message(articles)
        client = anthropic.Anthropic(api_key=api_key)

        last_warnings: list[str] = []
        for attempt in range(2):
            try:
                response = client.messages.create(
                    model=_MODEL,
                    max_tokens=2000,
                    system=system,
                    messages=[{"role": "user", "content": user_msg}],
                )
                text = response.content[0].text
                text = _FENCE_RE.sub("", text).strip()
                start = text.find("{")
                end = text.rfind("}") + 1
                if start == -1 or end == 0:
                    msg = f"Claude returned no JSON object (attempt {attempt + 1})"
                    last_warnings = [msg]
                    logger.debug(msg)
                    continue
                data = json.loads(text[start:end])
                return build_ranked_articles(data, articles), []

            except json.JSONDecodeError as e:
                last_warnings = [f"Claude returned invalid JSON (attempt {attempt + 1}): {e}"]
                logger.debug(last_warnings[0])
                continue
            except Exception as e:
                # Check for rate limit by inspecting the exception type name
                if "RateLimit" in type(e).__name__:
                    return None, [f"Claude API rate limit hit: {e}"]
                return None, [f"Claude API error: {e}"]

        return None, last_warnings or ["Claude ranking failed after 2 attempts"]
