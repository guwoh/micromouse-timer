from __future__ import annotations

from core.models import RoiBundle


def build_rois(
    map_size: tuple[int, int],
    start_corner: str = "top_left",
    start_line_thickness_pct: float = 0.03,
    goal_size_pct: float = 0.16,
    inset_pct: float = 0.0,
) -> RoiBundle:
    w, h = map_size
    ix = int(w * inset_pct)
    iy = int(h * inset_pct)

    eff_w = w - 2 * ix
    eff_h = h - 2 * iy

    line_t = max(2, int(min(eff_w, eff_h) * start_line_thickness_pct))
    goal_s = max(10, int(min(eff_w, eff_h) * goal_size_pct))
    cx, cy = w // 2, h // 2

    # Assuming standard 16x16 micromouse maze
    cell_w = eff_w // 16
    cell_h = eff_h // 16

    # The start line is the exit edge (mép) of the starting cell in standard orientation
    if start_corner == "top_right":
        start_line = (w - ix - cell_w, iy + cell_h, cell_w, line_t)
    elif start_corner == "bottom_right":
        start_line = (w - ix - cell_w, h - iy - cell_h - line_t, cell_w, line_t)
    elif start_corner == "bottom_left":
        start_line = (ix, h - iy - cell_h - line_t, cell_w, line_t)
    else: # top_left
        start_line = (ix, iy + cell_h, cell_w, line_t)

    goal_area = (cx - goal_s // 2, cy - goal_s // 2, goal_s, goal_s)
    return RoiBundle(start_line=start_line, goal_area=goal_area)
