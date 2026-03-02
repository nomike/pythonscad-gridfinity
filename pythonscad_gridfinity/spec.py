"""Gridfinity standard dimensions and specifications.

All measurements are in millimeters unless noted otherwise.
Based on https://gridfinity.xyz/specification/ and the
gridfinity-rebuilt-openscad reference implementation.
"""

import math


class GridfinitySpec:
    """Encapsulates all Gridfinity standard dimensions.

    This class serves as the single source of truth for the Gridfinity
    standard. All measurements are class-level constants so they can be
    referenced without instantiation, but an instance can be created if
    you need to pass the spec around or override values in the future.
    """

    # ------------------------------------------------------------------
    # Grid dimensions
    # ------------------------------------------------------------------
    GRID_SIZE = 42.0  # one grid unit in mm (both X and Y)

    # Small tolerance to prevent zero-thickness walls in boolean ops
    TOLERANCE = 0.02

    # ------------------------------------------------------------------
    # Base profile (the shape on the bottom of every bin)
    # Based on https://gridfinity.xyz/specification/
    # Each point is [horizontal_offset, vertical_offset] from the
    # innermost bottom point of the profile.
    # ------------------------------------------------------------------
    BASE_PROFILE = [
        [0.0, 0.0],  # innermost bottom point
        [0.8, 0.8],  # 45-degree chamfer up and out
        [0.8, 2.6],  # vertical section (0.8 + 1.8)
        [2.95, 4.75],  # 45-degree chamfer up and out (0.8+2.15, 0.8+1.8+2.15)
    ]

    BASE_TOP_DIMENSIONS = [41.5, 41.5]  # top of each base unit
    BASE_GAP = 0.5  # gap between adjacent bases (per side)
    BASE_TOP_RADIUS = 3.75  # corner radius at the top of the base (7.5/2)
    BASE_BOTTOM_RADIUS = BASE_TOP_RADIUS - BASE_PROFILE[3][0]  # ~0.8
    BASE_PROFILE_HEIGHT = BASE_PROFILE[3][1]  # 4.75
    BASE_HEIGHT = 7.0  # total base height including bridge
    BASE_BRIDGE_HEIGHT = BASE_HEIGHT - BASE_PROFILE_HEIGHT  # 2.25

    # ------------------------------------------------------------------
    # Baseplate profile (the socket that receives the base)
    # Slightly different from the base profile itself.
    # ------------------------------------------------------------------
    BASEPLATE_PROFILE = [
        [0.0, 0.0],  # innermost bottom point
        [0.7, 0.7],  # 45-degree chamfer
        [0.7, 2.5],  # vertical section (0.7 + 1.8)
        [2.85, 4.65],  # 45-degree chamfer (0.7+2.15, 0.7+1.8+2.15)
    ]

    BASEPLATE_DIMENSIONS = [42.0, 42.0]
    BASEPLATE_HEIGHT = 5.0  # minimum baseplate height (profile + clearance)
    BASEPLATE_OUTER_DIAMETER = 8.0
    BASEPLATE_OUTER_RADIUS = BASEPLATE_OUTER_DIAMETER / 2  # 4.0
    BASEPLATE_INNER_RADIUS = BASEPLATE_OUTER_RADIUS - BASEPLATE_PROFILE[3][0]  # 1.15
    BASEPLATE_INNER_DIAMETER = BASEPLATE_INNER_RADIUS * 2

    # ------------------------------------------------------------------
    # Magnet and screw hole dimensions
    # ------------------------------------------------------------------
    LAYER_HEIGHT = 0.2  # typical FDM layer height for supportless features
    MAGNET_HEIGHT = 2.0
    MAGNET_HOLE_RADIUS = 6.5 / 2  # for 6 mm diameter magnets
    MAGNET_HOLE_DEPTH = MAGNET_HEIGHT + (LAYER_HEIGHT * 2)  # 2.4
    SCREW_HOLE_RADIUS = 3.0 / 2  # M3 screw

    # Distance of hole center from the side of a grid unit
    HOLE_FROM_SIDE = 8.0
    # Distance of hole center from the center of a grid unit
    HOLE_FROM_CENTER = GRID_SIZE / 2 - HOLE_FROM_SIDE  # 13.0

    # Spec value from https://gridfinity.xyz/specification/
    HOLE_DISTANCE_FROM_BOTTOM_EDGE = 4.8

    # ------------------------------------------------------------------
    # Crush rib dimensions (press-fit magnet holes)
    # ------------------------------------------------------------------
    MAGNET_HOLE_CRUSH_RIB_INNER_RADIUS = 5.9 / 2  # 2.95
    MAGNET_HOLE_CRUSH_RIB_COUNT = 8

    # ------------------------------------------------------------------
    # Chamfer dimensions for magnet/screw holes
    # ------------------------------------------------------------------
    CHAMFER_ADDITIONAL_RADIUS = 0.8
    CHAMFER_ANGLE = 45

    # ------------------------------------------------------------------
    # Refined hole (Gridfinity Refined by @grizzie17)
    # Magnet inserted from the side, held by friction
    # ------------------------------------------------------------------
    REFINED_HOLE_RADIUS = 5.86 / 2
    REFINED_HOLE_HEIGHT = MAGNET_HEIGHT - 0.1  # 1.9
    REFINED_HOLE_BOTTOM_LAYERS = 2

    # ------------------------------------------------------------------
    # Baseplate screw mounting (underside screws for mounting to surface)
    # ------------------------------------------------------------------
    BASEPLATE_SCREW_COUNTERSINK_ADDITIONAL_RADIUS = 5.0 / 2  # 2.5
    BASEPLATE_SCREW_COUNTERBORE_RADIUS = 5.5 / 2  # 2.75
    BASEPLATE_SCREW_COUNTERBORE_HEIGHT = 3.0

    # ------------------------------------------------------------------
    # Weighted baseplate dimensions
    # ------------------------------------------------------------------
    BP_H_BOT = 6.4  # extra height for weighted baseplate bottom
    BP_CUT_SIZE = 21.4  # rectangular weight cutout size
    BP_CUT_DEPTH = 4.0  # rectangular weight cutout depth
    BP_RCUT_WIDTH = 8.5  # rounded cutout width
    BP_RCUT_LENGTH = 4.25  # rounded cutout length
    BP_RCUT_DEPTH = 2.0  # rounded cutout depth

    # ------------------------------------------------------------------
    # Skeletonized baseplate
    # ------------------------------------------------------------------
    SKELETON_RADIUS = 2.0  # radius of cutout for skeleton pattern
    SKELETON_MIN_THICKNESS = 1.0  # minimum remaining wall thickness

    # ------------------------------------------------------------------
    # Screw-together baseplate defaults
    # ------------------------------------------------------------------
    SCREW_TOGETHER_HEIGHT = 6.75  # extra height for screw-together style

    # ------------------------------------------------------------------
    # Wall / divider / lip constants (used by bins)
    # ------------------------------------------------------------------
    HEIGHT_UNIT = 7.0  # mm per Gridfinity height unit
    WALL_THICKNESS = 0.95
    FILLET_RADIUS = 2.8  # internal fillet radius (r_f2)
    FILLET_RADIUS_TOP = 0.6  # top-edge fillet radius (r_f1)
    DIVIDER_WIDTH = 1.2
    FIT_CLEARANCE = BASE_GAP / 2  # 0.25, tolerance between bin and grid
    FLOOR_THICKNESS = BASE_HEIGHT - BASE_PROFILE_HEIGHT  # 2.25

    # Stacking lip profile (points from inner wall outward/upward)
    STACKING_LIP_PROFILE = [
        [0.0, 0.0],
        [0.7, 0.7],
        [0.7, 2.5],
        [2.6, 4.4],  # 0.7+1.9, 0.7+1.8+1.9
    ]
    STACKING_LIP_HEIGHT = STACKING_LIP_PROFILE[3][1]  # 4.4
    STACKING_LIP_DEPTH = STACKING_LIP_PROFILE[3][0]  # 2.6
    STACKING_LIP_FILLET_RADIUS = 0.6
    STACKING_LIP_SUPPORT_HEIGHT = 1.2
    # d_wall2 from OpenSCAD: r_base - r_c1 - d_clear*sqrt(2)
    STACKING_LIP_SUPPORT_TAPER = (
        BASE_TOP_RADIUS - BASE_PROFILE[1][0] - FIT_CLEARANCE * math.sqrt(2)
    )

    # Tab constants
    TAB_WIDTH_NOMINAL = 42.0
    TAB_DEPTH = 15.85
    TAB_SUPPORT_ANGLE = 36
    TAB_SUPPORT_HEIGHT = 1.2
    TAB_HEIGHT = (
        math.tan(math.radians(TAB_SUPPORT_ANGLE)) * TAB_DEPTH + TAB_SUPPORT_HEIGHT
    )
