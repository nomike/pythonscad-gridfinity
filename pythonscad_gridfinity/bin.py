"""Gridfinity bin generator.

Creates parametric Gridfinity-compatible bins with configurable
compartments, scoops, label tabs, stacking lip, and bottom holes.

Usage:
    from pythonscad_gridfinity import GridfinityBin, HoleOptions

    # Solid bin (no compartment cuts, like OpenSCAD bin_render without children)
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
        div_x: Number of compartments along X, or None for a solid
            bin without compartment cuts (matching OpenSCAD's
            ``bin_render`` without children).  Set to 1 for a single
            compartment with scoop/tab.
        div_y: Number of compartments along Y, or None (same as div_x).
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
        div_x=None,
        div_y=None,
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
        self.div_x = max(div_x, 1) if div_x is not None else None
        self.div_y = max(div_y, 1) if div_y is not None else None
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
        lip_h = self._effective_lip_height() if self.lip_style == "normal" else 0.0
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

    def _effective_lip_height(self):
        """Actual stacking lip height after filleting the tip.

        The OpenSCAD reference applies a fillet at the sharp tip of the
        STACKING_LIP_PROFILE, rounding it and reducing the effective
        height.  Returns the nominal height when the fillet radius is 0.
        """
        s = self.spec
        fillet_r = s.STACKING_LIP_FILLET_RADIUS
        if fillet_r <= 0:
            return s.STACKING_LIP_HEIGHT

        lip = s.STACKING_LIP_PROFILE
        support_h = s.STACKING_LIP_SUPPORT_HEIGHT
        tol = s.TOLERANCE

        before = lip[2]  # [0.7, 2.5]
        tip = lip[3]  # [2.6, 4.4]
        support_drop = support_h + tip[0]  # tan(45deg) * depth
        after = [tip[0] - tol, -support_drop]

        v0 = [before[0] - tip[0], before[1] - tip[1]]
        v1 = [after[0] - tip[0], after[1] - tip[1]]
        cross_val = v0[0] * v1[1] - v0[1] * v1[0]
        dot_val = v0[0] * v1[0] + v0[1] * v1[1]
        angle = math.atan2(cross_val, dot_val)

        dist = fillet_r / math.sin(abs(angle) / 2)
        len_v0 = math.hypot(*v0)
        len_v1 = math.hypot(*v1)
        uv0 = [v0[0] / len_v0, v0[1] / len_v0]
        uv1 = [v1[0] / len_v1, v1[1] / len_v1]
        bisector = [uv0[0] + uv1[0], uv0[1] + uv1[1]]
        len_bis = math.hypot(*bisector)
        ubis = [bisector[0] / len_bis, bisector[1] / len_bis]
        center_y = tip[1] + dist * ubis[1]

        return center_y + fillet_r

    def _lip_fillet_arc(self):
        """Compute the filleted lip profile points for the top section.

        Returns a list of (profile_x, profile_y) points starting from
        the tangent point on the chamfer segment, through the fillet arc,
        to the tangent point on the support segment.  Coordinates are in
        the lip's local system (x = radial depth from inner reference,
        y = height above wall top).

        Returns None when fillet radius is 0.
        """
        s = self.spec
        fillet_r = s.STACKING_LIP_FILLET_RADIUS
        if fillet_r <= 0:
            return None

        lip = s.STACKING_LIP_PROFILE
        support_h = s.STACKING_LIP_SUPPORT_HEIGHT
        tol = s.TOLERANCE

        before = lip[2]  # [0.7, 2.5]
        tip = lip[3]  # [2.6, 4.4]
        support_drop = support_h + tip[0]
        after = [tip[0] - tol, -support_drop]

        v0 = [before[0] - tip[0], before[1] - tip[1]]
        v1 = [after[0] - tip[0], after[1] - tip[1]]
        cross_val = v0[0] * v1[1] - v0[1] * v1[0]
        dot_val = v0[0] * v1[0] + v0[1] * v1[1]
        angle = math.atan2(cross_val, dot_val)

        dist = fillet_r / math.sin(abs(angle) / 2)
        len_v0 = math.hypot(*v0)
        len_v1 = math.hypot(*v1)
        uv0 = [v0[0] / len_v0, v0[1] / len_v0]
        uv1 = [v1[0] / len_v1, v1[1] / len_v1]
        bisector = [uv0[0] + uv1[0], uv0[1] + uv1[1]]
        len_bis = math.hypot(*bisector)
        ubis = [bisector[0] / len_bis, bisector[1] / len_bis]
        center = [tip[0] + dist * ubis[0], tip[1] + dist * ubis[1]]

        seg_dir = [tip[0] - before[0], tip[1] - before[1]]
        seg_len_sq = seg_dir[0] ** 2 + seg_dir[1] ** 2
        t_param = (
            (center[0] - before[0]) * seg_dir[0] + (center[1] - before[1]) * seg_dir[1]
        ) / seg_len_sq
        tangent1 = [
            before[0] + t_param * seg_dir[0],
            before[1] + t_param * seg_dir[1],
        ]

        seg2_dir = [after[0] - tip[0], after[1] - tip[1]]
        seg2_len_sq = seg2_dir[0] ** 2 + seg2_dir[1] ** 2
        t2_param = (
            (center[0] - tip[0]) * seg2_dir[0] + (center[1] - tip[1]) * seg2_dir[1]
        ) / seg2_len_sq
        tangent2 = [
            tip[0] + t2_param * seg2_dir[0],
            tip[1] + t2_param * seg2_dir[1],
        ]

        a_start = math.atan2(tangent1[1] - center[1], tangent1[0] - center[0])
        a_end = math.atan2(tangent2[1] - center[1], tangent2[0] - center[0])

        n_segments = 12
        points = [tangent1]
        for i in range(1, n_segments):
            frac = i / n_segments
            a = a_start + frac * (a_end - a_start)
            points.append(
                [
                    center[0] + fillet_r * math.cos(a),
                    center[1] + fillet_r * math.sin(a),
                ]
            )
        points.append(tangent2)
        return points

    def _get_wall_profile_polygon(self):
        """Build the 2D wall+lip profile polygon matching OpenSCAD _profile_wall.

        Returns a list of [x, y] points in sweep coordinates: x = radial
        distance from the inner rectangle path, y = height above path base.
        Used by _sweep_lip_profile to match the OpenSCAD sweep_rounded result.
        """
        s = self.spec
        wall_h = self._wall_height_mm()
        x_off = s.BASE_TOP_RADIUS - s.STACKING_LIP_DEPTH  # 1.15

        # Full lip polygon: points 0,1,2, (fillet arc), support points.
        # STACKING_LIP = line + [[tip.x-tol, -support_drop], [0, -SUPPORT_HEIGHT]]
        lip = s.STACKING_LIP_PROFILE
        support_h = s.STACKING_LIP_SUPPORT_HEIGHT
        tol = s.TOLERANCE
        tip = lip[3]
        support_drop = support_h + tip[0]
        after_tip = [tip[0] - tol, -support_drop]
        support_inner = [0, -support_h]

        points = []
        points.append([lip[0][0] + x_off, max(lip[0][1] + wall_h, 0)])
        points.append([lip[1][0] + x_off, max(lip[1][1] + wall_h, 0)])
        points.append([lip[2][0] + x_off, max(lip[2][1] + wall_h, 0)])

        arc_pts = self._lip_fillet_arc()
        if arc_pts is not None:
            for pt in arc_pts:
                points.append([pt[0] + x_off, max(pt[1] + wall_h, 0)])
        else:
            points.append([lip[3][0] + x_off, max(lip[3][1] + wall_h, 0)])

        points.append([after_tip[0] + x_off, max(after_tip[1] + wall_h, 0)])
        points.append([support_inner[0] + x_off, max(support_inner[1] + wall_h, 0)])

        return points

    def _sweep_lip_profile(self, inner_size_2d, profile_points):
        """Sweep a 2D profile (outward, height) around a centered rectangle.

        Replicates OpenSCAD sweep_rounded: linear_extrude along each edge,
        rotate_extrude(90) at each corner. inner_size_2d is [width, length]
        of the path rectangle (grid size minus 2*BASE_TOP_RADIUS).
        """
        hw = inner_size_2d[0] / 2
        hl = inner_size_2d[1] / 2
        L = inner_size_2d[0]  # same for square

        poly_2d = polygon(profile_points)
        slab = poly_2d.linear_extrude(height=L)

        # Base transform: (outward, height, extent) -> (extent, outward, height)
        slab = slab.rotx(90).rotz(90)

        # Four edges: place (extent, outward, height) and translate to edge
        top = slab.translate([-hw, hl, 0])
        right = slab.rotz(-90).translate([hw, hl, 0])
        bottom = slab.rotz(-180).translate([hw, -hl, 0])
        left = slab.rotz(-270).translate([-hw, -hl, 0])

        # Four corners: rotate_extrude(90) then place
        corner_slab = poly_2d.rotate_extrude(angle=90)
        c1 = corner_slab.translate([hw, hl, 0])
        c2 = corner_slab.rotz(-90).translate([hw, -hl, 0])
        c3 = corner_slab.rotz(-180).translate([-hw, -hl, 0])
        c4 = corner_slab.rotz(-270).translate([-hw, hl, 0])

        return top | right | bottom | left | c1 | c2 | c3 | c4

    def _build_lip(self, wall_ring_height=None):
        """Build the stacking lip at the top of the bin.

        Matches OpenSCAD render_wall: a 2D wall+lip profile polygon (filleted
        tip, support section) is swept around the inner rectangle perimeter
        via linear_extrude on each edge and rotate_extrude(90) at each corner.
        The wall ring (thin ring below the lip) is built separately and unioned.

        Args:
            wall_ring_height: If set, use this instead of wall_h for the ring
                height (e.g. wall_h - 0.001 to avoid z-fighting with the lip).
        """
        s = self.spec
        outer = self._outer_dimensions()
        wall_h = self._wall_height_mm()
        ring_h = wall_h if wall_ring_height is None else wall_ring_height
        r_top = s.BASE_TOP_RADIUS
        inner_size = [outer[0] - 2 * r_top, outer[1] - 2 * r_top]

        # Wall ring: thin ring from z=0 to z=ring_h in local coords
        inner_dim = [outer[0] - 2 * s.WALL_THICKNESS, outer[1] - 2 * s.WALL_THICKNESS]
        wall_ring = (
            rounded_square(outer, r_top, center=True).linear_extrude(height=ring_h)
            - rounded_square(inner_dim, r_top, center=True).linear_extrude(
                height=ring_h
            )
        ).up(s.BASE_HEIGHT)

        # Lip: swept profile in local coords (z=0 at wall base), then move up
        profile_pts = self._get_wall_profile_polygon()
        lip_swept = self._sweep_lip_profile(inner_size, profile_pts)
        lip_swept = lip_swept.up(s.BASE_HEIGHT)

        return wall_ring | lip_swept

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

        # Floor level (inside the bin, top of base)
        floor_z = s.BASE_HEIGHT
        # Compartment height (from floor to wall top)
        comp_h = wall_h - s.FLOOR_THICKNESS
        # Infill height: when lip present, OpenSCAD stops at wall_top - support
        fill_height = wall_h - (
            s.STACKING_LIP_SUPPORT_HEIGHT if self.lip_style == "normal" else 0
        )

        # ---- 1. Base ----
        base = self._build_base_lite() if self.lite else self._build_base()

        # ---- 2. Body: match OpenSCAD exactly ----
        # OpenSCAD: bin_render_wall (wall+lip) then difference(union(
        #   bin_render_infill (block from BASE_HEIGHT, height=fill_height),
        #   base?), children()). So infill is a separate block that only
        # extends to fill_height; no pocket subtraction, so no z-fighting.
        has_compartments = not self.solid and (
            self.div_x is not None
            or self.div_y is not None
            or self.compartments is not None
            or self.cut_cylinders
        )
        if self.lip_style == "normal":
            infill_dim = [outer[0] - tol, outer[1] - tol]
            infill_block = rounded_square_3d(
                infill_dim,
                s.BASE_TOP_RADIUS,
                fill_height,
                center_xy=True,
            ).up(floor_z)
            if has_compartments:
                nx = self.div_x if self.div_x is not None else 1
                ny = self.div_y if self.div_y is not None else 1
                saved_div = (self.div_x, self.div_y)
                self.div_x, self.div_y = nx, ny
                d_magic = -2 * s.FIT_CLEARANCE - 2 * s.WALL_THICKNESS + s.DIVIDER_WIDTH
                gx, gy = self.grid_x, self.grid_y
                # OpenSCAD positions children at BASE_HEIGHT+fill_height; cutters
                # extend down through the infill only (7 to 12.8).
                cutter_z = floor_z
                if self.cut_cylinders:
                    infill_block = self._cut_cylinder_compartments(
                        infill_block, fill_height, d_magic, gx, gy, cell, cutter_z
                    )
                elif self.compartments is not None:
                    infill_block = self._cut_custom_compartments(
                        infill_block, fill_height, d_magic, gx, gy, cell, cutter_z
                    )
                else:
                    infill_block = self._cut_grid_compartments(
                        infill_block, fill_height, d_magic, gx, gy, cell, cutter_z
                    )
                self.div_x, self.div_y = saved_div
            # Match OpenSCAD: combine mesh (rendered infill) + CSG (wall+lip) to
            # avoid z-fighting in F5 preview. Fall back to CSG union with gap if
            # mesh() fails (e.g. unsupported geometry).
            mesh_result = infill_block.mesh(triangulate=True)
            if isinstance(mesh_result, tuple) and len(mesh_result) == 2:
                pts, faces = mesh_result
                if pts and faces:
                    infill_mesh = polyhedron(pts, faces)
                    body = infill_mesh | self._build_lip()
                else:
                    _apply_zfight_fallback()
            else:
                _apply_zfight_fallback()

            def _apply_zfight_fallback():
                nonlocal body
                ZFIGHT_GAP = 0.1
                infill_short = rounded_square_3d(
                    infill_dim,
                    s.BASE_TOP_RADIUS,
                    fill_height - ZFIGHT_GAP,
                    center_xy=True,
                ).up(floor_z)
                if has_compartments:
                    self.div_x, self.div_y = nx, ny
                    if self.cut_cylinders:
                        infill_short = self._cut_cylinder_compartments(
                            infill_short, fill_height, d_magic, gx, gy, cell, cutter_z
                        )
                    elif self.compartments is not None:
                        infill_short = self._cut_custom_compartments(
                            infill_short, fill_height, d_magic, gx, gy, cell, cutter_z
                        )
                    else:
                        infill_short = self._cut_grid_compartments(
                            infill_short, fill_height, d_magic, gx, gy, cell, cutter_z
                        )
                    self.div_x, self.div_y = saved_div
                body = infill_short | self._build_lip(
                    wall_ring_height=wall_h - ZFIGHT_GAP
                )
        else:
            body = self._build_body()
            if self.lip_style == "subtractive":
                lip_cutter = self._build_lip()
                body = body - lip_cutter

        # ---- 3. Compartment cutters (when no lip) ----
        if has_compartments and self.lip_style != "normal":
            nx = self.div_x if self.div_x is not None else 1
            ny = self.div_y if self.div_y is not None else 1
            saved_div = (self.div_x, self.div_y)
            self.div_x, self.div_y = nx, ny

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

            self.div_x, self.div_y = saved_div

        elif self.solid and self.solid_ratio < 1.0:
            # Partially filled solid: cut out the empty portion at the top
            fill_h = fill_height * self.solid_ratio
            empty_h = fill_height - fill_h
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
                ).up(floor_z + fill_height - empty_h)
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
