from typing import Protocol

from newsdigest.models import Article, RankedArticle

VALID_TIERS = {"highlight", "notable", "routine"}


class ArticleRanker(Protocol):
    def rank(
        self, articles: list[Article], profile: str
    ) -> tuple[list[RankedArticle] | None, list[str]]:
        """Rank articles. Returns (ranked_articles, warnings).

        ranked_articles is None if ranking failed — caller should fall back to unranked.
        warnings is a list of human-readable messages about what went wrong.
        """
        ...


def build_ranked_articles(data: dict, articles: list[Article]) -> list[RankedArticle]:
    """Convert raw LLM JSON response into RankedArticle list.

    Articles missing from the response default to tier=routine, score=50.
    """
    rankings = {int(r["index"]): r for r in data.get("rankings", []) if "index" in r}
    result: list[RankedArticle] = []
    for i, article in enumerate(articles):
        r = rankings.get(i, {})
        tier = r.get("tier", "routine")
        if tier not in VALID_TIERS:
            tier = "routine"
        score = max(1, min(100, int(r.get("score", 50))))
        summary = r.get("summary") or article.title
        result.append(RankedArticle(article=article, tier=tier, score=score, summary=summary))
    return result
