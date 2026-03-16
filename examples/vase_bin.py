"""Example: Generate Gridfinity spiral/vase-mode bins.

These bins are designed for spiral (vase) mode printing in the slicer.
All walls are single-perimeter so the slicer can print in one
continuous spiral path, resulting in much faster print times.

Open this file in PythonSCAD to render the bins.
"""

import sys
import os
from openscad import *

fn = 64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(modelpath()))))

from pythonscad_gridfinity import GridfinityVaseBin

# --- Example 1: Simple 1x1 vase bin ---
vase_simple = GridfinityVaseBin(1, 1, 6)
vase_simple.render().color("Tomato").show()

# --- Example 2: 3x1 vase bin with dividers ---
vase_div = GridfinityVaseBin(
    3,
    1,
    6,
    n_divx=3,
    nozzle=0.4,
)
vase_div.render().color("SteelBlue").translate([150, 0, 0]).show()

# --- Example 3: 2x2 vase bin, no lip, height snapped ---
vase_nolip = GridfinityVaseBin(
    2,
    2,
    4,
    enable_lip=False,
    enable_zsnap=True,
    bottom_layers=5,
)
vase_nolip.render().color("DarkOliveGreen").translate([0, -120, 0]).show()

# --- Example 4: 1x1 vase bin without magnet holes ---
vase_noholes = GridfinityVaseBin(
    1,
    1,
    3,
    enable_holes=False,
    nozzle=0.6,
    layer_height=0.2,
)
vase_noholes.render().color("MediumOrchid").translate([150, -120, 0]).show()

# --- Example 5: 2x1 vase bin with all refinements ---
vase_full = GridfinityVaseBin(
    2,
    1,
    6,
    n_divx=2,
    enable_scoop_chamfer=True,
    enable_pinch=True,
    enable_front_inset=True,
)
vase_full.render().color("Teal").translate([0, -240, 0]).show()

# --- Example 6: 1x1 vase bin without refinements ---
vase_plain = GridfinityVaseBin(
    1,
    1,
    6,
    enable_scoop_chamfer=False,
    enable_pinch=False,
    enable_front_inset=False,
)
vase_plain.render().color("SlateBlue").translate([150, -240, 0]).show()
