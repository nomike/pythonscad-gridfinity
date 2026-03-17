use <gridfinity-rebuilt-openscad/src/core/wall.scad>
include <gridfinity-rebuilt-openscad/src/core/standard.scad>

// Render ONLY the wall + stacking lip for a 1x1, 2U bin.
// wall_height = height_mm - BASE_HEIGHT = 14 - 7 = 7
// grid_size_mm = [41.5, 41.5]
render_wall([41.5, 41.5, 7]);
