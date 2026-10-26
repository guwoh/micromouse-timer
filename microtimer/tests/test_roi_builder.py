from vision.roi_builder import build_rois


def test_roi_generation():
    rois = build_rois((800, 800), start_corner="top_left")
    sx, sy, sw, sh = rois.start_line
    gx, gy, gw, gh = rois.goal_area
    assert sw > 0 and sh > 0
    assert gw > 0 and gh > 0
    assert sx >= 0 and sy >= 0
    assert gx >= 0 and gy >= 0
