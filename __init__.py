"""
pyhelp — Reusable, modular help system for PyQt6 applications.

Designed for use as a git submodule.  Core classes (HelpRegistry, HelpEntry,
HelpTheme, HelpParseError) are importable without PyQt6.  Widget classes
(HelpWindow, HelpTree) are available only when PyQt6 is installed.

Quickstart::

    from pyhelp import HelpRegistry, HelpWindow

    registry = HelpRegistry("./help")
    window = HelpWindow(registry)
    window.show()
"""

from pyhelp.parser import HelpEntry, HelpParseError
from pyhelp.registry import HelpRegistry
from pyhelp.sizing import HelpSizing, LogoSizeSpec
from pyhelp.theme import HelpTheme

__version__ = "0.1.0"

__all__ = [
    "HelpRegistry",
    "HelpEntry",
    "HelpTheme",
    "HelpParseError",
    "HelpSizing",
    "LogoSizeSpec",
    "HelpWindow",
    "HelpTree",
]

# Widget classes require PyQt6 — guard so non-Qt environments still import cleanly.
try:
    from pyhelp.widgets import HelpTree, HelpWindow  # noqa: F401
except ImportError:
    pass
