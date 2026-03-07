"""Gridfinity bin generator.

Creates parametric Gridfinity-compatible bins with configurable
compartments, scoops, label tabs, stacking lip, and bottom holes.

Usage:
    from pythonscad_gridfinity import GridfinityBin, HoleOptions

    b = GridfinityBin(3, 2, 6)
    b.render().show()

    # 3x2 bin with compartments, scoops, tabs, and magnet holes
    b = GridfinityBin(
        3, 2, 6,
        div_x=3, div_y=2,
        scoop=1.0,
        tab_style="auto",
        hole_options=HoleOptions(magnet_hole=True),
    )
    b.render().show()

    # Custom compartment layout
    from pythonscad_gridfinity import Compartment
    b = GridfinityBin(
        3, 2, 6,
        compartments=[
            Compartment(0, 0, 2, 1, scoop=1.0, tab_style="left"),
            Compartment(2, 0, 1, 2, scoop=0.5, tab_style="right"),
            Compartment(0, 1, 2, 1, tab_style="none"),
        ],
        hole_options=HoleOptions(magnet_hole=True),
    )
    b.render().show()
"""

import math
from dataclasses import dataclass

from openscad import *

from .spec import GridfinitySpec
from .holes import block_base_hole, hole_pattern
from .helpers import (
    rounded_square,
    rounded_square_3d,
    grid_positions,
    cut_chamfered_cylinder,
)


TAB_STYLES = ("full", "auto", "left", "center", "right", "none")
LIP_STYLES = ("normal", "reduced", "none", "subtractive")
HEIGHT_MODES = ("units", "mm_internal", "mm_external")


@dataclass
class Compartment:
    """Defines one compartment in a custom layout.

    Positions and sizes are in fractional grid units relative to the
    bin's grid_x / grid_y.  For example, in a 3x2 bin a compartment
    at ``(0, 0)`` with size ``(1.5, 1)`` occupies the left half of
    the bottom row.

    Compartments may overlap — the union of all cutters is subtracted
    from the bin body.

    Args:
        x: Fractional grid X position of the compartment's left edge.
        y: Fractional grid Y position of the compartment's front edge.
        w: Fractional grid width (X).
        h: Fractional grid depth (Y).
        scoop: Scoop weight 0.0–1.0.  None inherits from the bin.
        tab_style: Tab placement.  None inherits from the bin.
    """

    x: float
    y: float
    w: float
    h: float
    scoop: float | None = None
    tab_style: str | None = None

    def __post_init__(self):
        if self.w <= 0 or self.h <= 0:
            raise ValueError("Compartment w and h must be positive")
        if self.tab_style is not None and self.tab_style not in TAB_STYLES:
            raise ValueError(
                f"Unknown tab_style '{self.tab_style}'. Must be one of {TAB_STYLES}"
            )


class GridfinityBin:
    """Parametric Gridfinity bin generator.

    Generates bins that mate with Gridfinity baseplates. Supports
    configurable grid size, height, compartment layout, scoops, label
    tabs, stacking lip, and bottom magnet/screw holes.

    Args:
        grid_x: Number of grid units along X (each unit is 42 mm).
        grid_y: Number of grid units along Y.
        height_u: Height value. Interpretation depends on *height_mode*:
            - ``"units"``: Gridfinity height units (1U = 7 mm above the base).
            - ``"mm_internal"``: Interior cavity height in mm.
            - ``"mm_external"``: Total external height in mm.
        spec: GridfinitySpec instance. Uses standard dimensions if None.
        div_x: Number of compartments along X (1 = no dividers).
        div_y: Number of compartments along Y (1 = no dividers).
        scoop: Scoop weight from 0.0 (off) to 1.0 (full radius).
        tab_style: Label tab placement. One of TAB_STYLES.
        lip_style: Stacking lip style. One of LIP_STYLES.
        hole_options: HoleOptions for bottom magnet/screw holes.
        height_mode: How to interpret *height_u*. One of HEIGHT_MODES.
        solid: If True, fill the interior (no compartments).
        solid_ratio: When solid, fraction of interior to fill (0.0--1.0).
        compartments: List of Compartment objects for custom layouts.
            When provided, *div_x* / *div_y* are ignored and each
            Compartment specifies its own position, size, scoop, and
            tab style in fractional grid units.  Compartments may overlap.
        lite: If True, build a lite bin with a hollow shell base instead
            of the standard solid base profile.  Uses less material and
            prints faster.
        base_thickness: Bottom layer thickness in mm for lite bins
            (default 1.0).  Ignored when *lite* is False.
        half_grid: If True, use half-size (21 mm) grid bases instead of
            the standard 42 mm.  Implies ``only_corners`` for hole
            placement.
        cut_cylinders: If True, use cylindrical cutouts instead of
            rectangular compartments.  Useful for tool holders.
        cylinder_diameter: Diameter of cylindrical cutouts in mm.
        cylinder_chamfer: Chamfer radius around the top rim of each
            cylindrical cutout in mm.
        enable_zsnap: If True, snap the total height to the nearest
            7 mm increment (Gridfinity unit boundary).
        only_corners: If True, place magnet/screw holes only at the
            four outer corners of the bin instead of at every grid cell.
        depth: Override compartment depth in mm.  0 means use the
            default (full interior height).
        place_tab: ``"everywhere"`` puts tabs on every compartment;
            ``"top_left"`` only on the top-left compartment.
        enable_thumbscrew: If True, add a Gridfinity Refined thumbscrew
            hole (M15 x 1.5 compatible) in the center of each base
            unit for secure baseplate attachment.
        scoop_chamfer: If True, add a 45-degree chamfer at the top edge
            of the scoop for easier part removal.
    """

    PLACE_TAB_OPTIONS = ("everywhere", "top_left")

    def __init__(
        self,
        grid_x,
        grid_y,
        height_u,
        *,
        spec=None,
        div_x=1,
        div_y=1,
        scoop=1.0,
        tab_style="auto",
        lip_style="normal",
        hole_options=None,
        height_mode="units",
        solid=False,
        solid_ratio=1.0,
        compartments=None,
        lite=False,
        base_thickness=1.0,
        half_grid=False,
        cut_cylinders=False,
        cylinder_diameter=10.0,
        cylinder_chamfer=0.5,
        enable_zsnap=False,
        only_corners=False,
        depth=0,
        place_tab="everywhere",
        enable_thumbscrew=False,
        scoop_chamfer=False,
    ):
        self.spec = spec or GridfinitySpec()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.height_u = height_u
        self.div_x = max(div_x, 1)
        self.div_y = max(div_y, 1)
        self.scoop = max(0.0, min(float(scoop), 1.0))
        self.tab_style = tab_style
        self.lip_style = lip_style
        self.hole_options = hole_options
        self.height_mode = height_mode
        self.solid = solid
        self.solid_ratio = max(0.0, min(float(solid_ratio), 1.0))
        self.compartments = compartments
        self.lite = lite
        self.base_thickness = max(0.0, float(base_thickness))
        self.half_grid = half_grid
        self.cut_cylinders = cut_cylinders
        self.cylinder_diameter = float(cylinder_diameter)
        self.cylinder_chamfer = float(cylinder_chamfer)
        self.enable_zsnap = enable_zsnap
        self.only_corners = only_corners
        self.depth = float(depth)
        self.place_tab = place_tab
        self.enable_thumbscrew = enable_thumbscrew
        self.scoop_chamfer = scoop_chamfer

        if tab_style not in TAB_STYLES:
            raise ValueError(
                f"Unknown tab_style '{tab_style}'. Must be one of {TAB_STYLES}"
            )
        if lip_style not in LIP_STYLES:
            raise ValueError(
                f"Unknown lip_style '{lip_style}'. Must be one of {LIP_STYLES}"
            )
        if height_mode not in HEIGHT_MODES:
            raise ValueError(
                f"Unknown height_mode '{height_mode}'. Must be one of {HEIGHT_MODES}"
            )
        if place_tab not in self.PLACE_TAB_OPTIONS:
            raise ValueError(
                f"Unknown place_tab '{place_tab}'. "
                f"Must be one of {self.PLACE_TAB_OPTIONS}"
            )

    # ------------------------------------------------------------------
    # Height calculations
    # ------------------------------------------------------------------

    def _wall_height_mm(self):
        """Height of the main walls above the base, excluding the lip.

        In the original, ``height_mm`` *includes* ``BASE_HEIGHT`` and
        *excludes* ``STACKING_LIP_HEIGHT``.  For units mode the raw
        value is ``height_u * HEIGHT_UNIT``; the wall portion above
        ``BASE_HEIGHT`` is ``h - BASE_HEIGHT``.

        Lip style "none" preserves total height by extending the wall
        into the lip zone.  "reduced"/"subtractive" simply omit the lip
        without adjusting the wall height.
        """
        s = self.spec
        if self.height_mode == "units":
            h = self.height_u * s.HEIGHT_UNIT
            if self.enable_zsnap:
                if h % 7 != 0:
                    h = h + 7 - (h % 7)
            h -= s.BASE_HEIGHT
            if self.lip_style == "none":
                h += s.STACKING_LIP_HEIGHT
            return h
        elif self.height_mode == "mm_internal":
            return self.height_u + s.FLOOR_THICKNESS
        else:  # mm_external
            lip_h = s.STACKING_LIP_HEIGHT if self.lip_style == "normal" else 0.0
            return self.height_u - s.BASE_HEIGHT - lip_h

    def _total_height_mm(self):
        """Total height from z=0 (base bottom) to the very top."""
        s = self.spec
        wall_h = self._wall_height_mm()
        lip_h = s.STACKING_LIP_HEIGHT if self.lip_style == "normal" else 0.0
        return s.BASE_HEIGHT + wall_h + lip_h

    # ------------------------------------------------------------------
    # Grid cell size
    # ------------------------------------------------------------------

    @property
    def _cell_size(self):
        """Effective grid cell size in mm (42 or 21 for half_grid)."""
        s = self.spec
        return s.GRID_SIZE / (2 if self.half_grid else 1)

    # ------------------------------------------------------------------
    # Outer dimensions
    # ------------------------------------------------------------------

    def _outer_dimensions(self):
        """XY outer dimensions of the bin body (at the base top level).

        Returns:
            [width, depth] in mm.
        """
        s = self.spec
        cell = self._cell_size
        return [
            self.grid_x * cell - s.BASE_GAP,
            self.grid_y * cell - s.BASE_GAP,
        ]

    # ------------------------------------------------------------------
    # Base (per-cell mating profile)
    # ------------------------------------------------------------------

    def _build_base(self):
        """Build the base profile that mates with the baseplate.

        Uses hull-of-slices following BASE_PROFILE, one profile per grid
        cell, all unioned together.

        Returns:
            A 3D PythonSCAD object centered in XY, bottom at z=0.
        """
        s = self.spec
        profile = s.BASE_PROFILE
        cell = self._cell_size

        # Dimensions at the top of the base profile for one cell
        top_dim = [cell - s.BASE_GAP, cell - s.BASE_GAP]
        top_r = s.BASE_TOP_RADIUS

        inner = [top_dim[0] - 2 * top_r, top_dim[1] - 2 * top_r]

        def rr(radius):
            """Rounded rectangle at the given corner radius."""
            return rounded_square(
                [inner[0] + 2 * radius, inner[1] + 2 * radius],
                max(radius, 0.01),
                center=True,
            )

        thin = 0.01
        overlap = 0.001

        # Profile heights
        z1 = profile[1][1]  # 0.8
        z2 = profile[2][1]  # 2.6
        z3 = profile[3][1]  # 4.75 = BASE_PROFILE_HEIGHT
        z4 = s.BASE_HEIGHT  # 7.0

        # Radii at each profile point (inward from the top radius)
        r0 = top_r - profile[3][0]  # 3.75 - 2.95 = 0.8
        r1 = top_r - profile[3][0] + profile[1][0]  # 0.8 + 0.8 = 1.6
        r3 = top_r  # 3.75

        # Section 1: bottom 45-degree chamfer
        bot = rr(r0).linear_extrude(height=thin)
        top = rr(r1).linear_extrude(height=thin).up(z1)
        single_cell = hull(bot, top)

        # Section 2: vertical section
        single_cell = single_cell | rr(r1).linear_extrude(
            height=(z2 - z1) + 2 * overlap
        ).up(z1 - overlap)

        # Section 3: upper 45-degree chamfer
        bot2 = rr(r1).linear_extrude(height=thin).up(z2 - overlap)
        top2 = rr(r3).linear_extrude(height=thin).up(z3)
        single_cell = single_cell | hull(bot2, top2)

        # Section 4: flat top (bridge) up to BASE_HEIGHT
        single_cell = single_cell | rr(r3).linear_extrude(
            height=(z4 - z3) + overlap
        ).up(z3 - overlap)

        # Place one copy per grid cell
        base = None
        for cx, cy in grid_positions([self.grid_x, self.grid_y], cell, center=True):
            placed = single_cell.translate([cx, cy, 0])
            base = placed if base is None else (base | placed)

        return base

    # ------------------------------------------------------------------
    # Lite base (hollow shell)
    # ------------------------------------------------------------------

    def _build_base_lite(self):
        """Build a hollow shell base for lite bins.

        Instead of the solid per-cell base profiles, this creates a thin
        outer shell that follows the base profile shape and a flat bottom
        at *base_thickness* height.  This saves material and print time.

        Returns:
            A 3D PythonSCAD object centered in XY, bottom at z=0.
        """
        s = self.spec
        cell = self._cell_size
        top_dim = [cell - s.BASE_GAP, cell - s.BASE_GAP]
        top_r = s.BASE_TOP_RADIUS
        wall_t = s.WALL_THICKNESS
        bt = min(self.base_thickness, s.BASE_PROFILE_HEIGHT)

        inner = [top_dim[0] - 2 * top_r, top_dim[1] - 2 * top_r]

        def rr(radius):
            return rounded_square(
                [inner[0] + 2 * radius, inner[1] + 2 * radius],
                max(radius, 0.01),
                center=True,
            )

        profile = s.BASE_PROFILE
        thin = 0.01
        overlap = 0.001

        z1 = profile[1][1]
        z2 = profile[2][1]
        z3 = profile[3][1]
        z4 = s.BASE_HEIGHT

        r0 = top_r - profile[3][0]
        r1 = top_r - profile[3][0] + profile[1][0]
        r3 = top_r

        # Outer shell for one cell
        bot = rr(r0).linear_extrude(height=thin)
        top = rr(r1).linear_extrude(height=thin).up(z1)
        outer = hull(bot, top)
        outer = outer | rr(r1).linear_extrude(height=(z2 - z1) + 2 * overlap).up(
            z1 - overlap
        )
        bot2 = rr(r1).linear_extrude(height=thin).up(z2 - overlap)
        top2 = rr(r3).linear_extrude(height=thin).up(z3)
        outer = outer | hull(bot2, top2)
        outer = outer | rr(r3).linear_extrude(height=(z4 - z3) + overlap).up(
            z3 - overlap
        )

        # Inner cavity: shrink radii by wall_thickness
        ir0 = max(r0 - wall_t, 0.01)
        ir1 = max(r1 - wall_t, 0.01)
        ir3 = max(r3 - wall_t, 0.01)

        i_bot = rr(ir0).linear_extrude(height=thin)
        i_top = rr(ir1).linear_extrude(height=thin).up(z1)
        cavity = hull(i_bot, i_top)
        cavity = cavity | rr(ir1).linear_extrude(height=(z2 - z1) + 2 * overlap).up(
            z1 - overlap
        )
        i_bot2 = rr(ir1).linear_extrude(height=thin).up(z2 - overlap)
        i_top2 = rr(ir3).linear_extrude(height=thin).up(z3)
        cavity = cavity | hull(i_bot2, i_top2)
        cavity = cavity | rr(ir3).linear_extrude(height=(z4 - z3) + 2 * overlap).up(
            z3 - overlap
        )

        # Cut cavity above bottom_thickness
        cavity = cavity - cube(
            [top_dim[0] + 1, top_dim[1] + 1, bt + overlap],
            center=True,
        ).up((bt + overlap) / 2 - overlap)

        single_cell = outer - cavity

        # Solid bridge across all cells at the top
        grid_outer = [
            self.grid_x * cell - s.BASE_GAP,
            self.grid_y * cell - s.BASE_GAP,
        ]
        bridge = rounded_square_3d(
            grid_outer, top_r, z4 - z3 + overlap, center_xy=True
        ).up(z3 - overlap)

        bridge_inner = rounded_square_3d(
            [grid_outer[0] - 2 * wall_t, grid_outer[1] - 2 * wall_t],
            max(top_r - wall_t, 0.01),
            z4 - z3 + 3 * overlap,
            center_xy=True,
        ).up(z3 - 2 * overlap)

        bridge = bridge - bridge_inner

        # Bottom solid layer across all cells
        if bt > 0:
            bottom_slab = rounded_square_3d(grid_outer, top_r, bt, center_xy=True)
            bridge = bridge | bottom_slab

        base = None
        for cx, cy in grid_positions([self.grid_x, self.grid_y], cell, center=True):
            placed = single_cell.translate([cx, cy, 0])
            base = placed if base is None else (base | placed)

        return base | bridge

    # ------------------------------------------------------------------
    # Outer body
    # ------------------------------------------------------------------

    def _build_body(self):
        """Build the solid outer body from BASE_HEIGHT to wall_top.

        Starts at z=BASE_HEIGHT (top of the per-cell base profile) so
        that the chamfered base below is not hidden by a flat block.
        Compartment cutters will later be subtracted from this.

        Returns:
            A 3D PythonSCAD object centered in XY, bottom at BASE_HEIGHT.
        """
        s = self.spec
        outer = self._outer_dimensions()
        wall_h = self._wall_height_mm()
        return rounded_square_3d(outer, s.BASE_TOP_RADIUS, wall_h, center_xy=True).up(
            s.BASE_HEIGHT
        )

    # ------------------------------------------------------------------
    # Stacking lip
    # ------------------------------------------------------------------

    def _build_lip(self):
        """Build the stacking lip at the top of the bin.

        The lip is constructed as (outer_envelope - inner_envelope).
        Both envelopes are built as hull-of-slices of solid rounded
        rectangles, ensuring hull() never operates on ring shapes
        (which would fill the hole).

        Returns:
            A 3D PythonSCAD object positioned at the correct z height.
        """
        s = self.spec
        outer = self._outer_dimensions()
        wall_h = self._wall_height_mm()
        wall_top_z = s.BASE_HEIGHT + wall_h

        lip = s.STACKING_LIP_PROFILE
        r_top = s.BASE_TOP_RADIUS
        wall_t = s.WALL_THICKNESS
        support_h = s.STACKING_LIP_SUPPORT_HEIGHT  # 1.2

        inner_dim = [outer[0] - 2 * r_top, outer[1] - 2 * r_top]

        def rr(radius):
            """Rounded rectangle 2D shape at the given corner radius."""
            return rounded_square(
                [inner_dim[0] + 2 * radius, inner_dim[1] + 2 * radius],
                max(radius, 0.01),
                center=True,
            )

        thin = 0.01
        overlap = 0.001

        r_base_offset = r_top - s.STACKING_LIP_DEPTH  # 1.15
        r0 = r_base_offset + lip[0][0]  # 1.15 (lip inner tip)
        r1 = r_base_offset + lip[1][0]  # 1.85
        r3 = r_base_offset + lip[3][0]  # 3.75 = r_top

        h1 = lip[1][1]  # 0.7
        h2 = lip[2][1]  # 2.5
        h3 = lip[3][1]  # 4.4

        # Inner wall radius (where the bin wall meets the lip)
        r_wall_inner = r_top - wall_t  # 2.8

        # -- Z control points (absolute) --
        z_sup = wall_top_z - support_h  # bottom of support
        z_wt = wall_top_z  # wall top / lip start
        z_h1 = wall_top_z + h1  # 0.7 above wall top
        z_h2 = wall_top_z + h2  # 2.5 above wall top
        z_h3 = wall_top_z + h3  # 4.4 above wall top (lip top)

        def slab(r, z):
            return rr(r).linear_extrude(height=thin).up(z)

        # -- Outer envelope (solid extrusion) --
        # The outer edge of the lip is constant at r_top from support
        # bottom to lip top.
        outer_env = rr(r_top).linear_extrude(height=z_h3 - z_sup).up(z_sup)

        # -- Inner envelope (solid hull-of-slices) --
        # Follows the true inner edge at each height level:
        #   support bottom: r_wall_inner (2.8)  -- matches bin wall
        #   wall top:       r0 (1.15)           -- lip inner tip
        #   h1:             r1 (1.85)           -- expanding
        #   h2:             r1 (1.85)           -- vertical
        #   h3:             r3 (3.75)           -- fully open
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
    # Compartment cutters
    # ------------------------------------------------------------------

    def _compartment_cutter(
        self,
        comp_w,
        comp_d,
        comp_h,
        tab_style_resolved,
        is_front,
        is_back,
        is_left,
        is_right,
    ):
        """Build the cutter for a single compartment.

        The cutter is subtracted from the solid body to carve out the
        interior of one compartment.

        Args:
            comp_w: Compartment width (X) in mm.
            comp_d: Compartment depth (Y) in mm.
            comp_h: Compartment height (Z) in mm (from floor to wall top).
            tab_style_resolved: Effective tab style for this compartment.
            is_front: True if compartment is at the -Y edge.
            is_back: True if compartment is at the +Y edge.
            is_left: True if compartment is at the -X edge.
            is_right: True if compartment is at the +X edge.

        Returns:
            A 3D PythonSCAD object centered in XY, bottom at z=0.
        """
        s = self.spec
        r = s.FILLET_RADIUS  # 2.8
        tol = s.TOLERANCE

        # Basic box for the compartment interior
        cutter = rounded_square_3d([comp_w, comp_d], r, comp_h + tol, center_xy=True)

        # Fillet the bottom edges using PythonSCAD's native fillet.
        # The mask selects only the bottom edges by covering just the
        # floor region.
        mask = cube(
            [comp_w + 2 * r, comp_d + 2 * r, r],
            center=True,
        ).up(r / 2)
        cutter = cutter.fillet(r, mask, fn=8)

        # ---- Scoop ----
        if self.scoop > 0 and is_front:
            scoop_obj = self._build_scoop(comp_w, comp_d, comp_h)
            if scoop_obj is not None:
                cutter = cutter | scoop_obj

        # ---- Scoop chamfer ----
        if self.scoop_chamfer and self.scoop > 0 and is_front:
            scoop_r = max(self.scoop * comp_h / 2 - s.FILLET_RADIUS, 0)
            if scoop_r >= 0.01:
                chamfer_depth = min(scoop_r * 0.3, 2.0)
                chamfer_block = (
                    cube(
                        [
                            comp_w - 2 * s.FILLET_RADIUS,
                            chamfer_depth * 2,
                            chamfer_depth * 2,
                        ],
                        center=True,
                    )
                    .rotx(-45)
                    .translate([0, -comp_d / 2, comp_h])
                )
                clip = cube(
                    [comp_w, comp_d + 2, comp_h * 2],
                    center=True,
                ).up(comp_h)
                cutter = cutter | (chamfer_block & clip)

        # ---- Tab ----
        # The tab is SUBTRACTED from the cutter: where the tab shape
        # overlaps, the cutter does not cut, leaving bin material that
        # forms the angled label ledge.
        if tab_style_resolved != "none":
            tab_obj = self._build_tab(
                comp_w,
                comp_d,
                comp_h,
                tab_style_resolved,
                is_left,
                is_right,
            )
            if tab_obj is not None:
                cutter = cutter - tab_obj

        return cutter

    def _build_scoop(self, comp_w, comp_d, comp_h):
        """Build the scoop shape for one compartment.

        The scoop is a quarter-cylinder at the bottom-front (-Y side)
        of the compartment that creates a smooth finger-access curve.

        Args:
            comp_w: Compartment width (X) in mm.
            comp_d: Compartment depth (Y) in mm.
            comp_h: Compartment height (Z) in mm.

        Returns:
            A 3D PythonSCAD object centered in XY at z=0, or None.
        """
        s = self.spec
        r = s.FILLET_RADIUS

        scoop_r = max(self.scoop * comp_h / 2 - r, 0)
        if scoop_r < 0.01:
            return None

        # Cylinder along X at the front-bottom of the compartment.
        # Length must stay within compartment bounds to avoid cutting
        # through adjacent walls.
        scoop_cyl = (
            cylinder(h=comp_w - 2 * r, r=scoop_r, center=True, fn=32).rotx(90).rotz(90)
        )

        # Cylinder axis at y = -comp_d/2 + scoop_r, z = scoop_r.
        # The quarter facing -Y/-Z overlaps with the floor-wall junction.
        scoop_cyl = scoop_cyl.translate([0, -comp_d / 2 + scoop_r, scoop_r])

        # Clip to the compartment XY footprint so the scoop never
        # extends beyond the compartment walls.
        clip = cube(
            [comp_w, comp_d, comp_h * 2],
            center=True,
        ).up(comp_h)

        return scoop_cyl & clip

    def _build_tab(self, comp_w, comp_d, comp_h, style, is_left, is_right):
        """Build the tab shape to subtract from the compartment cutter.

        The tab is a triangular prism at the top-back (+Y side) of the
        compartment. When subtracted from the cutter, material is
        preserved there, creating an angled label ledge.

        Args:
            comp_w: Compartment width (X) in mm.
            comp_d: Compartment depth (Y) in mm.
            comp_h: Compartment height (Z) in mm.
            style: Resolved tab style ("full", "left", "center", "right").
            is_left: Whether this is the leftmost compartment column.
            is_right: Whether this is the rightmost compartment column.

        Returns:
            A 3D PythonSCAD object positioned inside the cutter, or None.
        """
        s = self.spec
        tab_depth = s.TAB_DEPTH
        tab_angle = s.TAB_SUPPORT_ANGLE
        tab_w = min(s.TAB_WIDTH_NOMINAL, comp_w)

        # Skip tabs if bin is too short (< 3 height units)
        if comp_h < 3 * s.HEIGHT_UNIT - s.FLOOR_THICKNESS:
            return None

        tab_drop = tab_depth * math.tan(math.radians(tab_angle))

        # 2D triangle in the XY plane (will be extruded along Z, then
        # rotated so X→-Y depth and the extrusion→X width).
        # The triangle defines the material to KEEP:
        #   - at back wall (x=0): from comp_h down to comp_h - tab_drop
        #   - tab_depth inward (x=-tab_depth): at comp_h (top only)
        # Negative X so after rotation the tab extends inward from the
        # back wall, overlapping with the cutter volume.
        tab_2d = polygon(
            [
                [0, comp_h],
                [0, comp_h - tab_drop],
                [-tab_depth, comp_h],
            ]
        )

        # Determine extrusion width and x-offset based on tab style
        if style == "full" or comp_w <= tab_w:
            extrude_w = comp_w
            x_offset = 0
        elif style == "left":
            extrude_w = tab_w
            x_offset = -(comp_w - tab_w) / 2
        elif style == "right":
            extrude_w = tab_w
            x_offset = (comp_w - tab_w) / 2
        else:  # center
            extrude_w = tab_w
            x_offset = 0

        # Extrude along Z, then rotate so:
        #   polygon X (depth) → 3D -Y (from back wall inward)
        #   polygon Y (height) → 3D Z
        #   extrusion Z → 3D X
        tab_3d = tab_2d.linear_extrude(height=extrude_w, center=True)
        tab_3d = tab_3d.rotx(90).rotz(90)

        # Position at the back of the compartment (+Y edge)
        tab_3d = tab_3d.translate([x_offset, comp_d / 2, 0])

        return tab_3d

    # ------------------------------------------------------------------
    # Thumbscrew hole
    # ------------------------------------------------------------------

    def _build_thumbscrew_hole(self):
        """Build a simplified M15x1.5 thumbscrew hole for one grid cell.

        Creates a threaded-style hole compatible with Gridfinity Refined
        thumbscrews.  Uses a helical approximation with triangular
        thread profile rather than a full ISO thread library.

        Returns:
            A 3D PythonSCAD object centered at the origin.
        """
        s = self.spec
        d = s.THUMBSCREW_DIAMETER
        pitch = s.THUMBSCREW_PITCH
        h = s.THUMBSCREW_HEIGHT

        minor_d = d - 1.0825 * pitch
        core = cylinder(h=h, d=minor_d, fn=48)

        n_turns = int(h / pitch) + 1
        thread_depth = (d - minor_d) / 2
        fn_thread = 8

        outer = cylinder(h=h, d=d, fn=48)

        grooves = None
        for i in range(n_turns * fn_thread):
            angle = i * 360.0 / fn_thread
            z = (i / fn_thread) * pitch
            if z > h:
                break
            seg_h = pitch * 0.4
            seg = (
                cube([thread_depth + 0.1, 0.3, seg_h], center=True)
                .translate([d / 2 - thread_depth / 2, 0, z])
                .rotz(angle)
            )
            grooves = seg if grooves is None else (grooves | seg)

        if grooves is not None:
            hole = core | (outer - grooves)
        else:
            hole = outer

        return hole

    # ------------------------------------------------------------------
    # Compartment layout helpers
    # ------------------------------------------------------------------

    def _cut_grid_compartments(self, body, comp_h, d_magic, gx, gy, cell, cutter_z):
        """Cut equal-grid compartments defined by div_x / div_y."""
        s = self.spec
        nx, ny = self.div_x, self.div_y

        effective_h = self.depth if self.depth > 0 else comp_h

        for ix in range(nx):
            for iy in range(ny):
                fx = ix / nx
                fy = iy / ny
                fw = 1.0 / nx
                fh = 1.0 / ny

                comp_w = fw * (gx * cell + d_magic) - s.DIVIDER_WIDTH
                comp_d = fh * (gy * cell + d_magic) - s.DIVIDER_WIDTH

                cx = (fx + fw / 2 - 0.5) * (gx * cell + d_magic)
                cy = (fy + fh / 2 - 0.5) * (gy * cell + d_magic)

                is_front = iy == 0
                is_back = iy == ny - 1
                is_left = ix == 0
                is_right = ix == nx - 1

                # Resolve tab placement
                is_top_left = is_back and is_left
                if self.place_tab == "top_left" and not is_top_left:
                    tab_resolved = "none"
                elif self.tab_style == "auto":
                    if is_left:
                        tab_resolved = "left"
                    elif is_right:
                        tab_resolved = "right"
                    else:
                        tab_resolved = "center"
                else:
                    tab_resolved = self.tab_style

                cutter = self._compartment_cutter(
                    comp_w,
                    comp_d,
                    effective_h,
                    tab_resolved,
                    is_front,
                    is_back,
                    is_left,
                    is_right,
                )
                # When depth is overridden, position the cutter so the top
                # aligns with the wall top
                if self.depth > 0 and self.depth < comp_h:
                    z_off = cutter_z + (comp_h - self.depth)
                else:
                    z_off = cutter_z
                body = body - cutter.translate([cx, cy, z_off])

        return body

    def _cut_cylinder_compartments(self, body, comp_h, d_magic, gx, gy, cell, cutter_z):
        """Cut cylindrical holes at each grid division center."""
        nx, ny = self.div_x, self.div_y
        cyl_r = self.cylinder_diameter / 2
        cyl_chamfer = self.cylinder_chamfer

        for ix in range(nx):
            for iy in range(ny):
                fx = ix / nx
                fy = iy / ny
                fw = 1.0 / nx
                fh = 1.0 / ny

                cx = (fx + fw / 2 - 0.5) * (gx * cell + d_magic)
                cy = (fy + fh / 2 - 0.5) * (gy * cell + d_magic)

                cyl = cut_chamfered_cylinder(cyl_r, comp_h, cyl_chamfer)
                body = body - cyl.translate([cx, cy, cutter_z + comp_h])

        return body

    def _cut_custom_compartments(self, body, comp_h, d_magic, gx, gy, cell, cutter_z):
        """Cut compartments from a list of Compartment objects."""
        s = self.spec
        total_w = gx * cell + d_magic
        total_d = gy * cell + d_magic
        effective_h = self.depth if self.depth > 0 else comp_h

        for comp in self.compartments:
            comp_w = (comp.w / gx) * total_w - s.DIVIDER_WIDTH
            comp_d = (comp.h / gy) * total_d - s.DIVIDER_WIDTH

            cx = ((comp.x + comp.w / 2) / gx - 0.5) * total_w
            cy = ((comp.y + comp.h / 2) / gy - 0.5) * total_d

            is_front = comp.y <= 0
            is_back = (comp.y + comp.h) >= gy
            is_left = comp.x <= 0
            is_right = (comp.x + comp.w) >= gx

            scoop_val = comp.scoop if comp.scoop is not None else self.scoop
            tab = comp.tab_style if comp.tab_style is not None else self.tab_style

            is_top_left = is_back and is_left
            if self.place_tab == "top_left" and not is_top_left:
                tab = "none"
            elif tab == "auto":
                if is_left:
                    tab = "left"
                elif is_right:
                    tab = "right"
                else:
                    tab = "center"

            saved_scoop = self.scoop
            try:
                self.scoop = max(0.0, min(float(scoop_val), 1.0))
                cutter = self._compartment_cutter(
                    comp_w,
                    comp_d,
                    effective_h,
                    tab,
                    is_front,
                    is_back,
                    is_left,
                    is_right,
                )
            finally:
                self.scoop = saved_scoop

            if self.depth > 0 and self.depth < comp_h:
                z_off = cutter_z + (comp_h - self.depth)
            else:
                z_off = cutter_z
            body = body - cutter.translate([cx, cy, z_off])

        return body

    # ------------------------------------------------------------------
    # Main render
    # ------------------------------------------------------------------

    def render(self):
        """Generate the bin geometry.

        Returns:
            A 3D PythonSCAD object representing the complete bin.
        """
        s = self.spec
        tol = s.TOLERANCE
        cell = self._cell_size
        outer = self._outer_dimensions()
        wall_h = self._wall_height_mm()
        wall_top_z = s.BASE_HEIGHT + wall_h

        # Floor level (inside the bin, top of base)
        floor_z = s.BASE_HEIGHT
        # Compartment height (from floor to wall top)
        comp_h = wall_h - s.FLOOR_THICKNESS

        # ---- 1. Base ----
        base = self._build_base_lite() if self.lite else self._build_base()

        # ---- 2. Outer body ----
        body = self._build_body()

        # ---- 3. Stacking lip ----
        if self.lip_style == "normal":
            lip = self._build_lip()
            body = body | lip
        elif self.lip_style == "subtractive":
            # Remove the lip zone from the top of the bin
            lip_cutter = self._build_lip()
            body = body - lip_cutter

        # ---- 4. Subtract compartment cutters ----
        if not self.solid:
            d_magic = -2 * s.FIT_CLEARANCE - 2 * s.WALL_THICKNESS + s.DIVIDER_WIDTH
            gx, gy = self.grid_x, self.grid_y
            cutter_z = floor_z + s.FLOOR_THICKNESS

            if self.cut_cylinders:
                body = self._cut_cylinder_compartments(
                    body, comp_h, d_magic, gx, gy, cell, cutter_z
                )
            elif self.compartments is not None:
                body = self._cut_custom_compartments(
                    body, comp_h, d_magic, gx, gy, cell, cutter_z
                )
            else:
                body = self._cut_grid_compartments(
                    body, comp_h, d_magic, gx, gy, cell, cutter_z
                )

        elif self.solid and self.solid_ratio < 1.0:
            # Partially filled solid: cut out the empty portion at the top
            fill_h = comp_h * self.solid_ratio
            empty_h = comp_h - fill_h
            if empty_h > 0.01:
                inner = [
                    outer[0] - 2 * s.WALL_THICKNESS,
                    outer[1] - 2 * s.WALL_THICKNESS,
                ]
                empty_cut = rounded_square_3d(
                    inner,
                    s.FILLET_RADIUS,
                    empty_h + tol,
                    center_xy=True,
                ).up(wall_top_z - empty_h)
                body = body - empty_cut

        # ---- 5. Union body + base ----
        result = body | base

        # ---- 6. Subtract bottom holes ----
        # Bin holes open from the bottom (z=0) going upward into the
        # base profile. No mirror needed -- block_base_hole already
        # builds geometry extending in +Z from z=0.
        if self.hole_options and self.hole_options.has_any_hole:
            hole_obj = block_base_hole(self.hole_options, spec=s)
            if hole_obj is not None:
                corners_only = self.only_corners or self.half_grid
                if corners_only:
                    d = s.HOLE_FROM_CENTER
                    full_cell = s.GRID_SIZE
                    outer_half = [
                        self.grid_x * cell / 2 - full_cell / 2,
                        self.grid_y * cell / 2 - full_cell / 2,
                    ]
                    for sx in (-1, 1):
                        for sy in (-1, 1):
                            hx = sx * (outer_half[0] + d)
                            hy = sy * (outer_half[1] + d)
                            result = result - hole_obj.translate([hx, hy, 0])
                else:
                    for cx, cy in grid_positions(
                        [self.grid_x, self.grid_y], cell, center=True
                    ):
                        holes = hole_pattern(hole_obj, spec=s).translate([cx, cy, 0])
                        result = result - holes

        # ---- 7. Subtract thumbscrew holes ----
        if self.enable_thumbscrew:
            ts_hole = self._build_thumbscrew_hole()
            for cx, cy in grid_positions([self.grid_x, self.grid_y], cell, center=True):
                result = result - ts_hole.translate([cx, cy, 0])

        return result
