---
name: Use uv and ruff for Python projects
description: User prefers uv (not pip), ruff (not black/flake8), and ty for type checking in Python projects
type: feedback
---

Use uv for all Python package management — never pip. Use ruff for linting/formatting. Use ty for type checking (still in alpha/beta but user wants it included).

**Why:** User preference for modern, fast Python tooling.
**How to apply:** Always set up pyproject.toml with dependency-groups for dev deps including ruff and ty. Use `uv sync`, `uv run pytest`, `uv run ruff check`, `uv run ty check`.
