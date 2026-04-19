"""
registry.py — HelpRegistry for pyhelp.

Scans a help directory tree, parses all .rst files, and provides ordered
chapter/entry access.  No PyQt6 dependency — safe to import headlessly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

from pyhelp.parser import HelpEntry, HelpParseError, parse_file


class HelpRegistry:
    """
    Scans a help root directory and provides structured access to parsed help entries.

    Directory layout expected::

        help_root/
            _config.yaml          # optional
            chapter_a/
                topic1.rst
                topic2.rst
            chapter_b/
                topic3.rst

    Args:
        help_root:   Path to the directory containing help ``.rst`` files.
                     Defaults to ``./help`` relative to the caller's working directory.
        config_file: Path to the YAML config file.  ``None`` (default) resolves to
                     ``help_root/_config.yaml``.  If the file does not exist the
                     registry silently uses built-in defaults.
    """

    def __init__(
        self,
        help_root: Union[str, Path] = "./help",
        config_file: Union[str, Path, None] = None,
    ) -> None:
        self._help_root: Path = Path(help_root).resolve()

        if config_file is None:
            self._config_path: Path = self._help_root / "_config.yaml"
        else:
            self._config_path = Path(config_file).resolve()

        self._config: dict = {}
        self._chapters: list[str] = []
        self._entries_by_chapter: dict[str, list[HelpEntry]] = {}

        self._load_config()
        self.scan()

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        """Load _config.yaml if it exists; silently ignore if absent or unreadable."""
        if yaml is None:
            return
        if not self._config_path.exists():
            return
        try:
            with self._config_path.open("r", encoding="utf-8") as fh:
                loaded = yaml.safe_load(fh)
            if isinstance(loaded, dict):
                self._config = loaded
        except Exception:
            # Malformed or unreadable config — continue with defaults
            self._config = {}

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan(self) -> None:
        """
        Walk *help_root* recursively, parse every ``.rst`` file, and build
        the internal chapter/entry index.

        Chapter order is determined by the ``chapter_order`` list in the config
        file.  Chapters not listed there are appended in alphabetical order after
        the explicitly ordered ones.

        This method is called automatically from ``__init__``.
        """
        raw_entries: list[HelpEntry] = []

        for rst_file in sorted(self._help_root.rglob("*.rst")):
            try:
                entry = parse_file(rst_file)
                raw_entries.append(entry)
            except HelpParseError:
                # Skip unparseable files; callers can catch individually if needed
                continue

        # Group by chapter
        by_chapter: dict[str, list[HelpEntry]] = {}
        for entry in raw_entries:
            by_chapter.setdefault(entry.chapter, []).append(entry)

        # Sort entries within each chapter by .order
        for chapter_entries in by_chapter.values():
            chapter_entries.sort(key=lambda e: (e.order, e.short_name))

        # Determine chapter order
        config_order: list[str] = self._config.get("chapter_order", [])
        ordered_chapters: list[str] = []
        for ch in config_order:
            if ch in by_chapter:
                ordered_chapters.append(ch)
        # Append remaining chapters alphabetically
        for ch in sorted(by_chapter.keys()):
            if ch not in ordered_chapters:
                ordered_chapters.append(ch)

        self._chapters = ordered_chapters
        self._entries_by_chapter = {ch: by_chapter[ch] for ch in ordered_chapters}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def chapters(self) -> list[str]:
        """Ordered list of chapter keys."""
        return list(self._chapters)

    def entries(self, chapter: str) -> list[HelpEntry]:
        """
        Return the entries for *chapter*, sorted by their ``order`` field.

        Args:
            chapter: Chapter key (e.g. ``"view"``).

        Returns:
            List of :class:`~pyhelp.parser.HelpEntry` objects, or an empty list
            if the chapter is not found.
        """
        return list(self._entries_by_chapter.get(chapter, []))

    def find(self, short_name: str) -> HelpEntry | None:
        """
        Search all chapters for an entry whose ``short_name`` matches.

        Args:
            short_name: The identifier to search for (e.g. ``"zoom-fit"``).

        Returns:
            The matching :class:`~pyhelp.parser.HelpEntry`, or ``None`` if not found.
        """
        for entry in self.all_entries():
            if entry.short_name == short_name:
                return entry
        return None

    def all_entries(self) -> list[HelpEntry]:
        """
        Flat list of all entries across all chapters, in chapter order.

        Returns:
            List of :class:`~pyhelp.parser.HelpEntry` objects.
        """
        result: list[HelpEntry] = []
        for ch in self._chapters:
            result.extend(self._entries_by_chapter.get(ch, []))
        return result

    @property
    def default_topic(self) -> str | None:
        """
        The default topic path from config (e.g. ``"view/viewmode"``), or ``None``
        if not configured.
        """
        return self._config.get("default_topic", None)

    @property
    def app_name(self) -> str:
        """Application name from config; defaults to ``"Help"`` if not set."""
        return self._config.get("app_name", "Help")

    def reload(self) -> None:
        """
        Re-read the config file and re-scan the help directory from disk.

        Useful during development for live-reload workflows.
        """
        self._config = {}
        self._load_config()
        self.scan()
