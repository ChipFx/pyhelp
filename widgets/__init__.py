"""
pyhelp.widgets — PyQt6 widget components for HelpWindow.

This package requires PyQt6.  Import guards in the parent package prevent
ImportError from propagating when PyQt6 is unavailable.
"""

from pyhelp.widgets.help_tree import HelpTree
from pyhelp.widgets.help_window import HelpWindow

__all__ = ["HelpWindow", "HelpTree"]
