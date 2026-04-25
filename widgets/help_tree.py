"""
help_tree.py — HelpTree widget for pyhelp.

A QTreeWidget that displays chapters and help entries from a HelpRegistry.
Emits ``topic_selected`` when the user selects an entry.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem

from pyhelp.parser import HelpEntry
from pyhelp.registry import HelpRegistry


class HelpTree(QTreeWidget):
    """
    Tree widget displaying chapters and help entries from a :class:`~pyhelp.registry.HelpRegistry`.

    Top-level items represent chapters (labelled with ``chapter_long``).
    Child items represent individual help entries (labelled with ``long_name``,
    tooltip from ``long_name``).

    Signals:
        topic_selected: Emitted with the selected :class:`~pyhelp.parser.HelpEntry`
                        whenever the user changes selection via click or keyboard.

    Args:
        registry: The :class:`~pyhelp.registry.HelpRegistry` to display.
        parent:   Optional parent widget.
    """

    topic_selected: pyqtSignal = pyqtSignal(HelpEntry)

    def __init__(self, registry: HelpRegistry, parent=None) -> None:
        super().__init__(parent)
        self._registry = registry

        self.setObjectName("HelpTree")
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        self.itemSelectionChanged.connect(self._on_selection_changed)

        self.populate()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self) -> None:
        """
        Build (or rebuild) the tree from the registry.

        Clears existing content before rebuilding.  Call this after
        ``registry.reload()`` to refresh the displayed tree.
        """
        self.blockSignals(True)
        self.clear()

        for chapter_key in self._registry.chapters:
            entries = self._registry.entries(chapter_key)
            if not entries:
                continue

            # Use chapter_long from the first entry as the display label
            chapter_long = entries[0].chapter_long if entries else chapter_key.title()

            chapter_item = QTreeWidgetItem(self, [chapter_long])
            chapter_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )
            # Mark as chapter so we can skip it during navigation
            chapter_item.setData(0, Qt.ItemDataRole.UserRole, None)

            for entry in entries:
                entry_item = QTreeWidgetItem(chapter_item, [entry.long_name])
                entry_item.setToolTip(0, entry.long_name)
                entry_item.setData(0, Qt.ItemDataRole.UserRole, entry)

            chapter_item.setExpanded(True)

        self.blockSignals(False)

    def select_entry(self, short_name: str) -> None:
        """
        Find the entry with the given *short_name* and select it in the tree,
        expanding its parent chapter if necessary.

        Args:
            short_name: The ``short_name`` of the entry to select.
        """
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            chapter_item = root.child(i)
            for j in range(chapter_item.childCount()):
                entry_item = chapter_item.child(j)
                entry: HelpEntry | None = entry_item.data(0, Qt.ItemDataRole.UserRole)
                if entry is not None and entry.short_name == short_name:
                    chapter_item.setExpanded(True)
                    self.blockSignals(True)
                    self.setCurrentItem(entry_item)
                    self.blockSignals(False)
                    self.scrollToItem(entry_item)
                    return

    def select_path(self, path: str) -> None:
        """
        Select an entry by its path string, with graceful degradation for
        paths that have more segments than the current tree depth supports.

        The ``#anchor`` fragment (used for sub-section scrolling) is stripped
        before matching.  Segments are tried from most-specific (last) to
        least-specific (first) as ``short_name`` values.  If no segment
        matches a known entry, the first entry of the chapter named by the
        first segment is selected instead.

        Args:
            path: Path string such as ``"view/viewmode"``,
                  ``"menu_bar/file_menu/import"``, or
                  ``"view/viewmode#section-id"``.
        """
        # Strip anchor fragment
        if "#" in path:
            path = path.split("#", 1)[0]

        segments = [s for s in path.split("/") if s]
        if not segments:
            return

        # Try each segment as a short_name, from most-specific (last) to first
        for short_name in reversed(segments):
            root = self.invisibleRootItem()
            for i in range(root.childCount()):
                chapter_item = root.child(i)
                for j in range(chapter_item.childCount()):
                    entry_item = chapter_item.child(j)
                    entry: HelpEntry | None = entry_item.data(
                        0, Qt.ItemDataRole.UserRole
                    )
                    if entry is not None and entry.short_name == short_name:
                        chapter_item.setExpanded(True)
                        self.blockSignals(True)
                        self.setCurrentItem(entry_item)
                        self.blockSignals(False)
                        self.scrollToItem(entry_item)
                        return

        # No segment matched as a short_name — expand and select the first
        # entry of the chapter named by the first segment.
        chapter_key = segments[0]
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            chapter_item = root.child(i)
            if chapter_item.childCount() == 0:
                continue
            first_entry: HelpEntry | None = chapter_item.child(0).data(
                0, Qt.ItemDataRole.UserRole
            )
            if first_entry is not None and first_entry.chapter == chapter_key:
                chapter_item.setExpanded(True)
                self.blockSignals(True)
                self.setCurrentItem(chapter_item.child(0))
                self.blockSignals(False)
                self.scrollToItem(chapter_item.child(0))
                return

    # ------------------------------------------------------------------
    # Private slots
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        """Emit ``topic_selected`` when the selection changes to an entry item."""
        items = self.selectedItems()
        if not items:
            return
        entry: HelpEntry | None = items[0].data(0, Qt.ItemDataRole.UserRole)
        if entry is not None:
            self.topic_selected.emit(entry)
