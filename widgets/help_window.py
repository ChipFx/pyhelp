"""
help_window.py — HelpWindow widget for pyhelp.

The main help dialog.  Combines a HelpTree (left pane) with a QTextBrowser
(right pane) and a toolbar + status bar.  Fully themed via HelpTheme.
"""

from __future__ import annotations

from collections.abc import Callable
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
from pyhelp.sizing import HelpSizing, LogoSizeSpec
from pyhelp.theme import HelpTheme
from pyhelp.widgets.help_tree import HelpTree


class HelpWindow(QDialog):
    """
    Main help dialog for pyhelp.

    Provides a tree-based topic browser on the left and a rendered HTML content
    pane on the right.  Supports live theme / font-size updates and remembers
    its geometry between sessions via :class:`QSettings`.

    Geometry priority on :meth:`show`: explicit ``size`` argument →
    QSettings saved geometry → ``defaults/default_size.json`` fallback.

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
                    When omitted, pyhelp's own assets folder is used.
    """

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
        # directory of the host process — intentionally different from
        # pyhelp's own assets folder (_PYHELP_ASSETS).
        self._assets_dir: Path = (
            Path(assets_dir).resolve() if assets_dir is not None else _PYHELP_ASSETS
        )

        self._theme = HelpTheme(theme_dict=theme, font_size=font_size)
        self._sizing = HelpSizing()
        self._logo_spec: LogoSizeSpec = self._sizing.logo
        self._on_close_callback: Union[Callable[[dict], None], None] = None

        self.setObjectName("HelpWindowRoot")
        self.setWindowTitle(f"{registry.app_name} \u2014 Help")
        self.setMinimumSize(QSize(700, 480))

        if modal:
            self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._build_ui()
        self._apply_stylesheet()
        self._refresh_logo()

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
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setObjectName("HelpSplitter")

        self._tree = HelpTree(self._registry)
        self._splitter.addWidget(self._tree)

        self._browser = QTextBrowser()
        self._browser.setObjectName("HelpContent")
        self._browser.setOpenLinks(False)
        self._browser.anchorClicked.connect(self._on_link_clicked)
        self._splitter.addWidget(self._browser)

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 3)

        root_layout.addWidget(self._splitter, stretch=1)

        # ── Status bar ─────────────────────────────────────────────────
        self._status_bar = QStatusBar()
        self._status_bar.setObjectName("HelpStatusBar")
        self._status_bar.setSizeGripEnabled(False)
        root_layout.addWidget(self._status_bar)

    # ------------------------------------------------------------------
    # Show / geometry
    # ------------------------------------------------------------------

    def show(
        self,
        *,
        size: Union[tuple[int, int], None] = None,
        splitter: Union[int, None] = None,
        logo: Union[dict, None] = None,
        on_close: Union[Callable[[dict], None], None] = None,
    ) -> None:
        """
        Show the help window, optionally restoring previously stored geometry.

        All parameters are keyword-only.  Omit any parameter to fall through
        to the next priority level (QSettings → ``default_size.json``).

        Args:
            size:     ``(width, height)`` of the window in pixels.  Overrides
                      both QSettings and the size defaults.
            splitter: Tree-panel width in pixels.  Overrides the splitter
                      default from ``default_size.json``.
            logo:     Dict of :class:`~pyhelp.sizing.LogoSizeSpec` field
                      overrides (e.g. ``{"max_h": 64, "set_h": 48}``).
                      Merged on top of the ``default_size.json`` logo section.
            on_close: Callable invoked when the window is closed.  Receives a
                      dict with keys ``"width"``, ``"height"``, and
                      ``"splitter_tree_width"`` reflecting the final user-adjusted
                      dimensions.  Store these and pass them back via ``size``
                      and ``splitter`` on the next :meth:`show` call to restore
                      the user's layout.
        """
        self._on_close_callback = on_close

        # Apply logo overrides before showing
        if logo is not None:
            self._logo_spec = self._sizing.logo.with_overrides(logo)
            self._refresh_logo()

        # Geometry: explicit size → QSettings → default_size.json
        if size is not None:
            self.resize(size[0], size[1])
        else:
            if not self._restore_geometry():
                self.resize(self._sizing.window_width, self._sizing.window_height)

        # Splitter: explicit → default_size.json
        tree_w = splitter if splitter is not None else self._sizing.tree_width
        content_w = max(1, self.width() - tree_w)
        self._splitter.setSizes([tree_w, content_w])

        super().show()

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
        ChipFX" is shown in its place.
        """
        svg_path = self._theme.resolve_logo(self._assets_dir)
        if svg_path is not None:
            pixmap = self._render_svg_pixmap(svg_path)
            if pixmap is not None:
                self._logo_label.setPixmap(pixmap)
                self._logo_label.setText("")
                return

        # No SVG resolved (or render failed) — show the branded text badge.
        self._logo_label.setPixmap(QPixmap())
        self._logo_label.setTextFormat(Qt.TextFormat.RichText)
        self._logo_label.setText(self._theme.logo_badge_html())

    def _render_svg_pixmap(self, path: Path) -> Union[QPixmap, None]:
        """
        Render an SVG file to a :class:`QPixmap` using the current
        :class:`~pyhelp.sizing.LogoSizeSpec`.

        The spec controls target dimensions, aspect-ratio preservation, max
        limits, and whether the logo may push its parent widget to grow.

        Returns:
            Rendered :class:`QPixmap`, or ``None`` if ``PyQt6.QtSvg`` is
            unavailable or the file cannot be rendered.
        """
        if not _SVG_AVAILABLE:
            return None
        try:
            renderer = QSvgRenderer(str(path))
            if not renderer.isValid():
                return None

            default_size = renderer.defaultSize()
            svg_w, svg_h = default_size.width(), default_size.height()

            parent = self._logo_label.parentWidget()
            parent_h = parent.height() if parent else None
            parent_w = parent.width() if parent else None

            w, h = self._logo_spec.compute_size(svg_w, svg_h, parent_h, parent_w)

            pixmap = QPixmap(QSize(w, h))
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
        """
        Handle ``rst-doc://`` internal links between help topics.

        Reconstructs the full path from the URL host and path components, then
        appends the fragment (``#anchor``) if present so sub-section scrolling
        is preserved through to :meth:`navigate_to_path`.
        """
        if url.scheme() != "rst-doc":
            return  # ignore external links

        # host = first path segment (chapter), path = remainder
        path = (url.host() + url.path()).lstrip("/")
        fragment = url.fragment()
        if fragment:
            path = f"{path}#{fragment}"
        self.navigate_to_path(path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reload(self) -> None:
        """
        Re-scan the help directory from disk and refresh the UI in place.

        Calls :meth:`~pyhelp.registry.HelpRegistry.reload` on the registry,
        rebuilds the tree, and attempts to re-display the topic that was
        showing before the reload.  If that topic no longer exists (file was
        deleted or ``short_name`` changed), falls back to
        ``registry.default_topic`` or the first available entry.

        Intended for use during help content development — wire it to a
        button or keyboard shortcut in your host application to see edits
        without reopening the window.
        """
        # Remember what was showing
        current_html = self._browser.toPlainText()  # non-empty iff something loaded
        current_items = self._tree.selectedItems()
        current_short_name: Union[str, None] = None
        if current_items:
            from PyQt6.QtCore import Qt as _Qt
            entry = current_items[0].data(0, _Qt.ItemDataRole.UserRole)
            if entry is not None:
                current_short_name = entry.short_name

        # Reload registry and rebuild tree
        self._registry.reload()
        self._tree.populate()

        # Re-navigate: current topic → default_topic → first entry
        if current_short_name is not None and self._registry.find(current_short_name):
            self.navigate_to(current_short_name)
        else:
            self._navigate_initial()

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
        Jump to a topic by its path string, with graceful degradation for
        paths that have more depth than the current registry supports.

        Path format::

            chapter/short_name              # two-segment (standard)
            chapter/sub/short_name          # three-segment: tries short_name,
                                            # then sub, then first entry in chapter
            chapter                         # one-segment: first entry in chapter
            chapter/short_name#section-id   # with anchor: scrolls to that
                                            # heading or explicit RST target
                                            # within the loaded document

        Anchor IDs are generated by docutils from heading text
        (``"My Section"`` → ``"my-section"``) or from explicit
        ``.. _target-name:`` directives.

        Args:
            path: Path string, optionally with a ``#anchor`` fragment.
        """
        # Split anchor fragment
        anchor: Union[str, None] = None
        if "#" in path:
            path, anchor = path.split("#", 1)

        segments = [s for s in path.split("/") if s]
        if not segments:
            return

        navigated = False

        if len(segments) == 1:
            # Single segment: try as short_name, then as chapter key
            entry = self._registry.find(segments[0])
            if entry is not None:
                self._show_entry(entry)
                self._tree.select_entry(segments[0])
                navigated = True
            else:
                chapter_entries = self._registry.entries(segments[0])
                if chapter_entries:
                    self._show_entry(chapter_entries[0])
                    self._tree.select_entry(chapter_entries[0].short_name)
                    navigated = True
        else:
            # Multi-segment: try each segment as short_name from most-specific
            # (last) to least-specific (first), stop on first match.
            for short_name in reversed(segments):
                entry = self._registry.find(short_name)
                if entry is not None:
                    self._show_entry(entry)
                    self._tree.select_path(path)
                    navigated = True
                    break

            if not navigated:
                # No segment matched — navigate to the first entry of the
                # chapter named by the first segment.
                chapter_entries = self._registry.entries(segments[0])
                if chapter_entries:
                    self._show_entry(chapter_entries[0])
                    self._tree.select_path(path)
                    navigated = True

        if navigated and anchor:
            self._scroll_to_anchor(anchor)

    def _scroll_to_anchor(self, anchor: str) -> None:
        """
        Scroll the content browser to a named anchor within the current document.

        Deferred by one event-loop iteration to ensure the HTML has been fully
        rendered before the scroll is attempted.

        Args:
            anchor: The anchor ID to scroll to.  Docutils generates these from
                    heading text (``"My Section"`` → ``"my-section"``) and from
                    explicit ``.. _target-name:`` directives in RST source.
        """
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._browser.scrollToAnchor(anchor))

    # ------------------------------------------------------------------
    # Geometry persistence
    # ------------------------------------------------------------------

    def _settings_key(self) -> str:
        app_name = self._registry.app_name.replace(" ", "_")
        return f"pyhelp/{app_name}/geometry"

    def _restore_geometry(self) -> bool:
        """
        Attempt to restore window geometry from QSettings.

        Returns:
            ``True`` if saved geometry was found and successfully applied,
            ``False`` if no saved state existed.
        """
        settings = QSettings()
        geom = settings.value(self._settings_key())
        if geom is not None:
            return self.restoreGeometry(geom)
        return False

    def closeEvent(self, event) -> None:
        """Save geometry to QSettings and invoke the on-close callback."""
        settings = QSettings()
        settings.setValue(self._settings_key(), self.saveGeometry())

        if self._on_close_callback is not None:
            self._on_close_callback({
                "width": self.width(),
                "height": self.height(),
                "splitter_tree_width": self._splitter.sizes()[0],
            })

        super().closeEvent(event)
