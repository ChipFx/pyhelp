"""
sizing.py — Layout and size configuration for pyhelp.

Provides :class:`LogoSizeSpec` (logo rendering dimension algorithm) and
:class:`HelpSizing` (full layout configuration loaded from
``defaults/default_size.json`` with optional caller overrides).

No PyQt6 dependency — safe to import in headless environments.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Union


@dataclass
class LogoSizeSpec:
    """
    Controls how the branding SVG is scaled before rendering.

    All dimensions are in pixels.  Any field left as ``None`` means
    "no constraint for that axis".

    Attributes:
        max_h:        Hard ceiling on rendered height.
        max_w:        Hard ceiling on rendered width.
        set_h:        Target height.  When ``keep_aspect`` is True and
                      ``set_w`` is ``None``, width is derived from the
                      SVG aspect ratio.
        set_w:        Target width.  When ``keep_aspect`` is True and
                      ``set_h`` is ``None``, height is derived from the
                      SVG aspect ratio.
        keep_aspect:  When True, the smaller of the two scale factors
                      (set_h vs set_w) is used so the image fits within
                      the requested box.  Max limits are re-applied with
                      aspect correction afterwards.
        fit_parent:   When True, the rendered size is clamped to the
                      parent widget's available dimensions so the logo
                      can never force the parent to grow.
    """

    max_h: Union[int, None] = None
    max_w: Union[int, None] = None
    set_h: Union[int, None] = None
    set_w: Union[int, None] = None
    keep_aspect: bool = True
    fit_parent: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "LogoSizeSpec":
        """
        Construct a :class:`LogoSizeSpec` from a plain dict (e.g. from JSON).

        Unknown keys are silently ignored.

        Args:
            d: Dict with any subset of the field names.

        Returns:
            New :class:`LogoSizeSpec` instance.
        """
        return cls(
            max_h=d.get("max_h"),
            max_w=d.get("max_w"),
            set_h=d.get("set_h"),
            set_w=d.get("set_w"),
            keep_aspect=bool(d.get("keep_aspect", True)),
            fit_parent=bool(d.get("fit_parent", True)),
        )

    def with_overrides(self, overrides: dict) -> "LogoSizeSpec":
        """
        Return a new :class:`LogoSizeSpec` with selected fields replaced.

        Args:
            overrides: Dict of field name → value pairs to override.

        Returns:
            New :class:`LogoSizeSpec` with overrides applied.
        """
        current = {
            "max_h": self.max_h,
            "max_w": self.max_w,
            "set_h": self.set_h,
            "set_w": self.set_w,
            "keep_aspect": self.keep_aspect,
            "fit_parent": self.fit_parent,
        }
        current.update(overrides)
        return LogoSizeSpec.from_dict(current)

    def compute_size(
        self,
        svg_w: int,
        svg_h: int,
        parent_h: Union[int, None] = None,
        parent_w: Union[int, None] = None,
    ) -> tuple[int, int]:
        """
        Compute the rendered pixel dimensions for an SVG.

        Resolution order:

        1. Apply ``set_h`` / ``set_w`` targets (with aspect correction when
           ``keep_aspect`` is True).
        2. Apply ``max_h`` / ``max_w`` hard ceilings, re-correcting the
           opposite axis when ``keep_aspect`` is True.
        3. Clamp to parent dimensions when ``fit_parent`` is True.

        Args:
            svg_w:    SVG intrinsic width in pixels.
            svg_h:    SVG intrinsic height in pixels.
            parent_h: Available height of the parent widget, for
                      ``fit_parent`` clamping.  ``None`` skips height
                      clamping.
            parent_w: Available width of the parent widget, for
                      ``fit_parent`` clamping.  ``None`` skips width
                      clamping.

        Returns:
            ``(width, height)`` tuple, both at least 1.
        """
        aspect: float = svg_w / svg_h if svg_h > 0 else 1.0
        w, h = float(svg_w), float(svg_h)

        # ── Step 1: apply set_ targets ────────────────────────────────
        if self.set_h is not None and self.set_w is not None:
            if self.keep_aspect:
                # Use the scale factor that fits within both targets
                scale_h = self.set_h / svg_h if svg_h > 0 else 1.0
                scale_w = self.set_w / svg_w if svg_w > 0 else 1.0
                scale = min(scale_h, scale_w)
                w, h = svg_w * scale, svg_h * scale
            else:
                w, h = float(self.set_w), float(self.set_h)
        elif self.set_h is not None:
            h = float(self.set_h)
            w = h * aspect if self.keep_aspect else float(svg_w or self.set_h)
        elif self.set_w is not None:
            w = float(self.set_w)
            h = w / aspect if (self.keep_aspect and aspect > 0) else float(svg_h or self.set_w)

        # ── Step 2: apply max ceilings ────────────────────────────────
        # Height ceiling first, then width — each may adjust the other.
        if self.max_h is not None and h > self.max_h:
            if self.keep_aspect and h > 0:
                w = w * self.max_h / h
            h = float(self.max_h)

        if self.max_w is not None and w > self.max_w:
            if self.keep_aspect and w > 0:
                h = h * self.max_w / w
            w = float(self.max_w)

        # ── Step 3: fit_parent clamping ───────────────────────────────
        if self.fit_parent:
            if parent_h is not None and h > parent_h:
                if self.keep_aspect and h > 0:
                    w = w * parent_h / h
                h = float(parent_h)
            if parent_w is not None and w > parent_w:
                if self.keep_aspect and w > 0:
                    h = h * parent_w / w
                w = float(parent_w)

        return max(1, int(round(w))), max(1, int(round(h)))


class HelpSizing:
    """
    Full layout and size configuration for HelpWindow.

    Loaded from ``defaults/default_size.json`` at construction time.
    Caller-supplied overrides are deep-merged on top so that only the
    fields the caller explicitly sets differ from the file defaults.

    Args:
        overrides: Optional dict of sizing overrides.  Nested dicts are
                   merged one level deep (e.g. ``{"logo": {"max_h": 64}}``
                   overrides only ``logo.max_h``).
    """

    DEFAULT_SIZE_PATH: Path = Path(__file__).parent / "defaults" / "default_size.json"

    def __init__(self, overrides: Union[dict, None] = None) -> None:
        with self.DEFAULT_SIZE_PATH.open("r", encoding="utf-8") as fh:
            self._config: dict = json.load(fh)

        if overrides:
            _deep_merge(self._config, overrides)

        window = self._config.get("window", {})
        splitter = self._config.get("splitter", {})

        self.window_width: int = int(window.get("width", 900))
        self.window_height: int = int(window.get("height", 600))
        self.tree_width: int = int(splitter.get("tree_width", 220))
        self.logo: LogoSizeSpec = LogoSizeSpec.from_dict(self._config.get("logo", {}))


def _deep_merge(base: dict, overrides: dict) -> None:
    """
    Merge *overrides* into *base* in-place.

    Nested dicts are merged one level deep; all other values are replaced.

    Args:
        base:      Dict to merge into (modified in place).
        overrides: Values to apply on top.
    """
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key].update(value)
        else:
            base[key] = value
