"""Tests for splitting oversized parts to fit the print bed (src/split.py).

Most tests below pass grid_pitch_mm explicitly (164.0) to exercise the
splitting mechanism generically, independent of which pitch the project
actually uses. The *actual* decision — 42 mm internal grid, not the
164 mm bay pitch, because a small bed (Voron Zero: 120x120mm) can't fit
even one bay pitch in a single piece — is covered by
test_default_grid_pitch_is_the_internal_42mm_grid and
test_voron_zero_sized_bed_can_still_split_on_the_internal_grid below.
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


def test_part_that_already_fits_is_not_split():
    part = _box(100, 100)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0)
    assert len(pieces) == 1
    assert pieces[0].grid_index == (0, 0)
    assert pieces[0].part.volume == pytest.approx(part.volume)


def test_oversized_part_is_split_into_bed_sized_pieces():
    part = _box(400, 300)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0)

    assert len(pieces) == 4  # 2 cuts in X (400mm -> 164/236), 1 in Y (300mm -> 164/136)
    for piece in pieces:
        bb = piece.part.bounding_box()
        assert bb.size.X <= 250.0 + 1e-6
        assert bb.size.Y <= 250.0 + 1e-6


def test_split_pieces_conserve_total_volume():
    part = _box(400, 300)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0)
    assert sum(p.part.volume for p in pieces) == pytest.approx(part.volume, rel=1e-6)


def test_split_pieces_are_each_relocated_to_their_own_local_origin():
    part = _box(400, 300)
    pieces = split_to_fit(part, grid_pitch_mm=164.0, bed_xy_mm=250.0)
    for piece in pieces:
        bb = piece.part.bounding_box()
        assert bb.min.X == pytest.approx(0.0, abs=1e-6)
        assert bb.min.Y == pytest.approx(0.0, abs=1e-6)


def test_grid_too_coarse_raises_split_error():
    part = _box(1000, 10)
    with pytest.raises(SplitError):
        split_to_fit(part, grid_pitch_mm=500.0, bed_xy_mm=250.0)


def test_default_grid_pitch_is_the_internal_42mm_grid():
    assert P.SPLIT_GRID_PITCH_MM == P.GRID_PITCH_MM == 42.0

    part = _box(400, 300)
    default_pieces = split_to_fit(part, bed_xy_mm=250.0)
    explicit_pieces = split_to_fit(part, grid_pitch_mm=42.0, bed_xy_mm=250.0)
    assert len(default_pieces) == len(explicit_pieces)


def test_voron_zero_sized_bed_can_still_split_on_the_internal_grid():
    # The decision to use the 42mm internal grid rather than the 164mm bay
    # pitch was made specifically because a small bed can't fit one whole
    # bay pitch in a single piece. Prove that out: take a part the size of
    # one S-case bay (164mm wide) and confirm it splits to fit a Voron
    # Zero's 120x120mm bed using the (default) internal grid.
    bay_width_part = _box(P.BAY_PITCH_MM, 100.0)
    voron_zero_bed_xy = 120.0

    pieces = split_to_fit(bay_width_part, bed_xy_mm=voron_zero_bed_xy)

    assert len(pieces) > 1  # one 164mm-wide bay does not fit a 120mm bed
    for piece in pieces:
        bb = piece.part.bounding_box()
        assert bb.size.X <= voron_zero_bed_xy + 1e-6
        assert bb.size.Y <= voron_zero_bed_xy + 1e-6

    # And the bay pitch itself would be useless as the split grid here:
    # the very first grid line (164mm) already exceeds the bed.
    with pytest.raises(SplitError):
        split_to_fit(bay_width_part, grid_pitch_mm=P.BAY_PITCH_MM,
                     bed_xy_mm=voron_zero_bed_xy)
