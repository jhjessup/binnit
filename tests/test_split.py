"""Tests for splitting oversized parts to fit the print bed (src/split.py).

Covers two separate decisions:
1. Which grid a split lands on — the 42mm internal grid, not the 164mm
   bay pitch (see test_default_grid_pitch_is_the_internal_42mm_grid and
   test_voron_zero_sized_bed_can_still_split_on_the_internal_grid).
2. What joins split halves back together — a repeating chevron ("zigzag
   finger joint"), self-aligning and meant to be glued, on by default
   (see the test_chevron_* tests). `joint=False` reverts to a plain flat
   butt cut, exercised by the test_*_flat_cut tests, which also serve as
   the simpler mechanism tests independent of joint geometry.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from build123d import Align, Box  # noqa: E402

from params import params as P  # noqa: E402
from src.split import SplitError, split_to_fit  # noqa: E402


def _box(x, y, z=40.0):
    return Box(x, y, z, align=(Align.MIN, Align.MIN, Align.MIN))


# --- mechanism tests (joint=False: plain flat cut) -------------------------

def test_part_that_already_fits_is_not_split():
    part = _box(100, 100)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0)
    assert len(pieces) == 1
    assert pieces[0].grid_index == (0, 0)
    assert pieces[0].part.volume == pytest.approx(part.volume)


def test_flat_cut_is_split_into_bed_sized_pieces():
    part = _box(400, 300)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0, joint=False)

    assert len(pieces) == 4  # 2 cuts in X (400mm -> 164/236), 1 in Y (300mm -> 164/136)
    for piece in pieces:
        bb = piece.part.bounding_box()
        assert bb.size.X <= 250.0 + 1e-6
        assert bb.size.Y <= 250.0 + 1e-6


def test_flat_cut_pieces_conserve_total_volume_exactly():
    # No clearance gap with joint=False, so this should be an exact partition.
    part = _box(400, 300)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0, joint=False)
    assert sum(p.part.volume for p in pieces) == pytest.approx(part.volume, rel=1e-6)


def test_flat_cut_pieces_are_each_relocated_to_their_own_local_origin():
    part = _box(400, 300)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0, joint=False)
    for piece in pieces:
        bb = piece.part.bounding_box()
        assert bb.min.X == pytest.approx(0.0, abs=1e-6)
        assert bb.min.Y == pytest.approx(0.0, abs=1e-6)


def test_grid_too_coarse_raises_split_error():
    part = _box(1000, 10)
    with pytest.raises(SplitError):
        split_to_fit(part, grid_pitch_mm=500.0, bed_xy_mm=250.0, joint=False)


# --- grid pitch decision: 42mm internal, not 164mm bay pitch ---------------

def test_default_grid_pitch_is_the_internal_42mm_grid():
    assert P.SPLIT_GRID_PITCH_MM == P.GRID_PITCH_MM == 42.0

    part = _box(400, 300)
    default_pieces = split_to_fit(part, bed_xy_mm=250.0, joint=False)
    explicit_pieces = split_to_fit(part, grid_pitch_mm=42.0, bed_xy_mm=250.0, joint=False)
    assert len(default_pieces) == len(explicit_pieces)


def test_voron_zero_sized_bed_can_still_split_on_the_internal_grid():
    # A part the size of one S-case bay (164mm wide) doesn't fit a Voron
    # Zero's 120x120mm bed, but splits fine on the internal grid.
    bay_width_part = _box(P.BAY_PITCH_MM, 100.0)
    voron_zero_bed_xy = 120.0

    pieces = split_to_fit(bay_width_part, bed_xy_mm=voron_zero_bed_xy, joint=False)

    assert len(pieces) > 1  # one 164mm-wide bay does not fit a 120mm bed
    for piece in pieces:
        bb = piece.part.bounding_box()
        assert bb.size.X <= voron_zero_bed_xy + 1e-6
        assert bb.size.Y <= voron_zero_bed_xy + 1e-6

    # The bay pitch itself would be useless as the split grid here: the
    # very first grid line (164mm) already exceeds the bed.
    with pytest.raises(SplitError):
        split_to_fit(bay_width_part, grid_pitch_mm=P.BAY_PITCH_MM,
                     bed_xy_mm=voron_zero_bed_xy, joint=False)


# --- joint decision: chevron, self-aligning, glued (joint=True, default) ---

def test_chevron_is_the_default():
    part = _box(400, 90)
    default_pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0)
    explicit_pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0,
                                    joint=True)
    assert len(default_pieces) == len(explicit_pieces) == 2
    for a, b in zip(default_pieces, explicit_pieces):
        assert a.part.volume == pytest.approx(b.part.volume, rel=1e-9)


def test_chevron_pieces_still_fit_the_bed():
    part = _box(400, 300)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0)
    assert len(pieces) == 4
    for piece in pieces:
        bb = piece.part.bounding_box()
        assert bb.size.X <= 250.0 + 1e-6
        assert bb.size.Y <= 250.0 + 1e-6


def test_chevron_joint_uses_params_dimensions_by_default():
    # A bigger tooth amplitude should make each piece's bounding box
    # overshoot the nominal cut line by more (the tooth peaks reach
    # further past it) — a real, visible effect of feature_size_mm.
    # (Volume itself is ~unaffected: a symmetric zigzag swaps an equal
    # wedge of material from one piece to its neighbor, net zero.)
    part = _box(400, 90)
    default_pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0)
    bigger_tooth_pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0,
                                        feature_size_mm=5.0)

    default_overshoot = default_pieces[0].part.bounding_box().size.X - 164.0
    bigger_overshoot = bigger_tooth_pieces[0].part.bounding_box().size.X - 164.0
    assert bigger_overshoot > default_overshoot
    assert default_overshoot == pytest.approx(P.SPLIT_JOINT_FEATURE_SIZE_MM,
                                                abs=0.1)


def test_chevron_cut_removes_only_the_clearance_gap_volume():
    # With joint=True, the two pieces no longer exactly partition the
    # original volume — a thin sliver equal to the clearance gap is
    # genuinely removed. It should be small (a few hundred mm^3 for a
    # 1440000 mm^3 part), not a large fraction of the part.
    part = _box(400, 90)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0)
    total = sum(p.part.volume for p in pieces)
    lost = part.volume - total
    assert 0 < lost < 0.01 * part.volume


def test_chevron_pieces_are_each_relocated_to_their_own_local_origin():
    part = _box(400, 90)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0)
    for piece in pieces:
        bb = piece.part.bounding_box()
        assert bb.min.X == pytest.approx(0.0, abs=1e-6)
        assert bb.min.Y == pytest.approx(0.0, abs=1e-6)


def test_chevron_params_are_internally_consistent():
    # Pitch isn't an independent guess — it must fall out of angle and
    # amplitude via params.chevron_pitch_mm().
    expected_pitch = P.chevron_pitch_mm(P.SPLIT_JOINT_FEATURE_SIZE_MM,
                                         P.SPLIT_JOINT_ANGLE_DEG)
    assert P.SPLIT_JOINT_PITCH_MM == pytest.approx(expected_pitch)
    # And the feature size must fit inside the thinnest named 3mm skins
    # it was derived from, with room to spare on both sides.
    assert P.SPLIT_JOINT_FEATURE_SIZE_MM < P.DRAWER_BOX_FLOOR_THICKNESS_MM
    assert P.SPLIT_JOINT_FEATURE_SIZE_MM < P.CASE_TOP_BOTTOM_SKIN_MM
