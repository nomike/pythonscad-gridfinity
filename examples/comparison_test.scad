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
    1,
    1,
    2,
    hole_options=HoleOptions(magnet_hole=True),
)
bin_simple.render().show()
