"""Fit checks for the facer generator (src/facer.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from params import params as P  # noqa: E402
from src.case import case  # noqa: E402
from src.facer import facer, facer_height_mm, latch_bump_center  # noqa: E402


def test_facer_width_matches_drawer_box():
    f = facer("S", 1)
    bb = f.bounding_box()
    assert bb.size.X == pytest.approx(P.drawer_box_outside_width_mm("S"))


def test_facer_height_matches_cavity_not_drawer():
    # The whole reason facer_height_mm() exists instead of reusing
    # drawer_box_outside_height_mm() directly: the facer must span the
    # full cavity height (1mm taller than the drawer) for its latch
    # bump to ever reach the skin above the drawer. Pin both facts.
    assert facer_height_mm(1) == pytest.approx(P.case_interior_height_mm(1))
    assert facer_height_mm(1) > P.drawer_box_outside_height_mm(1)


def test_facer_plate_and_knob_dimensions():
    f = facer("S", 1, with_latch=False)
    bb = f.bounding_box()
    assert bb.size.X == pytest.approx(P.drawer_box_outside_width_mm("S"))
    assert bb.size.Z == pytest.approx(facer_height_mm(1))
    assert bb.size.Y == pytest.approx(P.FACER_THICKNESS_MM + P.KNOB_PROJECTION_MM)


def test_latch_bump_straddles_both_boundaries():
    # The bump has to cross y=0 (back into case territory) AND reach
    # z=facer_height (the cavity ceiling) simultaneously — this is the
    # geometric fact that makes the latch physically reachable at all
    # (see latch_bump_center()'s docstring for why a bump centered
    # mid-plate could never work).
    f = facer("S", 1)
    bb = f.bounding_box()
    assert bb.min.Y < 0.0
    assert bb.max.Z > facer_height_mm(1)


def test_facer_fits_against_case_with_the_matching_notch():
    """The real fit check: place the case and the facer where they'd
    actually sit once assembled (facer's back face flush with the
    case's front opening, same X/Z frame as the drawer box) and confirm
    zero interference."""
    size, depth_units, floors = "S", 3, 1
    c = case(size, depth_units, floors)
    f = facer(size, floors)

    z_offset = P.INTERLOCK_PAD_HEIGHT_MM + P.CASE_TOP_BOTTOM_SKIN_MM
    case_depth = P.case_depth_mm(depth_units)
    f_placed = f.translate((P.CASE_SIDE_TOTAL_MM, case_depth, z_offset))

    assert (c & f_placed).volume < 1e-6


def test_latch_bump_interferes_with_a_case_built_without_the_notch():
    # Proves the latch bump is a real mechanical feature (genuinely
    # interferes with the plain skin) rather than just floating in
    # clearance that happens to never touch anything.
    size, depth_units, floors = "S", 3, 1
    c_no_notch = case(size, depth_units, floors, include_latch_notch=False)
    f = facer(size, floors)

    z_offset = P.INTERLOCK_PAD_HEIGHT_MM + P.CASE_TOP_BOTTOM_SKIN_MM
    case_depth = P.case_depth_mm(depth_units)
    f_placed = f.translate((P.CASE_SIDE_TOTAL_MM, case_depth, z_offset))

    assert (c_no_notch & f_placed).volume > 0.5


def test_latch_can_be_disabled_on_both_sides():
    size, depth_units, floors = "S", 3, 1
    c = case(size, depth_units, floors, include_latch_notch=False)
    f = facer(size, floors, with_latch=False)

    z_offset = P.INTERLOCK_PAD_HEIGHT_MM + P.CASE_TOP_BOTTOM_SKIN_MM
    case_depth = P.case_depth_mm(depth_units)
    f_placed = f.translate((P.CASE_SIDE_TOTAL_MM, case_depth, z_offset))

    assert (c & f_placed).volume < 1e-6


def test_unknown_size_raises():
    with pytest.raises(ValueError):
        facer("XXL", 1)
