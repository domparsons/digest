import tempfile
from datetime import datetime

from newsdigest.models import Article
from newsdigest.output.markdown import MarkdownOutput
from newsdigest.output.terminal import TerminalOutput


def _sample_articles() -> list[Article]:
    return [
        Article(
            url="https://example.com/1",
            title="Test Article One",
            source="Test Source",
            category="tech",
            published=datetime(2024, 1, 1, 12, 0),
            summary="Summary of article one",
        ),
        Article(
            url="https://example.com/2",
            title="Test Article Two",
            source="Other Source",
            category="science",
            published=None,
            summary=None,
        ),
    ]


def test_terminal_output_no_crash():
    """Terminal output runs without error."""
    output = TerminalOutput()
    output.render(_sample_articles())
    output.render([])  # Empty list should also work


def test_markdown_output_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        output = MarkdownOutput(tmpdir)
        filepath = output.render(_sample_articles())

        assert filepath.exists()
        content = filepath.read_text()
        assert "# News Digest" in content
        assert "Test Article One" in content
        assert "Test Article Two" in content
        assert "example.com/1" in content


def test_markdown_output_empty_articles():
    with tempfile.TemporaryDirectory() as tmpdir:
        output = MarkdownOutput(tmpdir)
        filepath = output.render([])

        content = filepath.read_text()
        assert "No new articles" in content


def test_markdown_output_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        output = MarkdownOutput(tmpdir)
        filepath = output.render(_sample_articles())

        content = filepath.read_text()
        assert "## Tech" in content
        assert "## Science" in content
        assert "> Summary of article one" in content
