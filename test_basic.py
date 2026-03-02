"""Minimal test: verify the library imports and a thin baseplate renders."""

import sys
import os
from openscad import *

sys.path.insert(0, os.path.dirname(os.path.abspath(modelpath())))

from pythonscad_gridfinity import GridfinityBaseplate

# Simple 1x1 thin baseplate
bp = GridfinityBaseplate(1, 1, style="thin")
result = bp.render()
result.show()
