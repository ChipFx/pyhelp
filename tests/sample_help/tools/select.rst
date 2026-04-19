---
short_name: select
long_name: Selection Tool
chapter: tools
chapter_long: Tools
order: 10
keywords: [select, selection, move, pointer, tool]
---

Selection Tool
==============

The **Selection Tool** is the primary tool for interacting with objects on the
canvas.  Use it to select, move, resize, and arrange elements.

Activating the Tool
-------------------

* Press :kbd:`V` (the default shortcut)
* Click the arrow icon at the top of the toolbox
* Choose **Tools → Selection Tool** from the menu

Basic Operations
----------------

Selecting Objects
~~~~~~~~~~~~~~~~~

* **Click** an object to select it.
* **Click** on an empty area to deselect everything.
* **Shift+Click** to add an object to the current selection.
* **Drag** on an empty area to draw a rubber-band selection rectangle —
  all objects fully contained within it will be selected.

Moving Objects
~~~~~~~~~~~~~~

Click and drag any selected object to move it.  Hold :kbd:`Shift` while
dragging to constrain movement to horizontal or vertical only.

Nudging with the Keyboard
~~~~~~~~~~~~~~~~~~~~~~~~~

With one or more objects selected:

* :kbd:`Arrow` keys — nudge by 1 pixel
* :kbd:`Shift+Arrow` — nudge by 10 pixels
* :kbd:`Alt+Arrow` — nudge by 0.1 pixels (sub-pixel, where supported)

.. note::

   Nudge distance can be customised in **Preferences → Canvas → Nudge Distance**.

Resizing
--------

When an object is selected, handles appear at the corners and edge midpoints.
Drag a handle to resize.

* Drag a **corner** handle — resize freely
* Hold :kbd:`Shift` while dragging a corner — maintain aspect ratio
* Hold :kbd:`Alt` while dragging — resize from the centre

.. warning::

   Resizing a locked object is not possible.  Unlock the object first via
   **Object → Unlock** or :kbd:`Ctrl+Shift+L`.

Related Topics
--------------

See `Crop Tool <rst-doc://tools/crop>`_ for trimming objects to a specific
boundary.
