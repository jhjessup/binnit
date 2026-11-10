"""Fit checks for the interlock dovetail rail/groove (src/interlock.py).

The important thing to verify isn't just "the functions run" — it's that
the rail and the pad's groove, correctly stacked, actually occupy
non-overlapping volumes (the real-world fit), and that a genuine
misalignment is still caught as interference (so this check isn't a
silent no-op). An earlier draft of pad_with_groove() had the groove's
taper oriented backwards — it ran without error and even "looked right"
in isolation, but didn't actually fit the rail; these tests exist
specifically to catch that class of mistake.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from params import params as P  # noqa: E402
from src.interlock import (  # noqa: E402
    connector_line_x_positions,
    pad_with_groove,
    rail,
)


def test_rail_dimensions_match_params():
    r = rail(100.0)
    bb = r.bounding_box()
    assert bb.size.Y == pytest.approx(100.0)
    assert bb.size.Z == pytest.approx(P.INTERLOCK_RAIL_HEIGHT_MM)
    assert bb.size.X == pytest.approx(P.dovetail_wide_width_mm())
    # Protrudes +Z from z=0 (the top skin's top face), not -Z.
    assert bb.min.Z == pytest.approx(0.0, abs=1e-6)
    assert bb.max.Z == pytest.approx(P.INTERLOCK_RAIL_HEIGHT_MM)


def test_pad_hangs_below_zero():
    p = pad_with_groove(100.0)
    bb = p.bounding_box()
    assert bb.min.Z == pytest.approx(-P.INTERLOCK_RAIL_HEIGHT_MM)
    assert bb.max.Z == pytest.approx(0.0, abs=1e-6)
    assert bb.size.X == pytest.approx(P.INTERLOCK_SIDE_ZONE_MM)


def test_pad_groove_actually_removes_material():
    p = pad_with_groove(100.0)
    solid_block_volume = P.INTERLOCK_SIDE_ZONE_MM * 100.0 * P.INTERLOCK_RAIL_HEIGHT_MM
    assert p.volume < solid_block_volume


def test_rail_and_pad_fit_with_clearance_and_no_interference():
    """The real fit check: stack a rail and a pad flush (skins touching,
    so the pad's attachment face sits exactly at the rail's tip height)
    and confirm the two solids don't overlap at all."""
    r = rail(100.0)
    p = pad_with_groove(100.0)
    p_stacked = p.translate((0, 0, P.INTERLOCK_RAIL_HEIGHT_MM))
    overlap = r & p_stacked
    assert overlap.volume < 1e-6


def test_lateral_misalignment_is_caught_as_interference():
    """Guards against the fit check being a silent no-op: a real 1mm
    sideways misalignment must actually show up as overlapping volume."""
    r = rail(100.0)
    p = pad_with_groove(100.0)
    p_stacked = p.translate((0, 0, P.INTERLOCK_RAIL_HEIGHT_MM))
    p_shifted = p_stacked.translate((1.0, 0, 0))
    overlap = r & p_shifted
    assert overlap.volume > 1.0


def test_zero_clearance_is_the_tight_boundary_case():
    """With no clearance at all, rail and groove should still just
    barely not overlap (boundary case) — if this showed interference,
    the clearance accounting would be backwards somewhere."""
    r = rail(100.0)
    p = pad_with_groove(100.0, clearance_mm=0.0)
    p_stacked = p.translate((0, 0, P.INTERLOCK_RAIL_HEIGHT_MM))
    overlap = r & p_stacked
    assert overlap.volume < 1e-6


def test_connector_line_x_positions_matches_stated_rule():
    # Line *count* follows the stated n+1 rule exactly; the two end
    # lines are inset by half the side zone so their footprint stays
    # inside the case's own side walls (see connector_line_x_positions'
    # docstring) rather than straddling the outer edge.
    inset = P.INTERLOCK_SIDE_ZONE_MM / 2.0
    for bays in (1, 2, 3, 4):
        positions = connector_line_x_positions(bays)
        assert len(positions) == P.interlock_connector_line_count(bays)
        assert positions[0] == pytest.approx(inset)
        assert positions[-1] == pytest.approx(bays * P.BAY_PITCH_MM - inset)
        # interior lines (if any) sit exactly on the raw bay boundary
        for i, pos in enumerate(positions[1:-1], start=1):
            assert pos == pytest.approx(i * P.BAY_PITCH_MM)


def test_end_connector_lines_stay_within_the_side_wall():
    # The real reason for the inset: an end connector's own footprint
    # (INTERLOCK_SIDE_ZONE_MM wide, centered on its line) must not cross
    # the case's outer edge.
    half_zone = P.INTERLOCK_SIDE_ZONE_MM / 2.0
    for bays in (1, 2, 3, 4):
        positions = connector_line_x_positions(bays)
        case_outside_width = bays * P.BAY_PITCH_MM
        assert positions[0] - half_zone >= -1e-9
        assert positions[-1] + half_zone <= case_outside_width + 1e-9
