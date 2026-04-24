"""
parser.py — HelpEntry dataclass and RST file parsing for pyhelp.

Parses .rst files with YAML front matter into HelpEntry objects.
This module has no PyQt6 dependency and is safe to import in headless environments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

import frontmatter
from docutils.core import publish_parts

# Register the rst-doc:// URI scheme with docutils so it renders links that
# use this scheme as proper <a href="..."> elements rather than plain text.
# Docutils validates URI schemes against a registered list; custom schemes must
# be explicitly added before any parsing occurs.
try:
    import docutils.utils.urischemes as _urischemes
    _urischemes.schemes["rst-doc"] = "pyhelp internal cross-reference"
except Exception:
    pass


class HelpParseError(Exception):
    """Raised when a help file cannot be parsed due to missing fields or invalid RST."""


@dataclass
class HelpEntry:
    """
    Represents a single parsed help topic.

    Attributes:
        short_name:   Identifier used in navigation and cross-references (e.g. "zoom-fit").
        long_name:    Human-readable title displayed in the UI (e.g. "Zoom to Fit").
        chapter:      Chapter key, from front matter or parent folder name.
        chapter_long: Chapter display name, from front matter or titlecased chapter key.
        order:        Sort order within the chapter (lower = earlier). Default 100.
        keywords:     List of search keywords for future search functionality.
        body_rst:     Raw RST body text after front matter has been stripped.
        body_html:    HTML rendered from body_rst via docutils.
        source_path:  Absolute path to the source .rst file.
    """

    short_name: str
    long_name: str
    chapter: str
    chapter_long: str
    order: int
    keywords: list[str]
    body_rst: str
    body_html: str
    source_path: Path


def parse_file(path: Union[Path, str]) -> HelpEntry:
    """
    Parse a single .rst help file into a HelpEntry.

    The file must contain a YAML front matter block (delimited by ``---``) with at
    minimum the ``short_name`` and ``long_name`` fields.  All other fields are
    optional and will be derived from context or set to defaults when absent.

    Args:
        path: Filesystem path to the ``.rst`` file to parse.

    Returns:
        A fully populated :class:`HelpEntry`.

    Raises:
        HelpParseError: If required front matter fields are missing or the RST
                        body cannot be rendered.
        FileNotFoundError: If *path* does not exist.
    """
    path = Path(path).resolve()

    try:
        post = frontmatter.load(str(path))
    except Exception as exc:
        raise HelpParseError(
            f"Failed to load front matter from {path}: {exc}"
        ) from exc

    meta = post.metadata

    # Validate required fields
    missing = [f for f in ("short_name", "long_name") if f not in meta]
    if missing:
        raise HelpParseError(
            f"{path}: missing required front matter field(s): {', '.join(missing)}"
        )

    short_name: str = str(meta["short_name"])
    long_name: str = str(meta["long_name"])

    # chapter falls back to parent folder name
    chapter: str = str(meta["chapter"]) if "chapter" in meta else path.parent.name

    # chapter_long falls back to titlecased chapter key
    chapter_long: str = (
        str(meta["chapter_long"]) if "chapter_long" in meta else chapter.replace("-", " ").title()
    )

    order: int = int(meta.get("order", 100))
    keywords: list[str] = list(meta.get("keywords", []))
    body_rst: str = post.content

    # Render RST to HTML
    try:
        html_parts = publish_parts(
            body_rst,
            writer="html",
            settings_overrides={"halt_level": 5, "report_level": 5},
        )
        body_html: str = html_parts["html_body"]
    except Exception as exc:
        raise HelpParseError(
            f"{path}: RST rendering failed: {exc}"
        ) from exc

    return HelpEntry(
        short_name=short_name,
        long_name=long_name,
        chapter=chapter,
        chapter_long=chapter_long,
        order=order,
        keywords=keywords,
        body_rst=body_rst,
        body_html=body_html,
        source_path=path,
    )
