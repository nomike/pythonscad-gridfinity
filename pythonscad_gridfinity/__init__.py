"""PythonSCAD Gridfinity library.

Generate Gridfinity-compatible baseplates and bins using PythonSCAD's
Python API.

Quick start::

    from openscad import *
    from pythonscad_gridfinity import GridfinityBaseplate, GridfinityBin, HoleOptions

    bp = GridfinityBaseplate(4, 3, style="weighted",
                             hole_options=HoleOptions(magnet_hole=True))
    bp.render().color("tomato").show()

    b = GridfinityBin(3, 2, 6, div_x=3, div_y=2)
    b.render().color("SteelBlue").show()
"""

__version__ = "0.2.0"

from .spec import GridfinitySpec
from .holes import HoleOptions, block_base_hole, hole_pattern, refined_hole
from .baseplate import GridfinityBaseplate, BASEPLATE_STYLES, SCREW_STYLES
from .bin import GridfinityBin, Compartment, TAB_STYLES, LIP_STYLES, HEIGHT_MODES
from .helpers import cut_chamfered_cylinder
from .vase import GridfinityVaseBin

__all__ = [
    "GridfinitySpec",
    "HoleOptions",
    "GridfinityBaseplate",
    "BASEPLATE_STYLES",
    "SCREW_STYLES",
    "GridfinityBin",
    "Compartment",
    "TAB_STYLES",
    "LIP_STYLES",
    "HEIGHT_MODES",
    "block_base_hole",
    "hole_pattern",
    "refined_hole",
    "cut_chamfered_cylinder",
    "GridfinityVaseBin",
]
