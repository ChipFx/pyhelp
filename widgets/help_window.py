"""
help_window.py — HelpWindow widget for pyhelp.

The main help dialog.  Combines a HelpTree (left pane) with a QTextBrowser
(right pane) and a toolbar + status bar.  Fully themed via HelpTheme.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from PyQt6.QtCore import QSettings, QSize, Qt, QUrl
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt6.QtSvg import QSvgRenderer
    _SVG_AVAILABLE = True
except ImportError:
    _SVG_AVAILABLE = False

# Absolute path to pyhelp's own assets folder.  Used as the default logo
# source so the window works out-of-the-box without any caller configuration.
# Callers may point assets_dir elsewhere (e.g. the host project's ./assets/)
# to substitute their own branding — see HelpWindow.__init__.
_PYHELP_ASSETS: Path = (Path(__file__).parent.parent / "assets").resolve()

from pyhelp.parser import HelpEntry
from pyhelp.registry import HelpRegistry
from pyhelp.theme import HelpTheme
from pyhelp.widgets.help_tree import HelpTree


class HelpWindow(QDialog):
    """
    Main help dialog for pyhelp.

    Provides a tree-based topic browser on the left and a rendered HTML content
    pane on the right.  Supports live theme / font-size updates and remembers
    its geometry between sessions via :class:`QSettings`.

    Args:
        registry:   The :class:`~pyhelp.registry.HelpRegistry` providing content.
        parent:     Optional parent widget.
        modal:      If ``True`` the window blocks input to other application windows
                    (``ApplicationModal``).  If ``False`` (default) it is non-blocking
                    and should be shown with :meth:`show`.
        theme:      Full application theme dict (must contain a ``"helpwindow"`` key,
                    and optionally a top-level ``"name"`` field for logo resolution)
                    *or* the helpwindow sub-dict directly.  ``None`` uses the built-in
                    dark theme.
        font_size:  Base font size in points (default 13).
        assets_dir: Directory containing ``branding_*.svg`` logo files.
                    Resolved relative to the caller's working directory.
                    When omitted, a built-in fallback badge is shown.
    """

    # Height in pixels at which the branding SVG is rendered in the toolbar.
    LOGO_HEIGHT: int = 32

    def __init__(
        self,
        registry: HelpRegistry,
        parent=None,
        modal: bool = False,
        theme: Union[dict, None] = None,
        font_size: int = 13,
        assets_dir: Union[Path, str, None] = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        self._font_size = font_size
        # Resolve assets_dir to an absolute path.  When the caller supplies a
        # relative path (e.g. "./assets/") it resolves against the working
        # directory of the host process — which is intentionally different from
        # pyhelp's own assets folder (_PYHELP_ASSETS).
        self._assets_dir: Path = (
            Path(assets_dir).resolve() if assets_dir is not None else _PYHELP_ASSETS
        )
        self._theme = HelpTheme(theme_dict=theme, font_size=font_size)

        self.setObjectName("HelpWindowRoot")
        self.setWindowTitle(f"{registry.app_name} \u2014 Help")
        self.setMinimumSize(QSize(700, 480))

        if modal:
            self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._build_ui()
        self._apply_stylesheet()
        self._refresh_logo()
        self._restore_geometry()

        # Populate tree after UI is ready
        self._tree.populate()
        self._tree.topic_selected.connect(self._on_topic_selected)

        # Navigate to default or first entry
        self._navigate_initial()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """Assemble all child widgets and layouts."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Toolbar ────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setObjectName("HelpToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(6, 4, 6, 4)
        toolbar_layout.setSpacing(6)

        self._logo_label = QLabel(self._registry.app_name)
        self._logo_label.setObjectName("HelpLogoLabel")

        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        close_btn = QPushButton("Close")
        close_btn.setObjectName("HelpCloseButton")
        close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_btn.clicked.connect(self.close)

        toolbar_layout.addWidget(self._logo_label)
        toolbar_layout.addWidget(spacer)
        toolbar_layout.addWidget(close_btn)

        root_layout.addWidget(toolbar)

        # ── Splitter (tree + content) ──────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("HelpSplitter")

        self._tree = HelpTree(self._registry)
        splitter.addWidget(self._tree)

        self._browser = QTextBrowser()
        self._browser.setObjectName("HelpContent")
        self._browser.setOpenLinks(False)
        self._browser.anchorClicked.connect(self._on_link_clicked)
        splitter.addWidget(self._browser)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([220, 580])

        root_layout.addWidget(splitter, stretch=1)

        # ── Status bar ─────────────────────────────────────────────────
        self._status_bar = QStatusBar()
        self._status_bar.setObjectName("HelpStatusBar")
        self._status_bar.setSizeGripEnabled(False)
        root_layout.addWidget(self._status_bar)

    # ------------------------------------------------------------------
    # Theme / style
    # ------------------------------------------------------------------

    def _apply_stylesheet(self) -> None:
        """Apply the current theme stylesheet to this dialog."""
        self.setStyleSheet(self._theme.to_stylesheet())

    def _refresh_logo(self) -> None:
        """
        Resolve and display the branding SVG for the current theme, or render
        the built-in text badge when no SVG is available.

        Resolution is delegated to :meth:`~pyhelp.theme.HelpTheme.resolve_logo`.
        If no matching SVG exists in the assets directory (deleted, missing, or
        not yet created), a compact HTML badge reading "pyhelp library / by
        ChipFX" is shown in its place, using theme colours and a one-pixel
        accent-coloured rule as a divider.
        """
        svg_path = self._theme.resolve_logo(self._assets_dir)
        if svg_path is not None:
            pixmap = self._render_svg_pixmap(svg_path, self.LOGO_HEIGHT)
            if pixmap is not None:
                self._logo_label.setPixmap(pixmap)
                self._logo_label.setText("")
                return

        # No SVG resolved (or render failed) — show the branded text badge.
        self._logo_label.setPixmap(QPixmap())
        self._logo_label.setTextFormat(Qt.TextFormat.RichText)
        self._logo_label.setText(self._theme.logo_badge_html())

    def _render_svg_pixmap(self, path: Path, height: int) -> Union[QPixmap, None]:
        """
        Render an SVG file to a :class:`QPixmap` at the requested height.

        Width is computed from the SVG's intrinsic aspect ratio.  Returns
        ``None`` if ``PyQt6.QtSvg`` is unavailable or the file cannot be
        rendered.

        Args:
            path:   Path to the ``.svg`` file.
            height: Desired output height in pixels.

        Returns:
            Rendered :class:`QPixmap`, or ``None`` on failure.
        """
        if not _SVG_AVAILABLE:
            return None
        try:
            renderer = QSvgRenderer(str(path))
            if not renderer.isValid():
                return None
            default_size = renderer.defaultSize()
            if default_size.height() > 0:
                width = int(default_size.width() * height / default_size.height())
            else:
                width = height * 3
            pixmap = QPixmap(QSize(max(1, width), height))
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            return pixmap
        except Exception:
            return None

    def _render_entry(self, entry: HelpEntry) -> None:
        """Render *entry* into the QTextBrowser with injected theme CSS."""
        css = self._theme.content_css()
        html = f"<style>{css}</style>\n{entry.body_html}"
        self._browser.setHtml(html)
        self._status_bar.showMessage(entry.long_name)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _navigate_initial(self) -> None:
        """Navigate to default_topic if configured, else to the first entry."""
        default = self._registry.default_topic
        if default:
            self.navigate_to_path(default)
            return
        all_entries = self._registry.all_entries()
        if all_entries:
            self._show_entry(all_entries[0])
            self._tree.select_entry(all_entries[0].short_name)

    def _show_entry(self, entry: HelpEntry) -> None:
        """Render *entry* in the browser and update the status bar."""
        self._render_entry(entry)

    def _on_topic_selected(self, entry: HelpEntry) -> None:
        """Slot: called when user selects a topic in the tree."""
        self._show_entry(entry)

    def _on_link_clicked(self, url: QUrl) -> None:
        """Handle ``rst-doc://`` internal links between help topics."""
        scheme = url.scheme()
        if scheme == "rst-doc":
            # Format: rst-doc://chapter/short_name
            path = url.host() + url.path()  # host = chapter, path = /short_name
            path = path.lstrip("/")
            self.navigate_to_path(path)
        # All other schemes are ignored (no external browser launch)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_theme(self, theme_dict: dict) -> None:
        """
        Apply a new theme live without closing the window.

        Args:
            theme_dict: Full application theme dict or helpwindow sub-dict.
        """
        self._theme = HelpTheme(theme_dict=theme_dict, font_size=self._font_size)
        self._apply_stylesheet()
        self._refresh_logo()

    def set_font_size(self, size: int) -> None:
        """
        Update the font size live.

        Args:
            size: New font size in points.
        """
        self._font_size = size
        self._theme.apply_font_size(size)
        self._apply_stylesheet()

    def navigate_to(self, short_name: str) -> None:
        """
        Jump to the topic identified by *short_name*.

        Args:
            short_name: The ``short_name`` of the entry to display.
        """
        entry = self._registry.find(short_name)
        if entry is not None:
            self._show_entry(entry)
            self._tree.select_entry(short_name)

    def navigate_to_path(self, path: str) -> None:
        """
        Jump to a topic by its path string (e.g. ``"view/viewmode"``).

        Splits on ``/`` and uses the short_name component to locate the entry.

        Args:
            path: Path string such as ``"view/viewmode"``.
        """
        parts = path.split("/", 1)
        short_name = parts[1] if len(parts) == 2 else parts[0]
        self.navigate_to(short_name)
        self._tree.select_path(path)

    # ------------------------------------------------------------------
    # Geometry persistence
    # ------------------------------------------------------------------

    def _settings_key(self) -> str:
        app_name = self._registry.app_name.replace(" ", "_")
        return f"pyhelp/{app_name}/geometry"

    def _restore_geometry(self) -> None:
        """Restore window size and position from QSettings."""
        settings = QSettings()
        geom = settings.value(self._settings_key())
        if geom is not None:
            self.restoreGeometry(geom)

    def closeEvent(self, event) -> None:
        """Save window geometry on close."""
        settings = QSettings()
        settings.setValue(self._settings_key(), self.saveGeometry())
        super().closeEvent(event)
