"""Fit checks for the case generator (src/case.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from params import params as P  # noqa: E402
from src.case import case  # noqa: E402
from src.drawer_box import drawer_box  # noqa: E402
from src.envelope import assert_fits_print_bed  # noqa: E402


def _drawer_placed_in_case(size, depth_units, floors):
    """The drawer box, translated to where it should sit inside the
    case's cavity, per params.py's stated gaps. The 1mm gap sits BEHIND
    the drawer (between its back wall and the case's) — the drawer's
    front face lands exactly flush with the case's front opening."""
    d = drawer_box(size, depth_units, floors)
    z_shell_bottom = P.INTERLOCK_PAD_HEIGHT_MM
    y_offset = P.CASE_BACK_WALL_MM + P.GAP_DRAWER_BACK_TO_CASE_BACK_MM
    return d.translate((P.CASE_SIDE_TOTAL_MM, y_offset,
                         z_shell_bottom + P.CASE_TOP_BOTTOM_SKIN_MM))


@pytest.mark.parametrize("size,depth_units,floors", [
    ("S", 3, 1),
    ("M", 4, 1),
])
def test_case_outside_bbox_matches_params(size, depth_units, floors):
    c = case(size, depth_units, floors)
    bb = c.bounding_box()
    assert bb.size.X == P.SIZES[size].case_outside_width_mm
    assert bb.size.Y == P.case_depth_mm(depth_units)
    assert bb.size.Z == P.case_outside_height_mm(floors)


@pytest.mark.parametrize("size,depth_units,floors", [
    ("S", 3, 1),
    ("M", 4, 1),
])
def test_drawer_box_fits_case_cavity_without_interference(size, depth_units, floors):
    c = case(size, depth_units, floors)
    d_placed = _drawer_placed_in_case(size, depth_units, floors)
    overlap = (c & d_placed).volume
    assert overlap < 1e-6


@pytest.mark.parametrize("size,depth_units,floors", [
    ("S", 3, 1),
    ("M", 4, 1),
])
def test_drawer_front_face_is_flush_with_case_front_opening(size, depth_units, floors):
    # Regression guard: an earlier version of case.py put the 1mm gap
    # at the FRONT (between the drawer's front face and the case's
    # front opening) instead of behind the drawer, where the brief
    # actually puts it ("drawer box sits flush with the case front").
    # Both the cavity cut and this test's drawer placement shared that
    # same wrong offset, so the overlap check above still passed —
    # this checks the actual stated fact directly instead.
    d_placed = _drawer_placed_in_case(size, depth_units, floors)
    case_depth = P.case_depth_mm(depth_units)
    assert d_placed.bounding_box().max.Y == pytest.approx(case_depth)


def test_misplaced_drawer_box_is_caught_as_interference():
    # Guards against the fit check being a silent no-op. The shift has
    # to be large enough to actually reach solid material: the slide
    # channel (x=[CASE_SIDE_OUTER_WALL_MM, CASE_SIDE_TOTAL_MM]) is now
    # genuinely open, not a blind pocket, so a small shift that stays
    # within that open region no longer collides with anything — only
    # a shift reaching past the outer wall (x < CASE_SIDE_OUTER_WALL_MM)
    # does.
    c = case("S", 3, 1)
    d = drawer_box("S", 3, 1)
    y_offset = P.CASE_BACK_WALL_MM + P.GAP_DRAWER_BACK_TO_CASE_BACK_MM
    d_bad = d.translate((P.CASE_SIDE_TOTAL_MM - 13.0, y_offset,
                          P.INTERLOCK_PAD_HEIGHT_MM + P.CASE_TOP_BOTTOM_SKIN_MM))
    overlap = (c & d_bad).volume
    assert overlap > 1.0


def test_connectors_add_real_material():
    c_with = case("S", 3, 1, include_connectors=True)
    c_without = case("S", 3, 1, include_connectors=False)
    assert c_with.volume > c_without.volume


def test_plain_shell_without_connectors_matches_skin_only_height():
    c = case("S", 3, 1, include_connectors=False)
    bb = c.bounding_box()
    expected_height = 2 * P.CASE_TOP_BOTTOM_SKIN_MM + P.case_interior_height_mm(1)
    assert bb.size.Z == pytest.approx(expected_height)
    assert bb.min.Z == pytest.approx(0.0, abs=1e-6)


def test_s_case_fits_print_bed():
    c = case("S", 3, 1)
    assert_fits_print_bed(c, label="S case, depth 3, 1 floor")


def test_unknown_size_raises():
    with pytest.raises(ValueError):
        case("XXL", 3, 1)


# --- slide channel (the case's entire contribution to the 3-member
# telescoping slide is just this open channel — no part is added; see
# src/slide.py's module docstring. tests/test_slide.py covers the real
# cross-part fit checks against the intermediate rail and the drawer's
# own rail) -----------------------------------------------------------

def test_slide_channel_opens_without_changing_outer_bbox():
    # include_slide_channel=False leaves that region solid (as the
    # whole case used to be) — so "without" has MORE material than
    # "with" (an opened channel). Either way the outer envelope is
    # identical; this is all internal.
    c_with = case("S", 3, 1, include_slide_channel=True)
    c_without = case("S", 3, 1, include_slide_channel=False)
    assert c_with.volume < c_without.volume
    assert c_with.bounding_box().size == c_without.bounding_box().size


def test_slide_channel_doesnt_reach_the_cavity():
    # The channel must not breach into the drawer cavity — confirmed
    # by the drawer box (placed exactly where it belongs) still
    # showing zero interference with a case that has its channel open.
    c = case("S", 3, 1, include_slide_channel=True)
    d_placed = _drawer_placed_in_case("S", 3, 1)
    assert (c & d_placed).volume < 1e-6


def test_slide_intermediate_outer_portion_is_real():
    # Sanity on params.py's own derived value: enough length must
    # remain for the intermediate's plain, case-captured outer portion
    # once the drawer-side channel's own depth and backing are spent.
    assert P.slide_outer_portion_length_mm() > 1.0


# --- facer latch notch — see tests/test_facer.py for the real cross-part
# fit check against the matching bump; these just cover the case's own side.

def test_latch_notch_removes_real_material_without_changing_outer_bbox():
    c_with = case("S", 3, 1, include_latch_notch=True)
    c_without = case("S", 3, 1, include_latch_notch=False)
    assert c_with.volume < c_without.volume
    assert c_with.bounding_box().size == c_without.bounding_box().size
