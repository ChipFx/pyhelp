"""
exporter.py — Export functionality for pyhelp.

v1 stub.  Full implementation deferred to v2.
Structure is here so future Claude Code sessions can build on it without
needing to re-discover the API shape.
"""

from __future__ import annotations

from pathlib import Path

from pyhelp.registry import HelpRegistry


def export_html(registry: HelpRegistry, output_dir: Path) -> None:
    """
    Export the full help set as a static HTML site.

    Args:
        registry:   Source :class:`~pyhelp.registry.HelpRegistry`.
        output_dir: Directory where HTML files will be written.

    Raises:
        NotImplementedError: Always — implementation deferred to v2.
    """
    raise NotImplementedError("HTML export coming in v2")


def export_pdf(registry: HelpRegistry, output_path: Path) -> None:
    """
    Export the full help set as a single PDF document.

    Args:
        registry:    Source :class:`~pyhelp.registry.HelpRegistry`.
        output_path: Destination ``.pdf`` file path.

    Raises:
        NotImplementedError: Always — implementation deferred to v2.
    """
    raise NotImplementedError("PDF export coming in v2")


def generate_sphinx_project(registry: HelpRegistry, output_dir: Path) -> None:
    """
    Generate a Sphinx documentation project from the help registry.

    Args:
        registry:   Source :class:`~pyhelp.registry.HelpRegistry`.
        output_dir: Directory where the Sphinx project skeleton will be written.

    Raises:
        NotImplementedError: Always — implementation deferred to v2.
    """
    raise NotImplementedError("Sphinx export coming in v2")
