"""Fit checks: generated drawer box geometry must match params.py exactly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.drawer_box import drawer_box  # noqa: E402
from params import params as P  # noqa: E402


def test_s_drawer_box_outside_bbox_matches_params():
    size, depth_units, floors = "S", 3, 1
    part = drawer_box(size, depth_units, floors)
    bb = part.bounding_box()

    assert bb.size.X == P.drawer_box_outside_width_mm(size)
    assert bb.size.Y == P.drawer_box_outside_depth_mm(depth_units)
    assert bb.size.Z == P.drawer_box_outside_height_mm(floors)


def test_s_drawer_box_is_hollow():
    # Interior volume should be carved out: a solid box of the same outer
    # dimensions would have far more volume than the actual (walled) part.
    size, depth_units, floors = "S", 3, 1
    part = drawer_box(size, depth_units, floors)
    bb = part.bounding_box()
    solid_volume = bb.size.X * bb.size.Y * bb.size.Z
    assert part.volume < solid_volume
