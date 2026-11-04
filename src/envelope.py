"""
Print-bed envelope check.

Binnit targets params.PRINT_BED_USABLE_XY_MM as the real footprint limit
for a single printed part — not the raw bed size (params.PRINT_BED_XY_MM).
Parts larger than this are meant to be split on grid lines; that splitting
isn't implemented yet, so until a generator does it, producing an
oversized part is a hard failure here, not a warning — matching the brief:
"CI must fail any generated part that exceeds the envelope."

This only checks X/Y footprint, not Z. The brief gives a bed XY parameter
but no Z/gantry height limit, so Z is intentionally left unchecked rather
than guessed.
"""

from build123d import Part

from params import params as P


class EnvelopeError(RuntimeError):
    """Raised when a generated part's footprint exceeds the usable bed."""


def assert_fits_print_bed(part: Part, label: str = "part",
                           bed_xy_mm: float | None = None) -> None:
    bed_xy_mm = P.PRINT_BED_USABLE_XY_MM if bed_xy_mm is None else bed_xy_mm
    bb = part.bounding_box()
    x, y = bb.size.X, bb.size.Y
    if x > bed_xy_mm or y > bed_xy_mm:
        raise EnvelopeError(
            f"{label} footprint {x:.1f} x {y:.1f} mm exceeds the "
            f"{bed_xy_mm:.1f} mm usable print bed (PRINT_BED_USABLE_XY_MM) "
            "and is not yet split on grid lines."
        )
