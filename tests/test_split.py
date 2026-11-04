"""Tests for splitting oversized parts to fit the print bed (src/split.py).

grid_pitch_mm is a required argument everywhere here, passed explicitly
in each test — which grid Binnit should actually use (42mm internal vs
164mm bay pitch) is still OPEN (params.SPLIT_GRID_PITCH_MM); these tests
validate the splitting mechanism itself, not that open decision.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from build123d import Align, Box  # noqa: E402

from params import params as P  # noqa: E402
from params.params import OpenParameterError  # noqa: E402
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


def test_omitting_grid_pitch_raises_open_parameter_error():
    # The caller must supply a real grid_pitch_mm; passing the module's
    # own OPEN sentinel (what you'd get by not deciding) must fail loudly
    # with the OPEN-parameter error, not a generic TypeError/ValueError.
    part = _box(400, 300)
    with pytest.raises(OpenParameterError):
        split_to_fit(part, grid_pitch_mm=P.SPLIT_GRID_PITCH_MM)
