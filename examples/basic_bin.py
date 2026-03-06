"""Example: Generate various Gridfinity bins.

Open this file in PythonSCAD to render the bins.
The modelpath() call ensures the package is found relative to this script.
"""

import sys
import os
from openscad import *

fn = 64

# Add the parent directory so the package can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(modelpath()))))

from pythonscad_gridfinity import GridfinityBin, Compartment, HoleOptions

# --- Example 1: Simple 2x1 bin, plain magnet holes (glued-in) ---
bin_simple = GridfinityBin(
    2,
    1,
    3,
    hole_options=HoleOptions(magnet_hole=True),
)
bin_simple.render().color("SteelBlue").show()

# --- Example 2: 3x2 bin, crush-rib press-fit magnet holes + screw holes ---
bin_full = GridfinityBin(
    3,
    2,
    6,
    div_x=3,
    div_y=2,
    scoop=1.0,
    tab_style="auto",
    hole_options=HoleOptions(
        magnet_hole=True,
        screw_hole=True,
        crush_ribs=True,
        chamfer=True,
    ),
)
bin_full.render().color("Tomato").translate([150, 0, 0]).show()

# --- Example 3: 2x1 bin, screw holes only, no stacking lip ---
bin_nolip = GridfinityBin(
    2,
    1,
    4,
    lip_style="none",
    hole_options=HoleOptions(screw_hole=True, chamfer=True),
)
bin_nolip.render().color("DarkOliveGreen").translate([0, -80, 0]).show()

# --- Example 4: 1x1 bin, Gridfinity Refined side-insert magnet holes ---
bin_refined = GridfinityBin(
    1,
    1,
    6,
    hole_options=HoleOptions(refined_hole=True),
)
bin_refined.render().color("SlateBlue").translate([150, -80, 0]).show()

# --- Example 5: 3x1 bin, magnet + screw combo, supportless printing ---
bin_tabs = GridfinityBin(
    3,
    1,
    5,
    div_x=3,
    scoop=0.0,
    tab_style="full",
    hole_options=HoleOptions(
        magnet_hole=True,
        screw_hole=True,
        supportless=True,
        chamfer=True,
    ),
)
bin_tabs.render().color("Peru").translate([0, -160, 0]).show()

# --- Example 6: 1x1 solid bin (no interior, no holes) ---
bin_solid = GridfinityBin(1, 1, 6, solid=True)
bin_solid.render().color("MediumOrchid").translate([300, 0, 0]).show()

# --- Example 7: 3x2 bin with custom compartment layout ---
# One large compartment on the left, two stacked on the right.
bin_custom = GridfinityBin(
    3, 2, 6,
    compartments=[
        Compartment(0, 0, 2, 2, scoop=1.0, tab_style="left"),
        Compartment(2, 0, 1, 1, scoop=0.5, tab_style="right"),
        Compartment(2, 1, 1, 1, scoop=0.0, tab_style="none"),
    ],
    hole_options=HoleOptions(magnet_hole=True),
)
bin_custom.render().color("CadetBlue").translate([300, -80, 0]).show()
