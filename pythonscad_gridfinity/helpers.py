"""Helper functions for Gridfinity geometry construction.

These are general-purpose PythonSCAD utilities, not Gridfinity-specific.
They provide convenient building blocks (rounded rectangles, grid patterns,
chamfer cones, etc.) used by the baseplate and bin modules.
"""

import math
from openscad import *


def rounded_square(size, radius, center=True):
    """Create a 2D rounded rectangle.

    Uses offset(r=...) on a smaller square to produce exact circular arcs
    at the corners.

    Args:
        size: [width, height] or a single number for a square.
        radius: Corner radius. Must be less than half the smallest dimension.
        center: If True, center on the origin.

    Returns:
        A 2D PythonSCAD object.
    """
    if isinstance(size, (int, float)):
        size = [size, size]
    inner = [size[0] - 2 * radius, size[1] - 2 * radius]
    return square(inner, center=center).offset(r=radius)


def rounded_square_3d(size, radius, height, center_xy=True):
    """Create a 3D box with rounded vertical edges.

    Builds a solid block of the given height whose XY cross-section is a
    rounded rectangle. The rounding only applies to the four vertical
    edges; top and bottom faces are flat.

    Args:
        size: [width, depth] of the XY footprint.
        radius: Corner radius for the vertical edges.
        height: Z height of the block.
        center_xy: If True, center the block in X and Y (bottom at z=0).

    Returns:
        A 3D PythonSCAD object.
    """
    return rounded_square(size, radius, center=center_xy).linear_extrude(height=height)


def pattern_grid(obj, grid_size, spacing, center=True):
    """Replicate an object on a 2D grid.

    Args:
        obj: The PythonSCAD object to replicate.
        grid_size: [nx, ny] number of copies along each axis.
        spacing: [sx, sy] distance between copies, or a single number.
        center: If True, center the grid on the origin.

    Returns:
        Union of all placed copies.
    """
    if isinstance(spacing, (int, float)):
        spacing = [spacing, spacing]
    nx, ny = int(grid_size[0]), int(grid_size[1])
    if center:
        offset_x = -(nx - 1) * spacing[0] / 2
        offset_y = -(ny - 1) * spacing[1] / 2
    else:
        offset_x, offset_y = 0, 0

    result = None
    for ix in range(nx):
        for iy in range(ny):
            x = offset_x + ix * spacing[0]
            y = offset_y + iy * spacing[1]
            placed = obj.translate([x, y, 0])
            result = placed if result is None else (result | placed)
    return result


def pattern_circular(obj, n):
    """Replicate an object in a circular pattern around the Z axis.

    Places *n* copies evenly spaced by 360/n degrees, starting at 360/n
    (matching the OpenSCAD reference which starts at i=1).

    Args:
        obj: The PythonSCAD object to replicate.
        n: Number of copies.

    Returns:
        Union of all rotated copies.
    """
    result = None
    for i in range(1, n + 1):
        rotated = obj.rotz(i * 360.0 / n)
        result = rotated if result is None else (result | rotated)
    return result


def copy_mirror(obj, axis):
    """Return the union of an object and its mirror.

    Args:
        obj: PythonSCAD object.
        axis: Mirror axis vector, e.g. [1, 0, 0].

    Returns:
        Union of the original and mirrored object.
    """
    return obj | obj.mirror(axis)


def cone(bottom_radius, angle_deg, max_height=0):
    """Create a cone defined by a base radius and wall angle.

    The cone's apex is directly above the center of the base. If
    max_height is given and the natural cone height exceeds it, the
    cone is truncated (frustum).

    Args:
        bottom_radius: Radius at z=0.
        angle_deg: Angle from the base to the slant, in degrees.
        max_height: If > 0, cap the cone at this height.

    Returns:
        A 3D PythonSCAD object.
    """
    height = math.tan(math.radians(angle_deg)) * bottom_radius
    if max_height <= 0 or height <= max_height:
        return cylinder(h=height, r1=bottom_radius, r2=0)
    else:
        top_angle = 90 - angle_deg
        top_radius = bottom_radius - math.tan(math.radians(top_angle)) * max_height
        return cylinder(h=max_height, r1=bottom_radius, r2=top_radius)


def cut_chamfered_cylinder(radius, depth, chamfer_radius=0, cut_lip=False):
    """Create a chamfered cylindrical cutout for subtracting from a bin.

    The cylinder extends downward from z=0.  A 45-degree chamfer ring at
    the top aids part removal.  When *cut_lip* is True an extra tall
    cylinder at the chamfered radius extends upward to also cut through
    the stacking lip.

    Args:
        radius: Cylinder radius.
        depth: How deep the cylinder extends below z=0.
        chamfer_radius: Extra radius for the 45-degree chamfer (0 = none).
        cut_lip: If True, add an upward cylinder that cuts the lip.

    Returns:
        A 3D PythonSCAD object centered at the origin.
    """
    outer_radius = radius + chamfer_radius
    body = cylinder(h=depth, r=radius).down(depth)

    if cut_lip:
        body = body | cylinder(h=1000, r=outer_radius)

    if chamfer_radius > 0:
        body = body | cone(outer_radius, 45, depth).mirror([0, 0, 1])

    return body


def grid_positions(grid_size, spacing, center=True):
    """Yield (x, y) positions for a 2D grid.

    Args:
        grid_size: [nx, ny] number of positions.
        spacing: [sx, sy] distance between positions, or a single number.
        center: If True, center the grid on the origin.

    Yields:
        (x, y) tuples.
    """
    if isinstance(spacing, (int, float)):
        spacing = [spacing, spacing]
    nx, ny = int(grid_size[0]), int(grid_size[1])
    if center:
        offset_x = -(nx - 1) * spacing[0] / 2
        offset_y = -(ny - 1) * spacing[1] / 2
    else:
        offset_x, offset_y = 0, 0

    for ix in range(nx):
        for iy in range(ny):
            yield (offset_x + ix * spacing[0], offset_y + iy * spacing[1])
