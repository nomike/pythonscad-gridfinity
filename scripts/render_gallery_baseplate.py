"""Render a representative baseplate preview for the README gallery."""

import os
import sys

from openscad import *

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(modelpath()))),
        "src",
    ),
)

from gridfinity import GridfinityBaseplate, HoleOptions

fn = 48

bp = GridfinityBaseplate(
    2,
    2,
    style="weighted",
    hole_options=HoleOptions(magnet_hole=True, chamfer=True),
)
bp.render().color("SteelBlue").show()
