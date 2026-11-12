"""Fit checks for the 3-member telescoping slide (src/slide.py).

As with the interlock dovetail, the important thing to verify isn't
just "the functions run" — it's that the rail and channel shapes
actually occupy non-overlapping volumes at the correct alignment, and
that a genuine misalignment is caught as real interference (so the
check isn't a silent no-op). There is no case-side rail anymore (see
module docstring: the case's own existing open channel does that job),
so these tests focus on the drawer rail / intermediate channel
interface, plus confirming the intermediate's outer portion actually
fits the case's channel opening with no feature of its own needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from build123d import Align, Box  # noqa: E402

from params import params as P  # noqa: E402
from src.slide import intermediate_rail, rail  # noqa: E402


def test_rail_dimensions_match_params():
    r = rail(100.0, direction=+1, depth_mm=P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM)
    bb = r.bounding_box()
    assert bb.size.Y == pytest.approx(100.0)
    assert bb.min.X == pytest.approx(0.0, abs=1e-6)
    assert bb.max.X == pytest.approx(P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM)
    assert bb.size.Z == pytest.approx(P.slide_tab_width_mm())


def test_rail_direction_flips_correctly():
    r_pos = rail(50.0, direction=+1, depth_mm=P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM)
    r_neg = rail(50.0, direction=-1, depth_mm=P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM)
    assert r_pos.bounding_box().min.X == pytest.approx(0.0, abs=1e-6)
    assert r_pos.bounding_box().max.X == pytest.approx(P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM)
    assert r_neg.bounding_box().max.X == pytest.approx(0.0, abs=1e-6)
    assert r_neg.bounding_box().min.X == pytest.approx(-P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM)


def test_intermediate_spans_the_full_channel_budget():
    inter = intermediate_rail(50.0, floors=1)
    bb = inter.bounding_box()
    assert bb.min.X == pytest.approx(0.0, abs=1e-6)
    assert bb.max.X == pytest.approx(P.slide_intermediate_thickness_mm())


def test_intermediate_outer_portion_is_fully_solid():
    # The case's own existing channel does the capturing — the
    # intermediate's outer portion must have NO feature cut into it at
    # all, or there'd be nothing for that pre-existing geometry to
    # bear against.
    inter = intermediate_rail(50.0, floors=1)
    outer_len = P.slide_outer_portion_length_mm()
    z_h = P.slide_intermediate_z_height_mm(1)
    probe = Box(outer_len, 50.0, z_h, align=(Align.MIN, Align.MIN, Align.CENTER))
    assert (inter & probe).volume == pytest.approx(probe.volume, rel=1e-6)


def test_intermediate_inner_channel_actually_removes_material():
    inter = intermediate_rail(50.0, floors=1)
    bb = inter.bounding_box()
    solid_volume = bb.size.X * bb.size.Y * bb.size.Z
    assert inter.volume < solid_volume


def test_drawer_rail_fits_intermediate_inner_channel_with_no_interference():
    thickness = P.slide_intermediate_thickness_mm()
    drawer_rail = rail(20.0, direction=-1,
                        depth_mm=P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM)
    drawer_rail = drawer_rail.translate((thickness, 0, 0))
    inter = intermediate_rail(50.0, floors=1)
    assert (inter & drawer_rail).volume < 1e-6


def test_misaligned_drawer_rail_is_caught_as_interference():
    # Guards against the fit check being a silent no-op.
    thickness = P.slide_intermediate_thickness_mm()
    drawer_rail = rail(20.0, direction=-1,
                        depth_mm=P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM)
    drawer_rail = drawer_rail.translate((thickness, 0, 0))
    drawer_rail_bad = drawer_rail.translate((0, 0, 1.0))
    inter = intermediate_rail(50.0, floors=1)
    assert (inter & drawer_rail_bad).volume > 1.0


def test_drawer_rail_shorter_than_intermediate_at_minimum_depth():
    # params.py's own invariant, re-checked here directly.
    assert P.SLIDE_DRAWER_RAIL_LENGTH_MM < P.slide_intermediate_length_mm(P.DEPTH_MIN_UNITS)


def test_drawer_rail_stays_engaged_across_its_full_stage_1_travel():
    """Not just a single static position: slide the drawer rail through
    its entire available stage-1 travel (from fully home to the point
    where it reaches the end of the intermediate's own channel) and
    confirm zero interference at every sampled point — a real range of
    motion, not a snapshot."""
    thickness = P.slide_intermediate_thickness_mm()
    inter_len = P.slide_intermediate_length_mm(P.DEPTH_MIN_UNITS)
    inter = intermediate_rail(inter_len, floors=1)
    max_travel = inter_len - P.SLIDE_DRAWER_RAIL_LENGTH_MM
    assert max_travel > 0

    for pull in (0.0, max_travel * 0.25, max_travel * 0.5, max_travel * 0.75, max_travel):
        drawer_rail = rail(P.SLIDE_DRAWER_RAIL_LENGTH_MM, direction=-1,
                            depth_mm=P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM)
        drawer_rail = drawer_rail.translate((thickness, pull, 0))
        overlap = (inter & drawer_rail).volume
        assert overlap < 1e-6, f"interference at pull={pull}mm: {overlap}"
