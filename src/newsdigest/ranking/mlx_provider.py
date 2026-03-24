import json
import logging
import re

from newsdigest.models import Article, RankedArticle
from newsdigest.ranking.base import build_ranked_articles
from newsdigest.ranking.prompts import build_system_prompt, build_user_message

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class MLXRanker:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None
        self._tokenizer = None

    def _load(self) -> list[str]:
        """Load model. Returns list of error strings (empty = success)."""
        try:
            from mlx_lm import load

            self._model, self._tokenizer = load(self._resolve_path())
            return []
        except Exception as e:
            return [f"Failed to load MLX model '{self._model_name}': {e}"]

    def _resolve_path(self) -> str:
        """Return local cache path if already downloaded, else the original ID."""
        try:
            from huggingface_hub import snapshot_download

            return snapshot_download(self._model_name, local_files_only=True)
        except Exception:
            return self._model_name

    def rank(
        self, articles: list[Article], profile: str
    ) -> tuple[list[RankedArticle] | None, list[str]]:
        if self._model is None:
            errors = self._load()
            if errors:
                return None, errors

        system = build_system_prompt(profile)
        user_msg = build_user_message(articles)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

        try:
            prompt = self._apply_chat_template(messages)
        except Exception as e:
            return None, [f"MLX chat template failed: {e}"]

        for attempt in range(2):
            try:
                from mlx_lm import generate

                raw = generate(
                    self._model, self._tokenizer, prompt=prompt, max_tokens=2000, verbose=False
                )
                ranked, warnings = self._parse(raw, articles)
                if ranked is not None:
                    return ranked, warnings
                if attempt == 0:
                    logger.debug("MLX JSON parse failed on attempt 1, retrying")
                    continue
                return None, warnings
            except Exception as e:
                return None, [f"MLX generation failed: {e}"]

        return None, ["MLX ranking failed after 2 attempts"]

    def _apply_chat_template(self, messages: list[dict]) -> str:
        assert self._tokenizer is not None
        try:
            return self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            return self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

    def _parse(
        self, text: str, articles: list[Article]
    ) -> tuple[list[RankedArticle] | None, list[str]]:
        text = _THINK_RE.sub("", text)
        text = _FENCE_RE.sub("", text).strip()
        # Find the first JSON object in the output
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            return None, [f"MLX returned no JSON object. Raw output: {text[:200]!r}"]
        try:
            data = json.loads(text[start:end])
            return build_ranked_articles(data, articles), []
        except json.JSONDecodeError as e:
            return None, [f"MLX returned invalid JSON: {e}. Raw: {text[:200]!r}"]
