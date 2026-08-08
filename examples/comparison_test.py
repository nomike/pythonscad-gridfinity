import sys
import os
from openscad import *

fn = 30
# Add the parent directory so the package can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(modelpath()))))

from pythonscad_gridfinity import GridfinityBin

bin_simple = GridfinityBin(1, 1, 2)

bin_simple.render().color("Tomato").show()
