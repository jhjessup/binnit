"""Envelope checks: generated parts must fit the usable print bed (X/Y).

Per the design brief, this must be a hard CI failure, not a warning, for
any part generated today (grid-line splitting for oversized parts is not
implemented yet).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from src.drawer_box import drawer_box  # noqa: E402
from src.envelope import EnvelopeError, assert_fits_print_bed  # noqa: E402


def test_s_drawer_box_fits_print_bed():
    part = drawer_box("S", 3, floors=1)
    assert_fits_print_bed(part, label="S drawer box, depth 3, 1 floor")


def test_envelope_check_actually_fails_on_oversized_part():
    # A deliberately oversized S-shaped box (double outside width) must be
    # rejected, so this test also guards against the check being a no-op.
    part = drawer_box("S", 3, floors=1)
    with pytest.raises(EnvelopeError):
        assert_fits_print_bed(part, label="oversized test part", bed_xy_mm=1.0)
