"""Example: Generate various Gridfinity baseplates.

Open this file in PythonSCAD to render the baseplates.
The modelpath() call ensures the package is found relative to this script.
"""

import sys
import os
from openscad import *

fn = 64

# Add the parent directory so the package can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(modelpath()))))

from pythonscad_gridfinity import GridfinityBaseplate, HoleOptions

# --- Example 1: Simple thin baseplate (1x1) ---
bp_thin = GridfinityBaseplate(1, 1, style="thin")
bp_thin.render().color("tomato").show()

# --- Example 2: 3x2 weighted baseplate with plain circular magnet holes ---
bp_weighted = GridfinityBaseplate(
    3,
    2,
    style="weighted",
    hole_options=HoleOptions(magnet_hole=True, chamfer=True),
)
bp_weighted.render().color("SteelBlue").right(150).show()

# --- Example 3: 2x2 skeletonized baseplate with crush-rib press-fit magnets ---
bp_skel = GridfinityBaseplate(
    2,
    2,
    style="skeleton",
    hole_options=HoleOptions(magnet_hole=True, crush_ribs=True),
)
bp_skel.render().color("DarkOliveGreen").right(300).show()

# --- Example 4: 2x2 screw-together baseplate with countersink screws ---
bp_screw = GridfinityBaseplate(
    2,
    2,
    style="screw_together",
    screw_style="countersink",
    hole_options=HoleOptions(magnet_hole=True, screw_hole=True),
)
bp_screw.render().color("SlateBlue").translate([0, -150, 0]).show()

# --- Example 5: 2x1 screw-together minimal baseplate with counterbore screws ---
bp_screw_min = GridfinityBaseplate(
    2,
    1,
    style="screw_together_minimal",
    screw_style="counterbore",
    hole_options=HoleOptions(magnet_hole=True, chamfer=True),
)
bp_screw_min.render().color("Peru").translate([150, -150, 0]).show()
