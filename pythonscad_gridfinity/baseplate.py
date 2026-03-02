"""Gridfinity baseplate generator.

Creates parametric Gridfinity-compatible baseplates with support for
multiple styles (thin, weighted, skeletonized, screw-together) and
configurable magnet/screw holes.

Usage:
    from pythonscad_gridfinity import GridfinityBaseplate, HoleOptions

    bp = GridfinityBaseplate(4, 3)
    bp.render().show()

    # Weighted baseplate with magnet holes
    bp = GridfinityBaseplate(
        4, 3,
        style="weighted",
        hole_options=HoleOptions(magnet_hole=True, crush_ribs=True),
    )
    bp.render().show()
"""

from openscad import *

from .spec import GridfinitySpec
from .holes import block_base_hole, hole_pattern, make_hole_printable
from .helpers import (
    rounded_square,
    grid_positions,
    pattern_circular,
    cone,
)


# Valid baseplate style names
BASEPLATE_STYLES = (
    "thin",
    "weighted",
    "skeleton",
    "screw_together",
    "screw_together_minimal",
)

# Valid underside screw styles
SCREW_STYLES = ("none", "countersink", "counterbore")


class GridfinityBaseplate:
    """Parametric Gridfinity baseplate generator.

    Supports five baseplate styles matching the OpenSCAD reference:

    - ``"thin"``: Minimal baseplate with just the lip profile.
    - ``"weighted"``: Thick bottom with rectangular weight cutouts.
    - ``"skeleton"``: Thick bottom hollowed out, keeping material near holes.
    - ``"screw_together"``: Thick with horizontal screw channels between cells.
    - ``"screw_together_minimal"``: Screw channels with thin lip profile.

    Args:
        grid_x: Number of grid units along X.
        grid_y: Number of grid units along Y.
        spec: GridfinitySpec instance. Uses standard dimensions if None.
        style: One of the BASEPLATE_STYLES.
        hole_options: HoleOptions for magnet/screw holes. None means no holes.
        screw_style: Underside screw mounting: "none", "countersink", or "counterbore".
        min_size_mm: (min_x, min_y) minimum overall size for fit-to-drawer.
                     Set grid_x/grid_y to 0 to auto-calculate from this.
        fit_offset: (-1..1, -1..1) where to place extra padding.
                    -1 = all on negative side, 0 = centered, 1 = all on positive side.
        screw_diameter: Diameter for screw-together channels (default 3.35, for M3).
        screw_head_diameter: Head diameter for screw-together (default 5.0).
        screw_spacing: Spacing between screw channels (default 0.5).
        n_screws: Number of screws per grid edge (1-3, default 1).
    """

    def __init__(
        self,
        grid_x,
        grid_y,
        spec=None,
        style="thin",
        hole_options=None,
        screw_style="none",
        min_size_mm=(0, 0),
        fit_offset=(0, 0),
        screw_diameter=3.35,
        screw_head_diameter=5.0,
        screw_spacing=0.5,
        n_screws=1,
    ):
        self.spec = spec or GridfinitySpec()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.style = style
        self.hole_options = hole_options
        self.screw_style = screw_style
        self.min_size_mm = min_size_mm
        self.fit_offset = fit_offset
        self.screw_diameter = screw_diameter
        self.screw_head_diameter = screw_head_diameter
        self.screw_spacing = screw_spacing
        self.n_screws = n_screws

        if style not in BASEPLATE_STYLES:
            raise ValueError(
                f"Unknown style '{style}'. Must be one of {BASEPLATE_STYLES}"
            )
        if screw_style not in SCREW_STYLES:
            raise ValueError(
                f"Unknown screw_style '{screw_style}'. Must be one of {SCREW_STYLES}"
            )

    # ------------------------------------------------------------------
    # Height calculations
    # ------------------------------------------------------------------

    def _additional_height(self):
        """Extra height below the lip profile, depends on the baseplate style."""
        s = self.spec
        style = self.style
        if style == "thin" or style == "screw_together_minimal":
            if style == "screw_together_minimal":
                return s.SCREW_TOGETHER_HEIGHT
            return 0.0
        if style == "weighted":
            return s.BP_H_BOT
        if style == "screw_together":
            return s.SCREW_TOGETHER_HEIGHT
        # skeleton
        return self._skeleton_height()

    def _skeleton_height(self):
        """Extra height needed for the skeletonized style."""
        s = self.spec
        opts = self.hole_options
        has_magnet = opts.magnet_hole if opts else False
        magnet_part = s.MAGNET_HOLE_DEPTH if has_magnet else 0.0
        screw_part = {
            "none": self.screw_diameter,
            "countersink": s.BASEPLATE_SCREW_COUNTERSINK_ADDITIONAL_RADIUS,
            "counterbore": s.BASEPLATE_SCREW_COUNTERBORE_HEIGHT,
        }[self.screw_style]
        return s.SKELETON_MIN_THICKNESS + magnet_part + screw_part

    # ------------------------------------------------------------------
    # Grid / size calculations
    # ------------------------------------------------------------------

    def _resolve_grid_and_size(self):
        """Determine final grid counts and overall size in mm.

        Returns:
            (grid_size, size_mm, padding_mm) where each is [x, y, z].
        """
        s = self.spec
        cell_size = s.GRID_SIZE
        add_h = self._additional_height()
        bp_h = add_h + s.BASEPLATE_HEIGHT

        # Resolve grid counts (0 = auto-fill from min_size_mm)
        gx = self.grid_x if self.grid_x > 0 else int(self.min_size_mm[0] // cell_size)
        gy = self.grid_y if self.grid_y > 0 else int(self.min_size_mm[1] // cell_size)
        grid_size = [gx, gy]

        grid_mm = [gx * cell_size, gy * cell_size, bp_h]
        size_mm = [
            max(grid_mm[0], self.min_size_mm[0]),
            max(grid_mm[1], self.min_size_mm[1]),
            bp_h,
        ]
        padding_mm = [size_mm[i] - grid_mm[i] for i in range(3)]
        return grid_size, size_mm, padding_mm

    # ------------------------------------------------------------------
    # Baseplate cutter (the socket that receives the bin base)
    # ------------------------------------------------------------------

    def _baseplate_cutter(self, size=None, height=None):
        """Create the negative for a single baseplate cell.

        The cutter is the cavity that receives a bin's base profile. It is
        constructed by hulling thin rounded-rectangle slices at the heights
        defined by the baseplate profile.

        Args:
            size: [width, depth] of one cell (default: BASEPLATE_DIMENSIONS).
            height: Total cutter height (default: BASEPLATE_HEIGHT).

        Returns:
            A 3D PythonSCAD object centered in XY, bottom at z=0.
        """
        s = self.spec
        if size is None:
            size = list(s.BASEPLATE_DIMENSIONS)
        if height is None:
            height = s.BASEPLATE_HEIGHT

        profile = s.BASEPLATE_PROFILE
        profile_h = profile[3][1]  # 4.65
        clearance = height - profile_h

        # Inner dimensions of the sweep path (outer size minus outer diameter)
        inner_dim = [
            size[0] - s.BASEPLATE_OUTER_DIAMETER,
            size[1] - s.BASEPLATE_OUTER_DIAMETER,
        ]

        # Corner radii at each profile transition
        r0 = s.BASEPLATE_INNER_RADIUS  # 1.15
        r1 = s.BASEPLATE_INNER_RADIUS + profile[1][0]  # 1.15 + 0.7 = 1.85
        # r2 same as r1 (vertical section)
        r3 = s.BASEPLATE_OUTER_RADIUS  # 4.0

        def rr(radius):
            """Rounded rectangle 2D shape at the given corner radius."""
            return rounded_square(
                [inner_dim[0] + 2 * radius, inner_dim[1] + 2 * radius],
                radius,
                center=True,
            )

        thin_slice = 0.01  # slice thickness for hull operations
        # Small overlap between adjacent sections to prevent z-fighting
        # in preview mode (coplanar faces flicker when they share a plane)
        overlap = 0.001

        # Build the cutter as a stack of slightly overlapping sections.
        z1 = clearance  # bottom of lip profile
        z2 = clearance + profile[1][1]  # top of first 45-degree chamfer
        z3 = clearance + profile[2][1]  # top of vertical section
        z4 = height  # top of second 45-degree chamfer

        # Section 1: clearance gap (constant inner shape)
        sections = rr(r0).linear_extrude(height=max(z1 + overlap, thin_slice))

        # Section 2: bottom 45-degree chamfer
        bot = rr(r0).linear_extrude(height=thin_slice).up(z1 - overlap)
        top = rr(r1).linear_extrude(height=thin_slice).up(z2)
        sections = sections | hull(bot, top)

        # Section 3: vertical section
        sections = sections | rr(r1).linear_extrude(height=(z3 - z2) + 2 * overlap).up(
            z2 - overlap
        )

        # Section 4: top 45-degree chamfer
        bot2 = rr(r1).linear_extrude(height=thin_slice).up(z3 - overlap)
        top2 = rr(r3).linear_extrude(height=thin_slice).up(z4)
        sections = sections | hull(bot2, top2)

        return sections

    # ------------------------------------------------------------------
    # Outside corner rounding
    # ------------------------------------------------------------------

    def _corner_cutter(self, height):
        """Shape to subtract from each outside corner to round it.

        Creates a square-minus-circle shape extruded to the full height,
        which when subtracted from the baseplate rounds the outside corners
        to BASEPLATE_OUTER_RADIUS.

        Args:
            height: Full baseplate height.

        Returns:
            A 3D PythonSCAD object positioned at the origin corner.
        """
        s = self.spec
        r = s.BASEPLATE_OUTER_RADIUS
        tol = s.TOLERANCE
        profile_2d = square(r + tol) - circle(r=r - tol, fn=48)
        return profile_2d.linear_extrude(height=height + 2 * tol).down(tol)

    # ------------------------------------------------------------------
    # Weight cutouts (for "weighted" style)
    # ------------------------------------------------------------------

    def _weight_cutout(self):
        """Create the weight-saving cutout for a single grid cell.

        Includes a central rectangular pocket and four rounded slots
        arranged in a circular pattern.

        Returns:
            A 3D PythonSCAD object centered in XY.
        """
        s = self.spec
        # Central rectangular cutout
        center_cut = cube(
            [s.BP_CUT_SIZE, s.BP_CUT_SIZE, s.BP_CUT_DEPTH * 2], center=True
        )

        # Four rounded slots at 90-degree intervals
        slot_rect = cube(
            [s.BP_RCUT_WIDTH, s.BP_RCUT_LENGTH, s.BP_RCUT_DEPTH * 2], center=True
        )
        slot_cap = cylinder(
            d=s.BP_RCUT_WIDTH, h=s.BP_RCUT_DEPTH * 2, center=True
        ).translate([0, s.BP_RCUT_LENGTH / 2, 0])
        single_slot = (slot_rect | slot_cap).translate([0, 10, 0])
        slots = pattern_circular(single_slot, 4)

        return center_cut | slots

    # ------------------------------------------------------------------
    # Skeleton cutout (for "skeleton" style)
    # ------------------------------------------------------------------

    def _skeleton_profile_2d(self, cell_size=None):
        """Create the 2D skeleton cutout profile for a single cell.

        The skeleton removes material from the cell interior while keeping
        solid areas around the four hole positions. When this shape is
        extruded and subtracted from the baseplate, material remains only
        near the holes and cell edges.

        Matches the OpenSCAD ``profile_skeleton()`` logic:
        1. Start with the inner rectangle shrunk by skeleton_radius.
        2. Subtract origin-cornered squares placed at each hole position
           and expanded by (magnet_radius + skeleton_radius + 2 mm).
        3. Apply offset(r=skeleton_radius) to round all corners.

        Args:
            cell_size: Grid cell size (default: GRID_SIZE).

        Returns:
            A 2D PythonSCAD object centered at origin.
        """
        s = self.spec
        if cell_size is None:
            cell_size = s.GRID_SIZE

        # Inner size matching baseplate_inner_size()
        inner_size = cell_size - s.BASEPLATE_OUTER_DIAMETER + s.BASEPLATE_INNER_DIAMETER
        r_skel = s.SKELETON_RADIUS
        d = s.HOLE_FROM_CENTER  # 13.0

        # Base shape: inner rectangle shrunk by skeleton radius on each side
        base_rect = square(inner_size - 2 * r_skel, center=True)

        # Exclusion zones: an origin-cornered square at each hole position,
        # expanded so the four together cover most of the interior while
        # leaving material around the holes. This matches the OpenSCAD
        # approach of `hole_pattern() offset(...) square([l,l])`.
        expand = s.MAGNET_HOLE_RADIUS + r_skel + 2
        big = inner_size
        excl_base = square([big, big]).offset(delta=expand)
        excl_at_corner = excl_base.translate([d, d])
        exclusions = None
        for i in range(1, 5):
            excl = excl_at_corner.rotz(i * 90.0)
            exclusions = excl if exclusions is None else (exclusions | excl)

        skeleton = base_rect - exclusions
        return skeleton.offset(r=r_skel)

    # ------------------------------------------------------------------
    # Underside screw mounting (countersink / counterbore)
    # ------------------------------------------------------------------

    def _countersink_cutter(self):
        """Countersink screw hole for mounting the baseplate to a surface."""
        s = self.spec
        r = s.SCREW_HOLE_RADIUS + s.TOLERANCE
        return cylinder(h=2 * s.BASE_PROFILE_HEIGHT, r=r) | cone(
            r + s.BASEPLATE_SCREW_COUNTERSINK_ADDITIONAL_RADIUS,
            s.CHAMFER_ANGLE,
            2 * s.BASE_PROFILE_HEIGHT,
        )

    def _counterbore_cutter(self):
        """Counterbore screw hole for mounting the baseplate to a surface."""
        s = self.spec
        r = s.SCREW_HOLE_RADIUS + s.TOLERANCE
        cb_h = s.BASEPLATE_SCREW_COUNTERBORE_HEIGHT + 2 * s.LAYER_HEIGHT
        bore = cylinder(h=cb_h, r=s.BASEPLATE_SCREW_COUNTERBORE_RADIUS)
        printable = make_hole_printable(
            r, s.BASEPLATE_SCREW_COUNTERBORE_RADIUS, cb_h, spec=s
        )
        return cylinder(h=2 * s.BASE_PROFILE_HEIGHT, r=r) | (bore - printable)

    # ------------------------------------------------------------------
    # Screw-together channels
    # ------------------------------------------------------------------

    def _screw_together_cutouts(self, gx, gy):
        """Create horizontal screw channels between grid cells.

        Args:
            gx: Number of grid units in X.
            gy: Number of grid units in Y.

        Returns:
            A 3D PythonSCAD object, or None.
        """
        s = self.spec
        cell_size = s.GRID_SIZE
        screw_d = self.screw_diameter
        head_d = self.screw_head_diameter
        spacing = self.screw_spacing
        num_screws = self.n_screws

        def screw_line(a, b):
            """Create screw channels for one axis."""
            result = None
            # Channels along the edges perpendicular to this axis
            for sign in [1, -1]:
                x_pos = sign * a * cell_size / 2
                for _bx, by in grid_positions([1, b], [1, cell_size], center=True):
                    for _sx, sy in grid_positions(
                        [1, num_screws], [1, head_d + spacing], center=True
                    ):
                        ch = (
                            cylinder(h=cell_size / 2, d=screw_d, center=True)
                            .rotx(90)
                            .rotz(90)
                            .translate([x_pos, by + sy, 0])
                        )
                        result = ch if result is None else (result | ch)
            return result

        channels_x = screw_line(gx, gy)
        channels_y = screw_line(gy, gx)
        if channels_y is not None:
            channels_y = channels_y.rotz(90)

        if channels_x is None:
            return channels_y
        if channels_y is None:
            return channels_x
        return channels_x | channels_y

    # ------------------------------------------------------------------
    # Main render
    # ------------------------------------------------------------------

    def render(self):
        """Generate the baseplate geometry.

        Returns:
            A 3D PythonSCAD object representing the complete baseplate.
        """
        s = self.spec
        cell_size = s.GRID_SIZE
        tol = s.TOLERANCE
        add_h = self._additional_height()
        bp_h = add_h + s.BASEPLATE_HEIGHT

        grid_size, size_mm, padding_mm = self._resolve_grid_and_size()
        gx, gy = grid_size

        # Where to put excess padding (-1..1 → 0..1 fraction on positive side)
        fit_frac = [(self.fit_offset[i] + 1) / 2 for i in range(2)]

        # Starting corner of the outer block
        grid_mm = [gx * cell_size, gy * cell_size, bp_h]
        start = [
            -grid_mm[0] / 2 - padding_mm[0] * (1 - fit_frac[0]),
            -grid_mm[1] / 2 - padding_mm[1] * (1 - fit_frac[1]),
            0,
        ]

        is_minimal = self.style in ("thin", "screw_together_minimal")
        is_screw_together = self.style in ("screw_together", "screw_together_minimal")

        # ---- Outer solid block ----
        body = cube(size_mm).translate(start)

        # ---- Subtract cell cutters ----
        for cx, cy in grid_positions(grid_size, cell_size, center=True):
            if is_minimal:
                # Full-height cutter for thin/minimal styles
                cutter = self._baseplate_cutter(
                    [cell_size, cell_size], bp_h + tol
                ).translate([cx, cy, -tol / 2])
            else:
                # Lip cutter at the top, plus style-specific bottom cutouts
                cutter = self._baseplate_cutter([cell_size, cell_size]).translate(
                    [cx, cy, add_h + tol / 2]
                )

                # Bottom cutouts by style
                if self.style == "weighted":
                    cutter = cutter | self._weight_cutout().translate([cx, cy, 0])
                elif self.style in ("skeleton", "screw_together"):
                    skel = (
                        self._skeleton_profile_2d(cell_size)
                        .linear_extrude(height=add_h + 2 * tol)
                        .translate([cx, cy, -tol])
                    )
                    cutter = cutter | skel

                # Magnet/screw holes at the four positions per cell
                if self.hole_options and self.hole_options.has_any_hole:
                    hole_obj = block_base_hole(self.hole_options, spec=s)
                    if hole_obj is not None:
                        # Holes open downward from the top of add_h
                        holes = hole_pattern(
                            hole_obj.mirror([0, 0, 1]).up(add_h + tol),
                            spec=s,
                        ).translate([cx, cy, 0])
                        cutter = cutter | holes

                # Underside screw mounting
                if self.screw_style != "none":
                    if self.screw_style == "countersink":
                        screw_cut = self._countersink_cutter()
                    else:
                        screw_cut = self._counterbore_cutter()
                    screw_cuts = hole_pattern(
                        screw_cut.down(tol),
                        spec=s,
                    ).translate([cx, cy, 0])
                    cutter = cutter | screw_cuts

            body = body - cutter

        # ---- Round outside corners ----
        # The corner cutter is built in the +x/+y quadrant at the origin
        # (a square minus a quarter-circle). For each corner we:
        #   1. Rotate it to face the correct quadrant
        #   2. Translate the circle center to the inset point
        r = s.BASEPLATE_OUTER_RADIUS
        corner_specs = [
            # (inset_x, inset_y, rotation_degrees)
            (start[0] + size_mm[0] - r, start[1] + size_mm[1] - r, 0),  # NE
            (start[0] + r, start[1] + size_mm[1] - r, 90),  # NW
            (start[0] + r, start[1] + r, 180),  # SW
            (start[0] + size_mm[0] - r, start[1] + r, 270),  # SE
        ]
        for cx, cy, angle in corner_specs:
            corner = self._corner_cutter(bp_h).rotz(angle).translate([cx, cy, 0])
            body = body - corner

        # ---- Screw-together channels ----
        if is_screw_together:
            channels = self._screw_together_cutouts(gx, gy)
            if channels is not None:
                body = body - channels.up(add_h / 2)

        return body
