# pythonscad-gridfinity

A Python library for generating [Gridfinity](https://gridfinity.xyz/)-compatible
baseplates and bins using [PythonSCAD](https://pythonscad.org/).

<!-- Badges (uncomment when published)
[![PyPI version](https://img.shields.io/pypi/v/pythonscad-gridfinity)](https://pypi.org/project/pythonscad-gridfinity/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
-->

## What is this?

[Gridfinity](https://www.youtube.com/watch?v=ra_9zU-mnl8) is a modular storage
system created by [Zack Freedman](https://www.youtube.com/c/ZackFreedman). It
uses a standardised grid of interlocking baseplates and bins to organise tools,
parts, and other small items.

[PythonSCAD](https://pythonscad.org/) is a fork of OpenSCAD that adds a native
Python API for programmatic 3D modelling. This library lets you generate
Gridfinity objects directly from Python scripts inside PythonSCAD.

## Features

### Baseplates

- Five baseplate styles: thin, weighted, skeletonized, screw-together, and
  screw-together-minimal.
- Configurable magnet holes (6 mm x 2 mm) with optional crush ribs, chamfer,
  and supportless printing.
- Gridfinity Refined side-insert magnet holes.
- M3 screw holes with countersink or counterbore options.
- Fit-to-drawer mode with configurable padding alignment.
- Screw-together channels for joining multiple baseplates.

### Bins

- Configurable grid size (X, Y) and height (in Gridfinity units, internal mm,
  or external mm).
- Equal compartments via `div_x` / `div_y` dividers.
- Custom compartment layouts with arbitrary placement and per-compartment
  scoop / tab control via the `Compartment` class.
- Finger scoops (adjustable weight 0--1).
- Label tabs (full, auto, left, center, right, or none).
- Stacking lip (normal, reduced, or none).
- Solid bin option with configurable fill ratio.
- Bottom magnet/screw holes (same options as baseplates).
- Interior edge fillets using PythonSCAD's native `.fillet()`.

### Hole options

- Standard magnet holes
- Crush-rib press-fit magnet holes
- Chamfered holes for easy magnet insertion
- Supportless (bridged) holes for printing without supports
- Gridfinity Refined friction-fit holes
- Underside screw mounting (countersink / counterbore)

### Architecture

- All Gridfinity standard dimensions are encoded in a single `GridfinitySpec`
  class, making it easy to reference or override measurements.
- Clean Python API using `dataclasses`, operator overloading (`|`, `-`), and
  PythonSCAD convenience methods (`.up()`, `.rotz()`, etc.).

## Installation

### From source (recommended for now)

Clone the repository alongside your PythonSCAD scripts:

```bash
git clone https://github.com/nomike/pythonscad-gridfinity.git
```

In your PythonSCAD script, add the clone directory to the Python path:

```python
import sys
import os
from openscad import *

sys.path.insert(0, "/path/to/pythonscad-gridfinity")

from pythonscad_gridfinity import GridfinityBaseplate, HoleOptions
```

If your script lives inside the repository (e.g. in `examples/`), you can use
`modelpath()` for a relative path:

```python
import sys
import os
from openscad import *

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(modelpath()))))

from pythonscad_gridfinity import GridfinityBaseplate, HoleOptions
```

### From PyPI (future)

```bash
pip install pythonscad-gridfinity
```

## Quick start

### Thin baseplate (1 x 1)

```python
from openscad import *
import sys
sys.path.insert(0, "/path/to/pythonscad-gridfinity")

from pythonscad_gridfinity import GridfinityBaseplate

bp = GridfinityBaseplate(1, 1, style="thin")
bp.render().color("tomato").show()
```

### Weighted baseplate with magnet holes (4 x 3)

```python
from pythonscad_gridfinity import GridfinityBaseplate, HoleOptions

bp = GridfinityBaseplate(
    4, 3,
    style="weighted",
    hole_options=HoleOptions(magnet_hole=True, crush_ribs=True, chamfer=True),
)
bp.render().color("SteelBlue").show()
```

### Skeletonized baseplate (2 x 2)

```python
from pythonscad_gridfinity import GridfinityBaseplate, HoleOptions

bp = GridfinityBaseplate(
    2, 2,
    style="skeleton",
    hole_options=HoleOptions(magnet_hole=True),
)
bp.render().show()
```

### Simple bin (2 x 1, 3U)

```python
from pythonscad_gridfinity import GridfinityBin

b = GridfinityBin(2, 1, 3)
b.render().color("SteelBlue").show()
```

### Bin with compartments, scoops, and tabs (3 x 2, 6U)

```python
from pythonscad_gridfinity import GridfinityBin, HoleOptions

b = GridfinityBin(
    3, 2, 6,
    div_x=3, div_y=2,
    scoop=1.0,
    tab_style="auto",
    hole_options=HoleOptions(magnet_hole=True),
)
b.render().color("Tomato").show()
```

### Custom compartment layout (3 x 2, 6U)

```python
from pythonscad_gridfinity import GridfinityBin, Compartment, HoleOptions

b = GridfinityBin(
    3, 2, 6,
    compartments=[
        Compartment(0, 0, 2, 2, scoop=1.0, tab_style="left"),
        Compartment(2, 0, 1, 1, scoop=0.5, tab_style="right"),
        Compartment(2, 1, 1, 1, scoop=0.0, tab_style="none"),
    ],
    hole_options=HoleOptions(magnet_hole=True),
)
b.render().color("CadetBlue").show()
```

## Baseplate styles

| Style | Description |
| --- | --- |
| `"thin"` | Minimal baseplate with just the lip profile. Thinnest option. |
| `"weighted"` | Thick bottom (6.4 mm extra) with rectangular weight cutouts for stability. |
| `"skeleton"` | Thick bottom hollowed out, keeping solid material only around hole positions. |
| `"screw_together"` | Thick bottom with horizontal screw channels between cells for joining baseplates. |
| `"screw_together_minimal"` | Screw channels combined with the thin lip profile. |

## Hole option details

The `HoleOptions` dataclass controls magnet and screw hole features:

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `magnet_hole` | `bool` | `False` | Hole for a 6 mm x 2 mm magnet. |
| `screw_hole` | `bool` | `False` | M3 screw hole beneath the magnet hole. |
| `crush_ribs` | `bool` | `False` | Sinusoidal crush ribs for press-fit magnets. |
| `chamfer` | `bool` | `True` | 45-degree chamfer around the hole opening. |
| `supportless` | `bool` | `False` | Bridging layers so the hole prints without supports. |
| `refined_hole` | `bool` | `False` | Gridfinity Refined side-insert style. Mutually exclusive with `magnet_hole`. |

## Bin options

### Tab styles

| Style | Description |
| --- | --- |
| `"full"` | Full-width tab across the entire compartment back wall. |
| `"auto"` | Left-aligned for the leftmost column, right for rightmost, center otherwise. |
| `"left"` | Tab left-aligned on the back wall. |
| `"center"` | Tab centered on the back wall. |
| `"right"` | Tab right-aligned on the back wall. |
| `"none"` | No label tab. |

Tabs are automatically disabled when the bin is shorter than 3 height units.

### Lip styles

| Style | Description |
| --- | --- |
| `"normal"` | Standard stacking lip for stacking bins. |
| `"reduced"` | No lip, height is reduced accordingly. |
| `"none"` | No lip, but total height is preserved. |

### Height modes

| Mode | Interpretation of `height_u` |
| --- | --- |
| `"units"` | Gridfinity height units (1U = 7 mm above the base). Default. |
| `"mm_internal"` | Interior cavity height in millimetres. |
| `"mm_external"` | Total external height in millimetres. |

## API reference

### `GridfinitySpec`

All Gridfinity standard dimensions as class-level constants. Key values:

- `GRID_SIZE = 42.0` -- one grid unit in mm
- `BASEPLATE_HEIGHT = 5.0` -- minimum baseplate height
- `MAGNET_HOLE_RADIUS = 3.25` -- for 6 mm magnets
- `SCREW_HOLE_RADIUS = 1.5` -- M3 screw

See [`spec.py`](pythonscad_gridfinity/spec.py) for the full list.

### `GridfinityBaseplate`

```python
GridfinityBaseplate(
    grid_x, grid_y,
    spec=None,              # GridfinitySpec instance (default: standard)
    style="thin",           # One of: thin, weighted, skeleton, screw_together, screw_together_minimal
    hole_options=None,      # HoleOptions instance
    screw_style="none",     # Underside mounting: none, countersink, counterbore
    min_size_mm=(0, 0),     # Minimum size for fit-to-drawer
    fit_offset=(0, 0),      # Padding alignment (-1..1 per axis)
    screw_diameter=3.35,    # Screw-together channel diameter
    screw_head_diameter=5.0,
    screw_spacing=0.5,
    n_screws=1,             # Screws per grid edge (1-3)
)
```

Call `.render()` to get a PythonSCAD 3D object, then `.show()` or `.export()`.

### `GridfinityBin`

```python
GridfinityBin(
    grid_x, grid_y, height_u,
    spec=None,              # GridfinitySpec instance (default: standard)
    div_x=1,                # Compartments along X (1 = no dividers)
    div_y=1,                # Compartments along Y (1 = no dividers)
    scoop=1.0,              # Scoop weight (0.0 = off, 1.0 = full)
    tab_style="auto",       # One of: full, auto, left, center, right, none
    lip_style="normal",     # One of: normal, reduced, none
    hole_options=None,       # HoleOptions instance for bottom holes
    height_mode="units",    # One of: units, mm_internal, mm_external
    solid=False,            # Fill the interior (no compartments)
    solid_ratio=1.0,        # Fill fraction when solid (0.0--1.0)
    compartments=None,      # List of Compartment objects (overrides div_x/div_y)
)
```

Call `.render()` to get a PythonSCAD 3D object, then `.show()` or `.export()`.

### `Compartment`

Defines a single compartment in a custom layout. Positions and sizes are in
fractional grid units relative to the bin's `grid_x` / `grid_y`.

```python
Compartment(
    x,                      # Grid X position of left edge
    y,                      # Grid Y position of front edge
    w,                      # Grid width (X)
    h,                      # Grid depth (Y)
    scoop=None,             # Scoop weight 0.0--1.0 (None inherits from bin)
    tab_style=None,         # Tab style (None inherits from bin)
)
```

### `HoleOptions`

See the [Hole option details](#hole-option-details) table above.

### Helper functions

The library also exposes lower-level building blocks in case you want to
compose custom objects:

- `block_base_hole(options, spec)` -- single combined magnet/screw hole
- `hole_pattern(obj, spec)` -- place an object at the four hole positions
- `refined_hole(spec)` -- Gridfinity Refined magnet hole geometry

## Project structure

```text
pythonscad-gridfinity/
  pythonscad_gridfinity/
    __init__.py       # Package exports
    spec.py           # GridfinitySpec (all standard dimensions)
    helpers.py        # Utility functions (rounded_square, pattern_grid, etc.)
    holes.py          # HoleOptions and hole geometry builders
    baseplate.py      # GridfinityBaseplate class
    bin.py            # GridfinityBin class
  examples/
    basic_baseplate.py
    basic_bin.py
  pyproject.toml
  LICENSE
  README.md
```

## Running from the command line

You can render and export baseplates without opening the PythonSCAD GUI:

```bash
pythonscad --trust-python -o baseplate.stl my_baseplate_script.py
```

The `--trust-python` flag is required to enable the Python interpreter.

## Acknowledgements

This library would not exist without the following projects and people:

- **[Zack Freedman](https://www.youtube.com/c/ZackFreedman)** for designing the
  [Gridfinity](https://www.youtube.com/watch?v=ra_9zU-mnl8) modular storage
  system and releasing it to the community.

- **[gridfinity-rebuilt-openscad](https://github.com/kennetek/gridfinity-rebuilt-openscad)**
  by [kennetek](https://github.com/kennetek) -- the definitive OpenSCAD
  implementation of the Gridfinity standard. This library's grid dimensions,
  base/lip profile geometry, stacking lip cross-section, baseplate styles
  (thin, weighted, skeleton, screw-together), bin construction (wall heights,
  compartment dividers, finger scoops, label tabs), and hole specifications
  (magnet, screw, crush-rib, supportless, and Gridfinity Refined) are all
  derived from gridfinity-rebuilt-openscad.

- **[cq-gridfinity](https://github.com/michaelgale/cq-gridfinity)** by
  [Michael Gale](https://github.com/michaelgale) -- a CadQuery/Python
  implementation of Gridfinity. Used as an additional reference for
  cross-checking geometry calculations and for informing the Python-oriented
  API design of this library.

- **[PythonSCAD](https://pythonscad.org/)** for making Python-based 3D
  modelling possible with a native Python API on top of the OpenSCAD engine.

## License

[MIT](LICENSE)
