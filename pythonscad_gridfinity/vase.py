"""Gridfinity spiral/vase-mode bin generator.

Creates bins designed for spiral (vase) mode printing.  The entire bin
is a single continuous wall so the slicer can print it in one spiral
path.  This is much faster than normal printing but limits the geometry
to single-wall features.

Usage:
    from pythonscad_gridfinity import GridfinityVaseBin

    v = GridfinityVaseBin(2, 1, 6)
    v.render().show()
"""

import math

from openscad import *

from .spec import GridfinitySpec
from .helpers import (
    rounded_square,
    rounded_square_3d,
    grid_positions,
    pattern_circular,
)


class GridfinityVaseBin:
    """Parametric Gridfinity bin for spiral/vase-mode printing.

    All walls are a single perimeter (2 * nozzle width) so the slicer
    can print them in a continuous spiral.  A "magic slice" is inserted
    to prevent the slicer from ignoring the bin's interior.

    Args:
        grid_x: Number of grid units along X.
        grid_y: Number of grid units along Y.
        height_u: Height in Gridfinity units (1U = 7 mm above the base).
        spec: GridfinitySpec instance.
        nozzle: Nozzle/extrusion width in mm.  Walls are 2 * nozzle.
        layer_height: Slicer layer height in mm.
        bottom_layers: Number of solid bottom layers.
        n_divx: Number of X compartments (dividers are single-wall).
        enable_lip: Include the stacking lip.
        enable_holes: Add magnet holes in the base.
        enable_zsnap: Snap height to nearest 7 mm increment.
    """

    def __init__(
        self,
        grid_x,
        grid_y,
        height_u,
        *,
        spec=None,
        nozzle=0.6,
        layer_height=0.35,
        bottom_layers=3,
        n_divx=1,
        enable_lip=True,
        enable_holes=True,
        enable_zsnap=False,
    ):
        self.spec = spec or GridfinitySpec()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.height_u = height_u
        self.nozzle = nozzle
        self.layer_height = layer_height
        self.bottom_layers = max(bottom_layers, 1)
        self.n_divx = max(n_divx, 1)
        self.enable_lip = enable_lip
        self.enable_holes = enable_holes
        self.enable_zsnap = enable_zsnap

    # ------------------------------------------------------------------
    # Height
    # ------------------------------------------------------------------

    def _wall_height(self):
        """Wall height in mm above the base profile."""
        s = self.spec
        raw = self.height_u * s.HEIGHT_UNIT
        if self.enable_zsnap:
            total = raw + s.BASE_HEIGHT
            if total % 7 != 0:
                total = total + 7 - (total % 7)
            raw = total - s.BASE_HEIGHT
        lip_h = s.STACKING_LIP_HEIGHT if self.enable_lip else 0
        return raw - lip_h

    # ------------------------------------------------------------------
    # Base shell
    # ------------------------------------------------------------------

    def _build_base_shell(self):
        """Build a thin-walled outer shell that follows the base profile."""
        s = self.spec
        cell = s.GRID_SIZE
        wall_t = 2 * self.nozzle
        top_dim = s.BASE_TOP_DIMENSIONS
        top_r = s.BASE_TOP_RADIUS
        profile = s.BASE_PROFILE

        inner = [top_dim[0] - 2 * top_r, top_dim[1] - 2 * top_r]
        thin = 0.01
        overlap = 0.001

        z1 = profile[1][1]
        z2 = profile[2][1]
        z3 = profile[3][1]
        z4 = s.BASE_HEIGHT

        r0 = top_r - profile[3][0]
        r1 = top_r - profile[3][0] + profile[1][0]
        r3 = top_r

        def rr(rad):
            return rounded_square(
                [inner[0] + 2 * rad, inner[1] + 2 * rad],
                max(rad, 0.01),
                center=True,
            )

        def make_shell(r_func, r0v, r1v, r3v):
            bot = r_func(r0v).linear_extrude(height=thin)
            top = r_func(r1v).linear_extrude(height=thin).up(z1)
            sh = hull(bot, top)
            sh = sh | r_func(r1v).linear_extrude(
                height=(z2 - z1) + 2 * overlap
            ).up(z1 - overlap)
            bot2 = r_func(r1v).linear_extrude(height=thin).up(z2 - overlap)
            top2 = r_func(r3v).linear_extrude(height=thin).up(z3)
            sh = sh | hull(bot2, top2)
            sh = sh | r_func(r3v).linear_extrude(
                height=(z4 - z3) + overlap
            ).up(z3 - overlap)
            return sh

        outer_cell = make_shell(rr, r0, r1, r3)

        ir0 = max(r0 - wall_t, 0.01)
        ir1 = max(r1 - wall_t, 0.01)
        ir3 = max(r3 - wall_t, 0.01)
        inner_cell = make_shell(rr, ir0, ir1, ir3)

        d_bottom = self.layer_height * self.bottom_layers
        inner_cell = inner_cell - cube(
            [top_dim[0] + 1, top_dim[1] + 1, d_bottom + overlap],
            center=True,
        ).up((d_bottom + overlap) / 2 - overlap)

        shell = outer_cell - inner_cell

        base = None
        for cx, cy in grid_positions([self.grid_x, self.grid_y], cell, center=True):
            placed = shell.translate([cx, cy, 0])
            base = placed if base is None else (base | placed)

        # Solid bottom slab
        grid_outer = [
            self.grid_x * cell - s.BASE_GAP,
            self.grid_y * cell - s.BASE_GAP,
        ]
        if d_bottom > 0:
            slab = rounded_square_3d(grid_outer, top_r, d_bottom, center_xy=True)
            base = base | slab

        return base

    # ------------------------------------------------------------------
    # Walls and lip
    # ------------------------------------------------------------------

    def _build_walls(self):
        """Build the single-wall bin body above the base."""
        s = self.spec
        cell = s.GRID_SIZE
        wall_t = 2 * self.nozzle
        wall_h = self._wall_height()
        outer = [
            self.grid_x * cell - s.BASE_GAP,
            self.grid_y * cell - s.BASE_GAP,
        ]
        r = s.BASE_TOP_RADIUS

        outer_shell = rounded_square_3d(outer, r, wall_h, center_xy=True)
        inner_size = [outer[0] - 2 * wall_t, outer[1] - 2 * wall_t]
        inner_shell = rounded_square_3d(
            inner_size, max(r - wall_t, 0.01), wall_h + 0.01, center_xy=True
        )
        walls = (outer_shell - inner_shell).up(s.BASE_HEIGHT)

        return walls

    def _build_lip_shell(self):
        """Build a single-wall stacking lip."""
        s = self.spec
        cell = s.GRID_SIZE
        wall_t = 2 * self.nozzle
        wall_h = self._wall_height()
        wall_top_z = s.BASE_HEIGHT + wall_h
        lip = s.STACKING_LIP_PROFILE
        r_top = s.BASE_TOP_RADIUS

        outer = [
            self.grid_x * cell - s.BASE_GAP,
            self.grid_y * cell - s.BASE_GAP,
        ]
        inner_dim = [outer[0] - 2 * r_top, outer[1] - 2 * r_top]

        def rr(radius):
            return rounded_square(
                [inner_dim[0] + 2 * radius, inner_dim[1] + 2 * radius],
                max(radius, 0.01),
                center=True,
            )

        thin = 0.01
        overlap = 0.001

        r_base_offset = r_top - s.STACKING_LIP_DEPTH
        r0 = r_base_offset + lip[0][0]
        r1 = r_base_offset + lip[1][0]
        r3 = r_base_offset + lip[3][0]

        h1 = lip[1][1]
        h2 = lip[2][1]
        h3 = lip[3][1]

        r_wall_inner = r_top - wall_t
        support_h = s.STACKING_LIP_SUPPORT_HEIGHT

        z_sup = wall_top_z - support_h
        z_wt = wall_top_z
        z_h1 = wall_top_z + h1
        z_h2 = wall_top_z + h2
        z_h3 = wall_top_z + h3

        def slab(r, z):
            return rr(r).linear_extrude(height=thin).up(z)

        outer_env = rr(r_top).linear_extrude(height=z_h3 - z_sup).up(z_sup)

        inner_env = hull(slab(r_wall_inner, z_sup - overlap), slab(r0, z_wt))
        inner_env = inner_env | hull(slab(r0, z_wt - overlap), slab(r1, z_h1))
        inner_env = inner_env | rr(r1).linear_extrude(
            height=(h2 - h1) + 2 * overlap
        ).up(z_h1 - overlap)
        inner_env = inner_env | hull(
            slab(r1, z_h2 - overlap), slab(r3 + overlap, z_h3 + overlap)
        )

        return outer_env - inner_env

    # ------------------------------------------------------------------
    # Dividers
    # ------------------------------------------------------------------

    def _build_dividers(self):
        """Build single-wall dividers between compartments."""
        s = self.spec
        cell = s.GRID_SIZE
        wall_t = 2 * self.nozzle
        wall_h = self._wall_height()
        n = self.n_divx

        if n <= 1:
            return None

        outer = [
            self.grid_x * cell - s.BASE_GAP,
            self.grid_y * cell - s.BASE_GAP,
        ]
        d_bottom = self.layer_height * self.bottom_layers
        spacing = outer[0] / n

        dividers = None
        for i in range(1, n):
            x_pos = -outer[0] / 2 + i * spacing
            div = cube(
                [wall_t, outer[1] - 2 * wall_t, wall_h - d_bottom],
                center=True,
            ).translate([x_pos, 0, s.BASE_HEIGHT + d_bottom + (wall_h - d_bottom) / 2])
            dividers = div if dividers is None else (dividers | div)

        return dividers

    # ------------------------------------------------------------------
    # Magic slice
    # ------------------------------------------------------------------

    def _magic_slice(self):
        """Thin vertical slice to prevent slicer from ignoring the center.

        The slicer needs a continuous contour; this near-invisible slice
        forces it to recognize the interior.
        """
        s = self.spec
        cell = s.GRID_SIZE
        d_bottom = self.layer_height * self.bottom_layers
        wall_h = self._wall_height()
        outer = [
            self.grid_x * cell - s.BASE_GAP,
            self.grid_y * cell - s.BASE_GAP,
        ]

        return cube(
            [0.005, outer[1], wall_h + s.BASE_HEIGHT - d_bottom],
            center=True,
        ).up(d_bottom + (wall_h + s.BASE_HEIGHT - d_bottom) / 2).rotz(90)

    # ------------------------------------------------------------------
    # Base cross pattern
    # ------------------------------------------------------------------

    def _base_cross_pattern(self):
        """X-pattern on the base for baseplate attachment."""
        s = self.spec
        cell = s.GRID_SIZE
        wall_t = 2 * self.nozzle
        d_bottom = self.layer_height * self.bottom_layers
        half_cell = cell / 2

        arm = cube([wall_t, cell, d_bottom], center=True).up(d_bottom / 2)
        cross = arm | arm.rotz(90)

        pattern = None
        for cx, cy in grid_positions([self.grid_x, self.grid_y], cell, center=True):
            spokes = pattern_circular(
                cube([wall_t, half_cell, s.BASE_PROFILE_HEIGHT]).translate(
                    [-wall_t / 2, 0, 0]
                ),
                4,
            ).translate([cx, cy, 0])
            pattern = spokes if pattern is None else (pattern | spokes)

        return pattern

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self):
        """Generate the vase-mode bin geometry.

        Returns:
            A 3D PythonSCAD object.
        """
        base = self._build_base_shell()
        walls = self._build_walls()
        result = base | walls

        if self.enable_lip:
            lip = self._build_lip_shell()
            result = result | lip

        dividers = self._build_dividers()
        if dividers is not None:
            result = result | dividers

        cross = self._base_cross_pattern()
        if cross is not None:
            result = result & (result | cross)

        magic = self._magic_slice()
        result = result - magic

        return result
