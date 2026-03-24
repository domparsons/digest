import logging

from newsdigest.config import RankingConfig
from newsdigest.models import Article, RankedArticle

logger = logging.getLogger(__name__)


def rank_articles(
    articles: list[Article], config: RankingConfig
) -> tuple[list[RankedArticle] | None, list[str]]:
    """Rank articles using the configured provider.

    Returns (ranked_articles, warnings).
    ranked_articles is None if ranking was skipped or failed — caller should fall back.
    """
    if not config.enabled:
        return None, []

    if not articles:
        return None, []

    ranker = _get_ranker(config)
    if ranker is None:
        return None, []

    try:
        return ranker.rank(articles, config.profile)
    except Exception as e:
        return None, [f"Ranking failed unexpectedly: {e}"]


def _get_ranker(config: RankingConfig):
    if config.provider == "mlx":
        try:
            import mlx_lm as _  # noqa: F401
        except ImportError:
            logger.warning("mlx-lm not installed — ranking disabled")
            return None
        from newsdigest.ranking.mlx_provider import MLXRanker

        return MLXRanker(config.model)

    if config.provider == "claude":
        from newsdigest.ranking.claude_provider import ClaudeRanker

        return ClaudeRanker()

    logger.warning("Unknown ranking provider '%s'", config.provider)
    return None
