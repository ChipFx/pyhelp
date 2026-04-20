# pyhelp

A reusable, modular help system for PyQt6 applications.  Write your help
content as plain RST files with a small YAML front matter header, point
`HelpRegistry` at the folder, and drop `HelpWindow` into your application —
no build step, no database, no compiled resources required.

---

## Installation as a git submodule

pyhelp is designed to live inside your project as a submodule, not as an
installed package.

```bash
# Add pyhelp as a submodule inside your project
git submodule add https://github.com/ChipFx/pyhelp.git pyhelp
git submodule update --init --recursive
```

Install the runtime dependencies into your project's virtual environment:

```bash
pip install -r pyhelp/requirements.txt
```

Add `pyhelp`'s parent directory to `sys.path` so it can be imported (or rely
on your project already being on the path):

```python
import sys
sys.path.insert(0, ".")   # if pyhelp/ lives in the project root
```

### Optional: editable install for IDE support

If you want IDE auto-complete and type checking, you can install pyhelp in
editable mode — but this is **not required** for it to work:

```bash
pip install -e ./pyhelp
```

### `.gitmodules` example

```ini
[submodule "pyhelp"]
    path = pyhelp
    url = https://github.com/ChipFx/pyhelp.git
    branch = main
```

### Updating the submodule

```bash
git submodule update --remote pyhelp
git add pyhelp
git commit -m "Update pyhelp submodule"
```

---

## Quickstart

```python
from pyhelp import HelpRegistry, HelpWindow

registry = HelpRegistry("./help")          # path to your .rst files
window = HelpWindow(registry, parent=self) # pass your main window as parent
window.show()                              # non-blocking by default
```

To open modally (blocks other windows while help is open):

```python
window = HelpWindow(registry, parent=self, modal=True)
window.show()
```

To jump to a specific topic programmatically:

```python
window.navigate_to("zoom-fit")            # by short_name
window.navigate_to_path("view/zoom-fit")  # by chapter/short_name path
```

---

## Help file format

Help files are `.rst` (reStructuredText) files with a YAML front matter
block at the top.

### Front matter fields

| Field          | Required | Default                          | Description                                       |
|----------------|----------|----------------------------------|---------------------------------------------------|
| `short_name`   | **yes**  | —                                | Identifier used in navigation (e.g. `zoom-fit`)   |
| `long_name`    | **yes**  | —                                | Display name shown in the tree (e.g. `Zoom to Fit`)|
| `chapter`      | no       | parent folder name               | Chapter key for grouping                          |
| `chapter_long` | no       | `chapter.replace("-", " ").title()` | Chapter display label                          |
| `order`        | no       | `100`                            | Sort order within the chapter (lower = first)     |
| `keywords`     | no       | `[]`                             | List of search keywords (reserved for future use) |

### Example file

```rst
---
short_name: zoom-fit
long_name: Zoom to Fit
chapter: view
chapter_long: View
order: 20
keywords: [zoom, fit, scale, canvas]
---

Zoom to Fit
===========

The **Zoom to Fit** command scales the canvas so that the entire document
is visible without scrolling.

Press :kbd:`Ctrl+0` or choose **View → Zoom → Zoom to Fit**.

.. note::

   Zoom to Fit respects your current view mode.

For layout options, see `View Modes <rst-doc://view/viewmode>`_.
```

### Cross-references between topics

Use the custom `rst-doc://` URL scheme to link between help topics:

```rst
`Topic Label <rst-doc://chapter/short_name>`_
```

HelpWindow intercepts these links and navigates the tree and content pane
without opening a browser.

---

## `_config.yaml`

Place a `_config.yaml` file in your help root to control global settings.
If the file is absent, pyhelp silently uses defaults.

```yaml
app_name: "MyApp"                   # Shown in window title and toolbar
chapter_order:                      # Explicit chapter display order
  - getting-started
  - view
  - tools
default_topic: "getting-started/overview"  # Opened on first launch
```

| Field           | Default   | Description                                                |
|-----------------|-----------|------------------------------------------------------------|
| `app_name`      | `"Help"`  | Application name shown in the window title and toolbar     |
| `chapter_order` | `[]`      | Ordered list of chapter keys; unlisted chapters appended alphabetically |
| `default_topic` | `null`    | Path to the topic shown on first open (`"chapter/short_name"`) |

---

## Theming

Pass a theme dict when constructing HelpWindow:

```python
my_theme = {
    "helpwindow": {
        "bg":               "#1a1a2e",
        "text":             "#e0e0f0",
        "accent":           "#7eb8ff",
        "logo_text":        "#f0c040",
        # ... (see full list below)
    }
}
window = HelpWindow(registry, theme=my_theme)
```

You can also pass just the `"helpwindow"` sub-dict directly.  Any keys you
omit fall back to the built-in dark theme.

### Live updates

```python
window.apply_theme(my_theme)       # replace full theme
window.set_font_size(15)           # change font size only
```

### All theme fields

| Field                    | Default     | Description                                      |
|--------------------------|-------------|--------------------------------------------------|
| `bg`                     | `#0d0d1a`  | Main window background                           |
| `bg_content`             | `#10101f`  | Content browser background                       |
| `bg_tree`                | `#0b0b17`  | Tree widget background                           |
| `bg_tree_selected`       | `#1e1e48`  | Selected tree item background                    |
| `bg_toolbar`             | `#08080f`  | Toolbar background                               |
| `bg_statusbar`           | `#08080f`  | Status bar background                            |
| `bg_tooltip`             | `#16162e`  | Tooltip background                               |
| `bg_button`              | `#1a1a30`  | Button background                                |
| `bg_button_hover`        | `#24244a`  | Button hover background                          |
| `bg_button_pressed`      | `#0e0e22`  | Button pressed background                        |
| `text`                   | `#d0d0e8`  | Primary text colour                              |
| `text_dim`               | `#8888aa`  | Dimmed text (status bar, captions)               |
| `text_tree`              | `#c0c0dc`  | Tree item text                                   |
| `text_tree_selected`     | `#ffffff`  | Selected tree item text                          |
| `logo_text`              | `#f0c040`  | App name label colour                            |
| `logo_sub`               | `#555577`  | Sub-label colour below app name                  |
| `accent`                 | `#66aaff`  | Accent / highlight colour                        |
| `link`                   | `#66aaff`  | Hyperlink colour in content                      |
| `link_visited`           | `#9977dd`  | Visited link colour                              |
| `border`                 | `#2a2a50`  | General border colour                            |
| `border_button`          | `#3a3a60`  | Button top/side border                           |
| `border_button_bottom`   | `#111130`  | Button bottom border (affordance shadow)         |
| `border_focus`           | `#66aaff`  | Focus ring / hover border                        |
| `admonition_note_bg`     | `#0e1a2e`  | Note admonition background                       |
| `admonition_note_border` | `#2255aa`  | Note admonition left border                      |
| `admonition_warn_bg`     | `#2a1a00`  | Warning admonition background                    |
| `admonition_warn_border` | `#aa6600`  | Warning admonition left border                   |
| `font_family`            | `Segoe UI, Arial, sans-serif` | Font stack        |
| `font_size`              | `13`       | Base font size (points)                          |
| `font_size_logo`         | `15`       | Logo label font size                             |
| `font_size_small`        | `11`       | Small text font size (status bar, tooltips)      |

---

## Qt-free usage

`HelpRegistry`, `HelpEntry`, and `HelpTheme` are fully importable without
PyQt6.  This lets you use the registry in CLI tools, documentation generators,
or test environments that have no display server:

```python
from pyhelp import HelpRegistry

registry = HelpRegistry("./help")

for chapter in registry.chapters:
    print(f"\n=== {chapter} ===")
    for entry in registry.entries(chapter):
        print(f"  [{entry.order:3d}] {entry.short_name}: {entry.long_name}")

entry = registry.find("zoom-fit")
print(entry.body_html)   # rendered HTML, no Qt required
```

---

## Running tests

```bash
cd pyhelp
pip install -r requirements-dev.txt
pytest tests/
```

The test suite has no Qt dependency and runs with a plain `pytest` invocation
on any platform, including headless CI.

---

## Roadmap

**v1 (current)**
- RST parsing with YAML front matter
- Chapter/entry registry with config-driven ordering
- Dark-themed HelpWindow with tree navigation
- Non-blocking and modal modes
- Live theme and font-size updates
- Geometry persistence via QSettings
- `rst-doc://` inter-topic linking

**v2 (planned)**
- Full-text search panel
- HTML export (`export_html`)
- PDF export (`export_pdf`)
- Sphinx project generation (`generate_sphinx_project`)
- Light theme and auto theme switching
