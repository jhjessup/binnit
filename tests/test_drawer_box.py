"""Fit checks: generated drawer box geometry must match params.py exactly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from src.drawer_box import drawer_box  # noqa: E402
from params import params as P  # noqa: E402


def test_s_drawer_box_outside_bbox_matches_params():
    # Checked WITHOUT slide rails: the rails deliberately protrude past
    # the box's own nominal outside width (they need to reach into the
    # case's channel, which lies outside the drawer's own footprint) —
    # see test_slide_rails_protrude_past_the_nominal_width below for
    # that. This test is about the plain box dimensions.
    size, depth_units, floors = "S", 3, 1
    part = drawer_box(size, depth_units, floors, include_slide_rails=False)
    bb = part.bounding_box()

    assert bb.size.X == P.drawer_box_outside_width_mm(size)
    assert bb.size.Y == P.drawer_box_outside_depth_mm(depth_units)
    assert bb.size.Z == P.drawer_box_outside_height_mm(floors)


def test_s_drawer_box_is_hollow():
    # Interior volume should be carved out: a solid box of the same outer
    # dimensions would have far more volume than the actual (walled) part.
    size, depth_units, floors = "S", 3, 1
    part = drawer_box(size, depth_units, floors, include_slide_rails=False)
    bb = part.bounding_box()
    solid_volume = bb.size.X * bb.size.Y * bb.size.Z
    assert part.volume < solid_volume


def test_slide_rails_protrude_past_the_nominal_width():
    # With rails (the default), the bounding box grows by
    # SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM on each side — the rails reach
    # outward from the drawer's own side walls into the intermediate's
    # channel.
    size, depth_units, floors = "S", 3, 1
    with_rails = drawer_box(size, depth_units, floors, include_slide_rails=True)
    without_rails = drawer_box(size, depth_units, floors, include_slide_rails=False)

    bb_with = with_rails.bounding_box()
    bb_without = without_rails.bounding_box()

    expected_width = bb_without.size.X + 2.0 * P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM
    assert bb_with.size.X == pytest.approx(expected_width)
    # Y and Z are unaffected by the side rails.
    assert bb_with.size.Y == pytest.approx(bb_without.size.Y)
    assert bb_with.size.Z == pytest.approx(bb_without.size.Z)
