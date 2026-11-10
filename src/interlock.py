"""
Interlock connector: the dovetail rail/pad that lets two cases stack
(top/bottom only, no side-by-side) and carry a hanging load.

Geometry, not yet covered elsewhere in the brief:
- The rail (top of a case) and the groove cut into the pad (bottom of
  the case above it) share the same dovetail cross-section — narrow at
  the base (where it meets the skin) and wider at the tip, per
  params.INTERLOCK_DOVETAIL_WIDTH_MM / dovetail_wide_width_mm(). The
  groove is the same shape, mirrored (wide at ITS opening too, deep
  into the pad) and enlarged by params.INTERLOCK_SLIDING_CLEARANCE_MM
  per side — a standard dovetail socket: shaped like the male feature,
  slightly oversized.
- No end-of-travel detent is built (params.INTERLOCK_END_OF_TRAVEL_DETENT
  is OPEN).

ASSUMPTION (not stated in the brief, needed to give the connector a
length): each rail/groove runs the full depth of the case, flush with
both the front and back faces. This is a deliberate choice, not a
derived fact — picked because it's front-referenced, which is what lets
a shallower case's connector still line up with a deeper case's (the
brief allows stacking "shallower on deeper" on the shared bay pitch):
both start flush at the front, so the shorter one is always fully
covered by the longer one's length, no partial-length matching needed.
If this turns out wrong once there's a real case to test it against,
it only affects where the connector sits along Y — not its cross-section.
"""

import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from build123d import Align, Box, Part, Polyline, extrude, make_face  # noqa: E402

from params import params as P  # noqa: E402


def _trapezoid_points_3d(width_at_0: float, width_at_h: float,
                          h: float) -> list[tuple[float, float, float]]:
    """3D cross-section points (lying in the XZ plane, y=0) for a
    trapezoid from z=0 (width_at_0) to z=h (width_at_h; h may be
    negative). Built directly on XZ (not the default XY) so
    extrude(..., dir=(0,1,0)) needs no rotation afterward — rotating a
    finished solid by a signed angle was a real bug here once (see git
    history): easy to get a sign backwards and end up with the rail
    pointing into the part instead of out of it."""
    half_0, half_h = width_at_0 / 2.0, width_at_h / 2.0
    return [(-half_0, 0.0, 0.0), (half_0, 0.0, 0.0),
            (half_h, 0.0, h), (-half_h, 0.0, h)]


def _dovetail_wide_width(root_width: float, height: float, angle_deg: float) -> float:
    return root_width + 2.0 * height * math.tan(math.radians(angle_deg))


def rail(length_mm: float, root_width_mm: float | None = None,
         height_mm: float | None = None, angle_deg: float | None = None) -> Part:
    """The male dovetail rail, protruding +Z from z=0 (the top skin's top
    face), centered on X=0, running `length_mm` along +Y."""
    root_width_mm = P.INTERLOCK_DOVETAIL_WIDTH_MM if root_width_mm is None else root_width_mm
    height_mm = P.INTERLOCK_RAIL_HEIGHT_MM if height_mm is None else height_mm
    angle_deg = P.INTERLOCK_DOVETAIL_ANGLE_DEG if angle_deg is None else angle_deg

    wide_mm = _dovetail_wide_width(root_width_mm, height_mm, angle_deg)
    pts = _trapezoid_points_3d(root_width_mm, wide_mm, height_mm)
    face = make_face(Polyline(*pts, close=True))
    return extrude(face, amount=length_mm, dir=(0, 1, 0))


def pad_with_groove(length_mm: float, pad_width_mm: float | None = None,
                     root_width_mm: float | None = None,
                     height_mm: float | None = None,
                     angle_deg: float | None = None,
                     clearance_mm: float | None = None) -> Part:
    """The female pad + groove, hanging -Z from z=0 (the bottom skin's
    bottom face) down to z=-height_mm, centered on X=0, running
    `length_mm` along +Y. `pad_width_mm` is the pad block's own lateral
    width (defaults to the full INTERLOCK_SIDE_ZONE_MM).

    Orientation matters here: this is a flush-skin assembly (the two
    cases' skins touch directly; the connector doesn't add any extra
    separation — "in addition to the 3 mm skin" describes each case's
    own height budget, not extra gap between cases). For the rail's
    wide TIP (away from the lower case's skin) to land inside the
    groove's widest point, the groove must be WIDE at z=0 (right at
    this pad's own attachment to the skin above it) and narrow at its
    tip (z=-height_mm) — the opposite taper direction from the rail
    itself, not a mirror of it. Getting this backwards (as a first
    draft of this function did) makes the groove's opening narrower
    than the rail at every height except the very base, so nothing
    fits — caught by the fit test in tests/test_interlock.py.
    """
    pad_width_mm = P.INTERLOCK_SIDE_ZONE_MM if pad_width_mm is None else pad_width_mm
    root_width_mm = P.INTERLOCK_DOVETAIL_WIDTH_MM if root_width_mm is None else root_width_mm
    height_mm = P.INTERLOCK_RAIL_HEIGHT_MM if height_mm is None else height_mm
    angle_deg = P.INTERLOCK_DOVETAIL_ANGLE_DEG if angle_deg is None else angle_deg
    clearance_mm = P.INTERLOCK_SLIDING_CLEARANCE_MM if clearance_mm is None else clearance_mm

    pad_block = Box(pad_width_mm, length_mm, height_mm,
                     align=(Align.CENTER, Align.MIN, Align.MIN))
    pad_block = pad_block.translate((0, 0, -height_mm))

    groove_root_mm = root_width_mm + 2.0 * clearance_mm     # narrow end, at the tip
    groove_wide_mm = (_dovetail_wide_width(root_width_mm, height_mm, angle_deg)
                       + 2.0 * clearance_mm)                 # wide end, at the skin
    pts = _trapezoid_points_3d(groove_wide_mm, groove_root_mm, -height_mm)
    face = make_face(Polyline(*pts, close=True))
    groove = extrude(face, amount=length_mm, dir=(0, 1, 0))
    # Widen the cut's open end slightly past z=-height so the boolean
    # subtraction fully clears the pad's tip face rather than leaving a
    # razor-thin membrane from float rounding.
    overcut = Box(groove_root_mm + 4.0 * clearance_mm, length_mm, 0.5,
                  align=(Align.CENTER, Align.MIN, Align.MIN))
    overcut = overcut.translate((0, 0, -height_mm - 0.5))
    groove = groove + overcut

    return pad_block - groove


def connector_line_x_positions(bays: int, bay_pitch_mm: float | None = None,
                                side_zone_mm: float | None = None) -> list[float]:
    """STATED rule: n+1 connector lines for n bays, one at every bay
    boundary (including the center line(s) over the case skin). Returns
    the X position of each connector's *center*, from the case's left
    edge (0) to its right edge (bays * bay_pitch_mm == the case's own
    outside width — see validate_width_addition_rule()'s premise).

    DERIVED ADJUSTMENT (not a bare transcription of the brief): the two
    end lines are inset by half of side_zone_mm. A raw bay-boundary
    position (0 and bays*bay_pitch_mm) is exactly on the case's outer
    edge — centering a 15 mm-wide connector there would put half its
    footprint outside the shell entirely. Interior lines need no
    adjustment: they land on the continuous top/bottom skin, which
    spans the case's full width, not just the space between side walls.
    This reuses INTERLOCK_SIDE_ZONE_MM (not a new number) precisely
    because that figure already equals CASE_SIDE_TOTAL_MM — the same
    15 mm side wall, described twice in the brief for two different
    features that turn out to occupy the same physical material.
    """
    bay_pitch_mm = P.BAY_PITCH_MM if bay_pitch_mm is None else bay_pitch_mm
    side_zone_mm = P.INTERLOCK_SIDE_ZONE_MM if side_zone_mm is None else side_zone_mm
    assert bays + 1 == P.interlock_connector_line_count(bays)

    positions = [i * bay_pitch_mm for i in range(bays + 1)]
    inset = side_zone_mm / 2.0
    positions[0] = inset
    positions[-1] = positions[-1] - inset
    return positions
