"""Magnet and screw hole geometry for Gridfinity objects.

Provides configurable hole options and functions to generate the
various hole types used in Gridfinity baseplates and bins:
  - Standard magnet holes (6 mm diameter x 2 mm)
  - Crush-rib press-fit magnet holes
  - Chamfered holes for easier magnet insertion
  - Supportless (printable) hole variants
  - Gridfinity Refined side-insert magnet holes
  - M3 screw holes with optional countersink/counterbore
"""

import math
from dataclasses import dataclass

from openscad import *

from .spec import GridfinitySpec
from .helpers import cone


@dataclass
class HoleOptions:
    """Configuration for magnet/screw holes in a Gridfinity object.

    Attributes:
        magnet_hole: Include a hole sized for a 6 mm x 2 mm magnet.
        screw_hole: Include a hole sized for an M3 screw beneath the magnet.
        crush_ribs: Add crush ribs inside the magnet hole for a press fit.
        chamfer: Add a 45-degree chamfer around the hole opening.
        supportless: Modify the hole so it prints without supports.
        refined_hole: Use the Gridfinity Refined side-insert style.
                      Mutually exclusive with magnet_hole.
    """

    magnet_hole: bool = False
    screw_hole: bool = False
    crush_ribs: bool = False
    chamfer: bool = True
    supportless: bool = False
    refined_hole: bool = False

    def __post_init__(self):
        if self.refined_hole and self.magnet_hole:
            raise ValueError("refined_hole and magnet_hole are mutually exclusive")

    @property
    def has_any_hole(self):
        """True if any hole feature is enabled."""
        return self.magnet_hole or self.screw_hole or self.refined_hole


def ribbed_circle(outer_radius, inner_radius, ribs, fn=256):
    """Create a 2D circle with sinusoidal crush ribs.

    The resulting shape oscillates between inner_radius and outer_radius,
    producing *ribs* full wave cycles around the circumference.

    Args:
        outer_radius: Maximum radius (at rib peaks).
        inner_radius: Minimum radius (between ribs).
        ribs: Number of full sinusoidal waves.
        fn: Number of polygon vertices (high default for smooth ribs).

    Returns:
        A 2D PythonSCAD polygon.
    """
    wave_range = (outer_radius - inner_radius) / 2
    wave_center = inner_radius + wave_range
    points = []
    for i in range(fn):
        angle = i * 360.0 / fn
        r = math.sin(math.radians(angle * ribs)) * wave_range + wave_center
        x = math.sin(math.radians(angle)) * r
        y = math.cos(math.radians(angle)) * r
        points.append([x, y])
    return polygon(points)


def ribbed_cylinder(outer_radius, inner_radius, height, ribs, fn=256):
    """Create a cylinder with sinusoidal crush ribs.

    Extrudes a ribbed_circle to the given height.

    Args:
        outer_radius: Maximum radius.
        inner_radius: Minimum radius.
        height: Cylinder height.
        ribs: Number of crush ribs.
        fn: Polygon resolution.

    Returns:
        A 3D PythonSCAD object.
    """
    return ribbed_circle(outer_radius, inner_radius, ribs, fn=fn).linear_extrude(
        height=height
    )


def make_hole_printable(inner_radius, outer_radius, outer_height, layers=2, spec=None):
    """Create the negative shape that makes a hole printable without supports.

    This generates thin bridging layers at the top of the hole that allow
    the slicer to bridge across the opening. The shape is designed to be
    *subtracted* from the hole cylinder using difference().

    Based on the technique shown at https://www.youtube.com/watch?v=W8FbHTcB05w

    Args:
        inner_radius: Radius of the inner through-hole (or 0.5 if none).
        outer_radius: Radius of the outer hole being bridged.
        outer_height: Total height of the outer hole.
        layers: Number of bridging layers.
        spec: GridfinitySpec instance (uses defaults if None).

    Returns:
        A 3D PythonSCAD object to subtract from the hole.
    """
    if spec is None:
        spec = GridfinitySpec()
    tol = spec.TOLERANCE
    lh = spec.LAYER_HEIGHT

    calc_layers = max(layers - 1, 1)
    cube_h = lh + 2 * tol
    inner_d = 2 * (inner_radius + tol)
    outer_d = 2 * (outer_radius + tol)
    per_layer_diff = (outer_d - inner_d) / calc_layers

    height_adj = outer_height - (layers * lh)

    # Outer block that fills the bridging zone
    block = cube([outer_d + tol, outer_d + tol, layers * cube_h], center=True).up(
        layers * cube_h / 2 + height_adj
    )

    # Cutouts for each bridging layer: alternating 90-degree oriented slots
    cutouts = None
    for i in range(1, calc_layers + 1):
        w1 = outer_d - per_layer_diff * (i - 1)
        w2 = outer_d - per_layer_diff * i
        z = cube_h / 2 - tol + height_adj + (i - 1) * lh
        rot = 90.0 if (i % 2 == 0) else 0.0
        slot = cube([w1, w2, cube_h], center=True).rotz(rot).up(z)
        cutouts = slot if cutouts is None else (cutouts | slot)

    # Last layer gets a square cutout (equal width both axes)
    if layers > 1:
        i = layers
        w1 = outer_d - per_layer_diff * (i - 1)
        z = cube_h / 2 - tol + height_adj + (i - 1) * lh
        rot = 90.0 if (i % 2 == 0) else 0.0
        last = cube([w1, w1, cube_h], center=True).rotz(rot).up(z)
        cutouts = cutouts | last

    return block - cutouts if cutouts is not None else block


def _magnet_hole_body(spec, options):
    """Build the magnet hole cylinder (with or without crush ribs).

    Args:
        spec: GridfinitySpec instance.
        options: HoleOptions.

    Returns:
        A 3D PythonSCAD object, or None if magnet_hole is disabled.
    """
    if not options.magnet_hole:
        return None

    extra_layers = (2 if options.screw_hole else 3) if options.supportless else 0
    depth = spec.MAGNET_HOLE_DEPTH + extra_layers * spec.LAYER_HEIGHT

    if options.crush_ribs:
        body = ribbed_cylinder(
            spec.MAGNET_HOLE_RADIUS,
            spec.MAGNET_HOLE_CRUSH_RIB_INNER_RADIUS,
            depth,
            spec.MAGNET_HOLE_CRUSH_RIB_COUNT,
        )
    else:
        body = cylinder(h=depth, r=spec.MAGNET_HOLE_RADIUS)

    if options.supportless:
        bridge_r = spec.SCREW_HOLE_RADIUS if options.screw_hole else 0.5
        printable = make_hole_printable(
            bridge_r,
            spec.MAGNET_HOLE_RADIUS,
            depth,
            layers=(2 if options.screw_hole else 3),
            spec=spec,
        )
        body = body - printable

    return body


def _screw_hole_body(spec, options):
    """Build the screw hole cylinder with optional chamfer.

    Args:
        spec: GridfinitySpec instance.
        options: HoleOptions.

    Returns:
        A 3D PythonSCAD object, or None if screw_hole is disabled.
    """
    if not options.screw_hole:
        return None

    radius = spec.SCREW_HOLE_RADIUS
    depth = spec.BASE_HEIGHT

    body = cylinder(h=depth, r=radius)

    if options.supportless:
        printable = make_hole_printable(0.5, radius, depth, layers=3, spec=spec)
        body = body - printable

    if options.chamfer:
        body = body | cone(
            radius + spec.CHAMFER_ADDITIONAL_RADIUS,
            spec.CHAMFER_ANGLE,
            depth,
        )

    return body


def refined_hole(spec=None):
    """Create a Gridfinity Refined magnet hole.

    The magnet is inserted from the +X direction and held by friction.
    A small poke-through hole on the bottom allows removal with a
    toothpick.

    Based on https://www.printables.com/model/413761-gridfinity-refined

    Args:
        spec: GridfinitySpec instance (uses defaults if None).

    Returns:
        A 3D PythonSCAD object (to be subtracted from the base).
    """
    if spec is None:
        spec = GridfinitySpec()

    refined_offset = spec.LAYER_HEIGHT * spec.REFINED_HOLE_BOTTOM_LAYERS
    r = spec.REFINED_HOLE_RADIUS
    h = spec.REFINED_HOLE_HEIGHT

    # Extra layer clearance for the poke-through hole
    ptl = refined_offset + spec.LAYER_HEIGHT
    poke_h = h + ptl
    poke_r = 2.5
    magic = 5.60
    poke_cx = -12.53 + magic

    main = (
        # Rectangular slot for magnet insertion from +X
        cube([11, r * 2, h]).translate([0, -r, 0])
        # Cylindrical magnet pocket
        | cylinder(h=h, r=r)
    ).up(refined_offset)

    poke = (
        cube([10 - magic, poke_r, poke_h]).translate([poke_cx, -poke_r / 2, 0])
        | cylinder(h=poke_h, d=poke_r).translate([poke_cx, 0, 0])
    ).up(-ptl + refined_offset)

    return main | poke


def block_base_hole(options, spec=None):
    """Create a single combined magnet/screw hole for a grid cell.

    This is the main entry point for generating hole geometry. It
    assembles the appropriate combination of magnet hole, screw hole,
    crush ribs, chamfer, and supportless features based on the options.

    The hole is oriented with the opening at z=0, extending downward
    into -Z (caller should mirror/translate as needed).

    Args:
        options: HoleOptions instance.
        spec: GridfinitySpec instance (uses defaults if None).

    Returns:
        A 3D PythonSCAD object, or None if no holes are enabled.
    """
    if spec is None:
        spec = GridfinitySpec()

    if not options.has_any_hole:
        return None

    result = None

    if options.refined_hole:
        result = refined_hole(spec)

    magnet = _magnet_hole_body(spec, options)
    if magnet is not None:
        result = magnet if result is None else (result | magnet)
        if options.chamfer:
            chamfer_cone = cone(
                spec.MAGNET_HOLE_RADIUS + spec.CHAMFER_ADDITIONAL_RADIUS,
                spec.CHAMFER_ANGLE,
                spec.MAGNET_HOLE_DEPTH,
            )
            result = result | chamfer_cone

    screw = _screw_hole_body(spec, options)
    if screw is not None:
        result = screw if result is None else (result | screw)

    return result


def hole_pattern(obj, spec=None):
    """Place an object at the four hole positions within a single grid cell.

    The four positions are at (+-d, +-d) where d = HOLE_FROM_CENTER,
    matching the Gridfinity standard layout. The object is first
    translated to (d, d) then rotated by 90-degree increments, placing
    copies at all four corners.

    Args:
        obj: PythonSCAD object to replicate.
        spec: GridfinitySpec instance (uses defaults if None).

    Returns:
        Union of four copies of the object.
    """
    if spec is None:
        spec = GridfinitySpec()
    d = spec.HOLE_FROM_CENTER  # 13.0
    at_corner = obj.translate([d, d, 0])
    result = None
    for i in range(1, 5):
        placed = at_corner.rotz(i * 90.0)
        result = placed if result is None else (result | placed)
    return result
