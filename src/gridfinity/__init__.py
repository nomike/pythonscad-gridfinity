"""PythonSCAD Gridfinity library.

Generate Gridfinity-compatible baseplates and bins using PythonSCAD's
Python API.

Quick start::

    from openscad import *
    from gridfinity import GridfinityBaseplate, GridfinityBin, HoleOptions

    bp = GridfinityBaseplate(4, 3, style="weighted",
                             hole_options=HoleOptions(magnet_hole=True))
    bp.render().color("tomato").show()

    b = GridfinityBin(3, 2, 6, div_x=3, div_y=2)
    b.render().color("SteelBlue").show()
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pythonscad-gridfinity")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

from .baseplate import BASEPLATE_STYLES, SCREW_STYLES, GridfinityBaseplate
from .bin import (
    HEIGHT_MODES,
    LIP_STYLES,
    TAB_STYLES,
    Compartment,
    GridfinityBin,
)
from .helpers import cut_chamfered_cylinder
from .holes import HoleOptions, block_base_hole, hole_pattern, refined_hole
from .spec import GridfinitySpec
from .vase import GridfinityVaseBin

__all__ = [
    "BASEPLATE_STYLES",
    "HEIGHT_MODES",
    "LIP_STYLES",
    "SCREW_STYLES",
    "TAB_STYLES",
    "Compartment",
    "GridfinityBaseplate",
    "GridfinityBin",
    "GridfinitySpec",
    "GridfinityVaseBin",
    "HoleOptions",
    "__version__",
    "block_base_hole",
    "cut_chamfered_cylinder",
    "hole_pattern",
    "refined_hole",
]
