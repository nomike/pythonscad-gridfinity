import sys
import os
from openscad import *

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(modelpath()))))

from pythonscad_gridfinity import GridfinityBin
from pythonscad_gridfinity.spec import GridfinitySpec

s = GridfinitySpec()
b = GridfinityBin(1, 1, 2)

# Render only the lip + wall ring (no base, no infill).
# _build_lip() now returns wall_ring | swept lip (matching OpenSCAD render_wall).
result = b._build_lip()
result.color("Tomato").show()
