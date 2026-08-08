"""Render a representative standard bin preview for the README gallery."""

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

from gridfinity import GridfinityBin, HoleOptions

fn = 48

GridfinityBin(
    2,
    1,
    3,
    div_x=2,
    scoop=1.0,
    tab_style="auto",
    hole_options=HoleOptions(magnet_hole=True),
).render().color("Tomato").show()
