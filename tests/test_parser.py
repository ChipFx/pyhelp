"""
test_parser.py — Unit tests for pyhelp.parser.

Tests cover HelpEntry dataclass population, front matter validation,
HTML rendering, and fallback logic for optional fields.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pyhelp.parser import HelpEntry, HelpParseError, parse_file

# Path to the sample help directory bundled with the test suite
SAMPLE_HELP = Path(__file__).parent / "sample_help"
VIEW_DIR = SAMPLE_HELP / "view"
TOOLS_DIR = SAMPLE_HELP / "tools"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_rst(tmp_path):
    """Return a factory for writing temporary .rst files."""

    def _write(content: str, filename: str = "topic.rst") -> Path:
        p = tmp_path / filename
        p.write_text(textwrap.dedent(content), encoding="utf-8")
        return p

    return _write


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestParseValidFile:
    """parse_file() correctly populates all HelpEntry fields."""

    def test_parse_valid_file(self):
        path = VIEW_DIR / "viewmode.rst"
        entry = parse_file(path)

        assert isinstance(entry, HelpEntry)
        assert entry.short_name == "viewmode"
        assert entry.long_name == "View Modes"
        assert entry.chapter == "view"
        assert entry.chapter_long == "View"
        assert entry.order == 10
        assert "view" in entry.keywords
        assert "mode" in entry.keywords
        assert entry.source_path == path.resolve()

    def test_all_sample_files_parse(self):
        """Every bundled sample file should parse without error."""
        for rst in SAMPLE_HELP.rglob("*.rst"):
            entry = parse_file(rst)
            assert entry.short_name, f"{rst}: short_name empty"
            assert entry.long_name, f"{rst}: long_name empty"


class TestMissingRequiredFields:
    """parse_file() raises HelpParseError when required fields are absent."""

    def test_missing_short_name(self, tmp_rst):
        path = tmp_rst(
            """\
            ---
            long_name: Only Long Name
            ---
            Body text.
            """
        )
        with pytest.raises(HelpParseError, match="short_name"):
            parse_file(path)

    def test_missing_long_name(self, tmp_rst):
        path = tmp_rst(
            """\
            ---
            short_name: only-short
            ---
            Body text.
            """
        )
        with pytest.raises(HelpParseError, match="long_name"):
            parse_file(path)

    def test_missing_both_required_fields(self, tmp_rst):
        path = tmp_rst(
            """\
            ---
            order: 5
            ---
            Body text.
            """
        )
        with pytest.raises(HelpParseError):
            parse_file(path)


class TestBodyHtml:
    """Rendered HTML contains expected content."""

    def test_body_html_not_empty(self):
        entry = parse_file(VIEW_DIR / "viewmode.rst")
        assert entry.body_html.strip() != ""

    def test_body_html_contains_heading(self):
        entry = parse_file(VIEW_DIR / "viewmode.rst")
        # docutils wraps headings in <h1> / <section> tags
        assert "<h" in entry.body_html

    def test_body_html_contains_body_text(self):
        entry = parse_file(VIEW_DIR / "zoom-fit.rst")
        # "Zoom to Fit" appears in the RST body
        assert "Zoom to Fit" in entry.body_html

    def test_body_html_contains_note_admonition(self):
        entry = parse_file(VIEW_DIR / "viewmode.rst")
        # docutils renders note:: as <div class="note">
        assert "note" in entry.body_html.lower()


class TestChapterFallback:
    """chapter falls back to parent folder name when not in front matter."""

    def test_chapter_fallback_to_folder(self, tmp_rst, tmp_path):
        # Create a sub-folder to act as the "chapter"
        chapter_dir = tmp_path / "mychapter"
        chapter_dir.mkdir()
        path = chapter_dir / "topic.rst"
        path.write_text(
            "---\nshort_name: topic\nlong_name: My Topic\n---\nBody.\n",
            encoding="utf-8",
        )
        entry = parse_file(path)
        assert entry.chapter == "mychapter"

    def test_chapter_long_falls_back_to_titlecase(self, tmp_rst, tmp_path):
        chapter_dir = tmp_path / "my-chapter"
        chapter_dir.mkdir()
        path = chapter_dir / "topic.rst"
        path.write_text(
            "---\nshort_name: topic\nlong_name: My Topic\n---\nBody.\n",
            encoding="utf-8",
        )
        entry = parse_file(path)
        # "my-chapter" → titlecase → "My Chapter"
        assert entry.chapter_long == "My Chapter"

    def test_explicit_chapter_takes_precedence(self):
        entry = parse_file(VIEW_DIR / "viewmode.rst")
        # Front matter says chapter: view, parent folder is also "view" here,
        # but the explicit value should be used regardless
        assert entry.chapter == "view"


class TestOrderDefault:
    """order defaults to 100 when not specified in front matter."""

    def test_order_default_is_100(self, tmp_rst):
        path = tmp_rst(
            """\
            ---
            short_name: no-order
            long_name: No Order
            ---
            Body text.
            """
        )
        entry = parse_file(path)
        assert entry.order == 100

    def test_explicit_order_respected(self):
        entry = parse_file(VIEW_DIR / "viewmode.rst")
        assert entry.order == 10

    def test_keywords_default_empty(self, tmp_rst):
        path = tmp_rst(
            """\
            ---
            short_name: no-kw
            long_name: No Keywords
            ---
            Body text.
            """
        )
        entry = parse_file(path)
        assert entry.keywords == []
