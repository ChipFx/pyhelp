"""
test_registry.py — Unit tests for pyhelp.registry.HelpRegistry.

Tests cover directory scanning, chapter ordering, entry lookup, config
handling, reload, and path resolution edge cases.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pyhelp.registry import HelpRegistry

# The bundled sample help directory
SAMPLE_HELP = Path(__file__).parent / "sample_help"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_rst(directory: Path, short_name: str, long_name: str, order: int = 100) -> Path:
    """Write a minimal valid .rst file into *directory*."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{short_name}.rst"
    path.write_text(
        f"---\nshort_name: {short_name}\nlong_name: {long_name}\norder: {order}\n---\nBody.\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestScanFindsAllFiles:
    """HelpRegistry.scan() finds every .rst file under help_root."""

    def test_scan_finds_all_files(self):
        registry = HelpRegistry(SAMPLE_HELP)
        all_entries = registry.all_entries()
        # There are 4 sample files: view/viewmode, view/zoom-fit,
        # tools/select, tools/crop
        assert len(all_entries) == 4

    def test_scan_no_extra_entries(self):
        registry = HelpRegistry(SAMPLE_HELP)
        short_names = {e.short_name for e in registry.all_entries()}
        assert short_names == {"viewmode", "zoom-fit", "select", "crop"}


class TestChapterOrder:
    """Chapter order follows chapter_order in _config.yaml."""

    def test_chapter_order_respected(self):
        registry = HelpRegistry(SAMPLE_HELP)
        # _config.yaml: chapter_order: [view, tools]
        assert registry.chapters == ["view", "tools"]

    def test_unlisted_chapters_appended_alphabetically(self, tmp_path):
        # Create help dir with three chapters, config only lists one
        config = tmp_path / "_config.yaml"
        config.write_text("chapter_order:\n  - beta\n", encoding="utf-8")
        make_rst(tmp_path / "alpha", "a1", "Alpha One")
        make_rst(tmp_path / "beta", "b1", "Beta One")
        make_rst(tmp_path / "gamma", "g1", "Gamma One")

        registry = HelpRegistry(tmp_path)
        # beta first (from config), then alpha and gamma alphabetically
        assert registry.chapters[0] == "beta"
        assert registry.chapters[1] == "alpha"
        assert registry.chapters[2] == "gamma"


class TestFindByShortName:
    """HelpRegistry.find() returns the correct entry or None."""

    def test_find_by_short_name(self):
        registry = HelpRegistry(SAMPLE_HELP)
        entry = registry.find("zoom-fit")
        assert entry is not None
        assert entry.long_name == "Zoom to Fit"

    def test_find_missing_returns_none(self):
        registry = HelpRegistry(SAMPLE_HELP)
        result = registry.find("does-not-exist")
        assert result is None

    def test_find_across_chapters(self):
        registry = HelpRegistry(SAMPLE_HELP)
        crop = registry.find("crop")
        assert crop is not None
        assert crop.chapter == "tools"


class TestDefaultTopic:
    """default_topic is read from _config.yaml."""

    def test_default_topic_from_config(self):
        registry = HelpRegistry(SAMPLE_HELP)
        assert registry.default_topic == "view/viewmode"

    def test_default_topic_absent_when_no_config(self, tmp_path):
        make_rst(tmp_path / "ch", "t1", "Topic One")
        registry = HelpRegistry(tmp_path)
        assert registry.default_topic is None

    def test_app_name_from_config(self):
        registry = HelpRegistry(SAMPLE_HELP)
        assert registry.app_name == "SampleApp"

    def test_app_name_default(self, tmp_path):
        make_rst(tmp_path / "ch", "t1", "Topic One")
        registry = HelpRegistry(tmp_path)
        assert registry.app_name == "Help"


class TestReload:
    """reload() re-reads config and re-scans from disk."""

    def test_reload_picks_up_new_file(self, tmp_path):
        ch_dir = tmp_path / "things"
        make_rst(ch_dir, "thing1", "Thing One")
        registry = HelpRegistry(tmp_path)
        assert len(registry.all_entries()) == 1

        # Add a second file and reload
        make_rst(ch_dir, "thing2", "Thing Two")
        registry.reload()
        assert len(registry.all_entries()) == 2

    def test_reload_removes_deleted_file(self, tmp_path):
        ch_dir = tmp_path / "things"
        p1 = make_rst(ch_dir, "thing1", "Thing One")
        make_rst(ch_dir, "thing2", "Thing Two")
        registry = HelpRegistry(tmp_path)
        assert len(registry.all_entries()) == 2

        p1.unlink()
        registry.reload()
        assert len(registry.all_entries()) == 1
        assert registry.find("thing1") is None

    def test_reload_updates_modified_entry(self, tmp_path):
        ch_dir = tmp_path / "ch"
        path = make_rst(ch_dir, "t1", "Original Name")
        registry = HelpRegistry(tmp_path)
        assert registry.find("t1").long_name == "Original Name"

        path.write_text(
            "---\nshort_name: t1\nlong_name: Updated Name\n---\nNew body.\n",
            encoding="utf-8",
        )
        registry.reload()
        assert registry.find("t1").long_name == "Updated Name"


class TestMissingConfigFile:
    """Registry works without a _config.yaml file."""

    def test_missing_config_no_crash(self, tmp_path):
        make_rst(tmp_path / "ch", "t1", "Topic One")
        # No _config.yaml written — should not raise
        registry = HelpRegistry(tmp_path)
        assert len(registry.all_entries()) == 1

    def test_missing_config_defaults(self, tmp_path):
        make_rst(tmp_path / "ch", "t1", "Topic One")
        registry = HelpRegistry(tmp_path)
        assert registry.default_topic is None
        assert registry.app_name == "Help"

    def test_explicit_missing_config_path(self, tmp_path):
        make_rst(tmp_path / "ch", "t1", "Topic One")
        nonexistent = tmp_path / "no_such_config.yaml"
        registry = HelpRegistry(tmp_path, config_file=nonexistent)
        assert len(registry.all_entries()) == 1


class TestRelativePathResolution:
    """help_root is resolved to an absolute path regardless of how it is supplied."""

    def test_relative_path_resolved(self, tmp_path, monkeypatch):
        ch_dir = tmp_path / "ch"
        make_rst(ch_dir, "t1", "Topic One")
        # Change cwd to tmp_path so a relative path is valid
        monkeypatch.chdir(tmp_path)
        registry = HelpRegistry(".")
        assert registry.all_entries()[0].source_path.is_absolute()

    def test_source_path_is_absolute(self):
        registry = HelpRegistry(SAMPLE_HELP)
        for entry in registry.all_entries():
            assert entry.source_path.is_absolute()


class TestEntriesOrdering:
    """entries() returns entries sorted by their order field."""

    def test_entries_sorted_by_order(self, tmp_path):
        ch = tmp_path / "ch"
        make_rst(ch, "c", "C Topic", order=30)
        make_rst(ch, "a", "A Topic", order=10)
        make_rst(ch, "b", "B Topic", order=20)
        registry = HelpRegistry(tmp_path)
        names = [e.short_name for e in registry.entries("ch")]
        assert names == ["a", "b", "c"]

    def test_entries_for_missing_chapter_empty(self):
        registry = HelpRegistry(SAMPLE_HELP)
        assert registry.entries("nonexistent") == []
