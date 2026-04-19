"""
theme.py — ThemeManager for pyhelp.

Provides HelpTheme, which resolves colour/font settings for HelpWindow and
generates Qt stylesheets and HTML content CSS on demand.

No PyQt6 dependency — safe to import in headless environments.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Union


class HelpTheme:
    """
    Holds the resolved colour/font theme for HelpWindow.

    Can be constructed from:

    * Nothing — uses the built-in ``default_theme.json``.
    * A full application theme dict that contains a ``"helpwindow"`` key.
    * Just the ``helpwindow`` sub-dict directly.

    The theme generates a Qt stylesheet string and a CSS snippet for injecting
    into rendered HTML content on demand.

    Args:
        theme_dict: A dict that is either the full application theme
                    (containing a ``"helpwindow"`` key) or the helpwindow
                    sub-dict directly.  ``None`` uses built-in defaults.
        font_size:  Base font size in points.  Overrides the ``font_size``
                    field from the theme dict.
    """

    DEFAULT_THEME_PATH: Path = Path(__file__).parent / "defaults" / "default_theme.json"

    def __init__(
        self,
        theme_dict: Union[dict, None] = None,
        font_size: int = 13,
    ) -> None:
        self._defaults: dict = self._load_defaults()
        self._font_size: int = font_size

        if theme_dict is None:
            self._theme_name: str = "Dark"
            self._theme: dict = copy.deepcopy(self._defaults)
        elif "helpwindow" in theme_dict:
            # Full app theme — extract name and helpwindow block, merge with defaults
            self._theme_name = str(theme_dict.get("name", "Dark"))
            hw_block = theme_dict["helpwindow"]
            merged = copy.deepcopy(self._defaults)
            merged.update(hw_block)
            self._theme = merged
        else:
            # Assume caller passed the helpwindow block directly — no name available
            self._theme_name = "Dark"
            merged = copy.deepcopy(self._defaults)
            merged.update(theme_dict)
            self._theme = merged

        # Apply explicit font_size argument
        self._theme["font_size"] = font_size

    # ------------------------------------------------------------------
    # Class methods
    # ------------------------------------------------------------------

    @classmethod
    def from_app_theme(cls, app_theme: dict, font_size: int = 13) -> "HelpTheme":
        """
        Construct a HelpTheme from a full application theme dict.

        Extracts ``app_theme["helpwindow"]`` and merges with built-in defaults
        for any missing keys.

        Args:
            app_theme:  Full application theme dict, must contain a
                        ``"helpwindow"`` key.
            font_size:  Base font size in points.

        Returns:
            A new :class:`HelpTheme` instance.
        """
        return cls(theme_dict=app_theme, font_size=font_size)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def theme_name(self) -> str:
        """
        The theme name as provided in the top-level ``"name"`` field of the
        application theme dict (e.g. ``"Dark"``, ``"Light"``, ``"Print"``).
        Defaults to ``"Dark"`` when not supplied.
        """
        return self._theme_name

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_defaults(self) -> dict:
        """Load the built-in default theme from default_theme.json."""
        with self.DEFAULT_THEME_PATH.open("r", encoding="utf-8") as fh:
            full = json.load(fh)
        return full["helpwindow"]

    def _bg_is_dark(self) -> bool:
        """
        Return ``True`` if the theme background colour has HSL lightness below 50%.

        Used as the fallback criterion when no theme-named logo file exists.
        Treats unparseable colour values as dark.
        """
        hex_color = self._t("bg").lstrip("#")
        if len(hex_color) != 6:
            return True
        try:
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255
        except ValueError:
            return True
        # HSL lightness = (max_channel + min_channel) / 2
        lightness = (max(r, g, b) + min(r, g, b)) / 2
        return lightness < 0.5

    def _t(self, key: str) -> str:
        """Return theme value for *key*, falling back to empty string."""
        return str(self._theme.get(key, ""))

    def _i(self, key: str) -> int:
        """Return integer theme value for *key*, falling back to 0."""
        return int(self._theme.get(key, 0))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_logo(self, assets_dir: Union[Path, str]) -> Union[Path, None]:
        """
        Resolve the branding SVG path for this theme.

        Resolution order:

        1. ``{assets_dir}/branding_{theme_name}.svg`` — exact theme match.
        2. ``{assets_dir}/branding_Dark.svg`` or ``branding_Light.svg`` —
           chosen by whether the theme background colour is predominantly dark
           (HSL lightness < 50 %).

        Args:
            assets_dir: Directory containing ``branding_*.svg`` files.
                        Typically the host project's ``./assets/`` folder.

        Returns:
            Absolute :class:`~pathlib.Path` to the chosen SVG, or ``None`` if
            no matching file exists in *assets_dir*.
        """
        assets_dir = Path(assets_dir).resolve()

        # 1. Theme-specific file
        specific = assets_dir / f"branding_{self._theme_name}.svg"
        if specific.exists():
            return specific

        # 2. Lightness-based fallback
        fallback_name = "branding_Dark.svg" if self._bg_is_dark() else "branding_Light.svg"
        fallback = assets_dir / fallback_name
        if fallback.exists():
            return fallback

        return None

    def logo_badge_html(self) -> str:
        """
        Generate an HTML string for a compact branding badge to display in a
        ``QLabel`` when no branding SVG file is available.

        The badge renders as two lines separated by a single-pixel coloured
        rule (the "laser line"):

        ::

            pyhelp library     ← logo_text colour, font_size_logo
            ───────────────    ← 1 px rule in accent colour
            by ChipFX          ← logo_sub colour, font_size_small

        Inline styles are used throughout so the badge is self-contained and
        is not affected by the outer Qt stylesheet.

        Returns:
            HTML string suitable for ``QLabel.setText()``.
        """
        t = self._t
        fs = self._font_size
        fs_logo = self._i("font_size_logo") or fs + 2
        fs_small = self._i("font_size_small") or max(fs - 2, 9)
        font = t("font_family") or "sans-serif"

        line1 = (
            f'<p style="'
            f'margin: 1px 6px 0 6px; '
            f'padding-bottom: 3px; '
            f'border-bottom: 1px solid {t("accent")}; '
            f'font-family: {font}; '
            f'font-size: {fs_logo}pt; '
            f'font-weight: bold; '
            f'color: {t("logo_text")};">'
            f'pyhelp library</p>'
        )
        line2 = (
            f'<p style="'
            f'margin: 2px 6px 1px 6px; '
            f'font-family: {font}; '
            f'font-size: {fs_small}pt; '
            f'color: {t("logo_sub")};">'
            f'by ChipFX</p>'
        )
        return line1 + line2

    def apply_font_size(self, size: int) -> None:
        """
        Update the base font size used when generating stylesheets.

        Args:
            size: New font size in points.
        """
        self._font_size = size
        self._theme["font_size"] = size

    def to_stylesheet(self) -> str:
        """
        Generate a complete Qt stylesheet string for HelpWindow and its children.

        The stylesheet targets the widget object names set by HelpWindow
        (``HelpWindowRoot``, ``HelpToolbar``, ``HelpTree``, ``HelpContent``,
        ``HelpStatusBar``).

        Returns:
            Multi-line Qt stylesheet string.
        """
        t = self._t
        fs = self._font_size
        fs_small = self._i("font_size_small") or max(fs - 2, 9)
        fs_logo = self._i("font_size_logo") or fs + 2
        font = t("font_family") or "sans-serif"

        return f"""
/* ── HelpWindow root ─────────────────────────────────────────────── */
QDialog#HelpWindowRoot {{
    background-color: {t("bg")};
    color: {t("text")};
    font-family: {font};
    font-size: {fs}pt;
}}

/* ── Toolbar ─────────────────────────────────────────────────────── */
QWidget#HelpToolbar {{
    background-color: {t("bg_toolbar")};
    border-bottom: 1px solid {t("border")};
}}

QLabel#HelpLogoLabel {{
    color: {t("logo_text")};
    font-size: {fs_logo}pt;
    font-weight: bold;
    padding: 4px 8px;
}}

QLabel#HelpLogoSub {{
    color: {t("logo_sub")};
    font-size: {fs_small}pt;
    padding: 0px 8px 4px 8px;
}}

/* ── Close button ────────────────────────────────────────────────── */
QPushButton#HelpCloseButton {{
    background-color: {t("bg_button")};
    color: {t("text_button")};
    font-family: {font};
    font-size: {fs}pt;
    border: 1px solid {t("border_button")};
    border-bottom: 2px solid {t("border_button_bottom")};
    border-radius: 4px;
    padding: 4px 14px;
    min-width: 60px;
}}

QPushButton#HelpCloseButton:hover {{
    background-color: {t("bg_button_hover")};
    color: {t("text_button_hover")};
    border: 1px solid {t("border_focus")};
    border-bottom: 2px solid {t("border_button_bottom")};
}}

QPushButton#HelpCloseButton:pressed {{
    background-color: {t("bg_button_pressed")};
    border: 1px solid {t("border")};
    border-bottom: 1px solid {t("border_button_bottom")};
    padding-top: 5px;
    padding-bottom: 3px;
}}

/* ── Splitter ────────────────────────────────────────────────────── */
QSplitter#HelpSplitter {{
    background-color: {t("bg_splitter")};
}}

QSplitter#HelpSplitter::handle {{
    background-color: {t("border_splitter")};
    width: 2px;
}}

/* ── Help tree ───────────────────────────────────────────────────── */
QTreeWidget#HelpTree {{
    background-color: {t("bg_tree")};
    color: {t("text_tree")};
    font-family: {font};
    font-size: {fs}pt;
    border: none;
    border-right: 1px solid {t("border")};
    outline: none;
}}

QTreeWidget#HelpTree::item {{
    padding: 3px 6px;
}}

QTreeWidget#HelpTree::item:selected {{
    background-color: {t("bg_tree_selected")};
    color: {t("text_tree_selected")};
}}

QTreeWidget#HelpTree::item:hover:!selected {{
    background-color: {t("bg_button")};
}}

/* ── Content browser ─────────────────────────────────────────────── */
QTextBrowser#HelpContent {{
    background-color: {t("bg_content")};
    color: {t("text")};
    font-family: {font};
    font-size: {fs}pt;
    border: none;
    padding: 8px;
}}

/* ── Status bar ──────────────────────────────────────────────────── */
QStatusBar#HelpStatusBar {{
    background-color: {t("bg_statusbar")};
    color: {t("text_statusbar")};
    font-family: {font};
    font-size: {fs_small}pt;
    border-top: 1px solid {t("border")};
}}

/* ── Tooltips ────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {t("bg_tooltip")};
    color: {t("text_tooltip")};
    border: 1px solid {t("border")};
    font-family: {font};
    font-size: {fs_small}pt;
    padding: 4px 6px;
}}

/* ── Scrollbars ──────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: {t("bg_tree")};
    width: 10px;
    border: none;
}}

QScrollBar::handle:vertical {{
    background-color: {t("border")};
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {t("border_focus")};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {t("bg_tree")};
    height: 10px;
    border: none;
}}

QScrollBar::handle:horizontal {{
    background-color: {t("border")};
    border-radius: 5px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {t("border_focus")};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
""".strip()

    def content_css(self) -> str:
        """
        Generate a CSS string for injecting into the QTextBrowser HTML content.

        Matches background, text, link, and admonition colours from the theme so
        that rendered RST content looks visually integrated with the window.

        Returns:
            CSS string (without ``<style>`` tags).
        """
        t = self._t
        fs = self._font_size
        font = t("font_family") or "sans-serif"

        return f"""
body {{
    background-color: {t("bg_content")};
    color: {t("text")};
    font-family: {font};
    font-size: {fs}pt;
    line-height: 1.6;
    margin: 12px 16px;
}}

h1, h2, h3, h4, h5, h6 {{
    color: {t("text")};
    border-bottom: 1px solid {t("border")};
    padding-bottom: 4px;
    margin-top: 1.2em;
}}

a {{
    color: {t("link")};
    text-decoration: none;
}}

a:visited {{
    color: {t("link_visited")};
}}

a:hover {{
    text-decoration: underline;
}}

code, tt, pre {{
    background-color: {t("bg_tree")};
    color: {t("accent")};
    font-family: "Consolas", "Courier New", monospace;
    font-size: {fs - 1}pt;
    padding: 1px 4px;
    border-radius: 3px;
}}

pre {{
    padding: 8px 12px;
    overflow-x: auto;
}}

kbd {{
    background-color: {t("bg_button")};
    color: {t("text_button_hover")};
    border: 1px solid {t("border_button")};
    border-bottom: 2px solid {t("border_button_bottom")};
    border-radius: 3px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: {fs - 1}pt;
    padding: 1px 5px;
}}

ul, ol {{
    padding-left: 1.5em;
}}

li {{
    margin-bottom: 0.3em;
}}

/* Note admonition */
div.note {{
    background-color: {t("admonition_note_bg")};
    border-left: 4px solid {t("admonition_note_border")};
    padding: 8px 12px;
    margin: 1em 0;
    border-radius: 0 4px 4px 0;
}}

div.note p.admonition-title {{
    color: {t("accent")};
    font-weight: bold;
    margin: 0 0 6px 0;
}}

/* Warning admonition */
div.warning {{
    background-color: {t("admonition_warn_bg")};
    border-left: 4px solid {t("admonition_warn_border")};
    padding: 8px 12px;
    margin: 1em 0;
    border-radius: 0 4px 4px 0;
}}

div.warning p.admonition-title {{
    color: #ffaa44;
    font-weight: bold;
    margin: 0 0 6px 0;
}}

hr {{
    border: none;
    border-top: 1px solid {t("border")};
    margin: 1.5em 0;
}}

blockquote {{
    border-left: 3px solid {t("border")};
    margin-left: 1em;
    padding-left: 1em;
    color: {t("text_dim")};
}}
""".strip()
