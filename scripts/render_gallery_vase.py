"""Render a representative vase/lite bin preview for the README gallery."""

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

from gridfinity import GridfinityVaseBin

fn = 48

GridfinityVaseBin(2, 1, 4, n_divx=2, nozzle=0.4).render().color("CadetBlue").show()
