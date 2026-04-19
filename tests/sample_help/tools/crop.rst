---
short_name: crop
long_name: Crop Tool
chapter: tools
chapter_long: Tools
order: 20
keywords: [crop, trim, boundary, clip, tool]
---

Crop Tool
=========

The **Crop Tool** lets you define a rectangular boundary and trim the canvas
or a selected object to that boundary.

Activating the Tool
-------------------

* Press :kbd:`C`
* Click the crop icon in the toolbox
* Choose **Tools → Crop Tool** from the menu

Cropping the Canvas
-------------------

1. Activate the Crop Tool.
2. Drag on the canvas to draw the crop boundary.
3. Adjust the handles if needed — drag edges or corners to refine.
4. Press :kbd:`Enter` or double-click inside the crop region to apply.
5. Press :kbd:`Escape` to cancel without cropping.

Crop Options
------------

The tool options bar (below the menu) provides:

Constrain ratio
    Lock the crop rectangle to a specific aspect ratio.  Common ratios
    (16:9, 4:3, 1:1, etc.) are available from the dropdown, or enter a
    custom ratio.

Shield colour
    The area outside the crop boundary is dimmed.  Click the colour swatch
    to change the shield colour and opacity.

Delete cropped pixels
    When checked, pixels outside the crop boundary are permanently removed.
    When unchecked, they are hidden but can be recovered by expanding the
    canvas later.

.. warning::

   **Delete cropped pixels** cannot be undone once the document is saved and
   closed.  Leave this unchecked if you might need to recover the trimmed
   content later.

Keyboard Shortcuts During Crop
-------------------------------

* :kbd:`Enter` — Apply crop
* :kbd:`Escape` — Cancel
* :kbd:`Shift+Drag` — Constrain crop to square
* :kbd:`Alt+Drag` — Draw crop from centre outward
* :kbd:`Space+Drag` — Move the crop boundary without resizing

Related Topics
--------------

For selecting and moving objects without cropping, see
`Selection Tool <rst-doc://tools/select>`_.
