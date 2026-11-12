"""
Drawer slide mechanism: a 3-member telescoping slide, Binnit's own
design — not Vault's.

Three members, same general mechanical pattern used in ball-bearing-
free full-extension slides generally (wooden/plastic "Euro-style"
slides use this same principle; it's not anyone's proprietary design):
  - CASE RAIL   — a dovetail rail protruding from the case's own side
                  wall (fixed).
  - INTERMEDIATE RAIL — a free-floating plate with a dovetail GROOVE
                  on each face: one receives the case rail, the other
                  receives the drawer rail. It's what makes full
                  extension possible — without it, a 2-piece slide can
                  only extend the drawer until its own rail nears the
                  end of the case's groove, well short of fully clear.
  - DRAWER RAIL — a dovetail rail protruding from the drawer box's own
                  side wall (fixed), engaging the intermediate's inner
                  groove.

Both dovetail interfaces reuse INTERLOCK_DOVETAIL_ANGLE_DEG and
INTERLOCK_SLIDING_CLEARANCE_MM from params.py — same kind of captured
sliding joint as the interlock connector, not a new, separately-tuned
one.

Getting the groove/rail orientation right took a wrong turn worth
recording: a groove's cross-section must match its rail's cross-section
at every point along the shared axis (same taper direction, uniformly
enlarged by clearance) — NOT be positioned relative to the receiving
part's own face. The intermediate rail's plate spans the full channel
budget (case rail's reference face to drawer rail's reference face);
each groove is cut using the SAME reference point as its mating rail,
even though that reference sits right at — or in the drawer rail's
case, exactly at — the plate's own boundary. Verified directly: rail
and groove show zero overlap when aligned, real interference when
either is shifted.

SIMPLIFICATIONS, not covered by the brief and not fully engineered here
(flagged rather than silently skipped, per this project's own rule):
- No explicit end-of-travel stop/catch tab forcing the handoff between
  stage 1 (drawer sliding on the intermediate) and stage 2 (intermediate
  sliding on the case) — declined explicitly for this round. The lengths
  chosen (case rail > intermediate > drawer rail) make a working slide
  possible, but nothing GUARANTEES the intermediate starts moving at
  the mechanically ideal moment; in practice this relies on friction
  and/or the user's own care, not a hard mechanical trigger.
- No pull-out retention stop either (also declined) — the drawer can be
  pulled completely free of the case once fully extended.
"""

import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from build123d import Align, Box, Part, Polyline, export_stl, extrude, make_face  # noqa: E402

from params import params as P  # noqa: E402


def _dovetail_wide(root_width: float, height: float, angle_deg: float) -> float:
    return root_width + 2.0 * height * math.tan(math.radians(angle_deg))


def _rail_points(root_width: float, height: float, angle_deg: float,
                  direction: int) -> list[tuple[float, float, float]]:
    """3D cross-section points (XZ plane, y=0) for a dovetail rail:
    narrow (root_width) at local x=0, wide at local x=direction*height.
    direction=+1 points into +X (protrudes rightward from its own base);
    direction=-1 points into -X. Taper is along X here, width along Z —
    swapped from src/interlock.py's own Z-taper/X-width convention,
    since this mechanism's sliding axis (Y) and engagement axis (X,
    across the case's side wall) are different from the interlock
    connector's stacking axis (Z)."""
    wide = _dovetail_wide(root_width, height, angle_deg)
    half_root, half_wide = root_width / 2.0, wide / 2.0
    h = direction * height
    return [(0.0, 0.0, -half_root), (0.0, 0.0, half_root),
            (h, 0.0, half_wide), (h, 0.0, -half_wide)]


def rail(length_mm: float, direction: int, root_width_mm: float | None = None,
         height_mm: float | None = None, angle_deg: float | None = None) -> Part:
    """A single dovetail rail, protruding along X from local x=0 (its
    base, where it would attach to a case or drawer wall) running
    `length_mm` along +Y. `direction`: +1 or -1, which way it points."""
    root_width_mm = P.SLIDE_RAIL_ROOT_WIDTH_MM if root_width_mm is None else root_width_mm
    height_mm = P.SLIDE_RAIL_HEIGHT_MM if height_mm is None else height_mm
    angle_deg = P.INTERLOCK_DOVETAIL_ANGLE_DEG if angle_deg is None else angle_deg

    pts = _rail_points(root_width_mm, height_mm, angle_deg, direction)
    face = make_face(Polyline(*pts, close=True))
    return extrude(face, amount=length_mm, dir=(0, 1, 0))


def _groove_cut(length_mm: float, direction: int, root_width_mm: float,
                 height_mm: float, angle_deg: float, clearance_mm: float) -> Part:
    """The cutting tool for a groove matching rail(), enlarged uniformly
    by clearance_mm, same reference point and taper direction as the
    rail it receives — not mirrored, not repositioned."""
    enlarged_root = root_width_mm + 2.0 * clearance_mm
    pts = _rail_points(enlarged_root, height_mm, angle_deg, direction)
    face = make_face(Polyline(*pts, close=True))
    return extrude(face, amount=length_mm, dir=(0, 1, 0))


def intermediate_rail(length_mm: float, outer_root_width_mm: float | None = None,
                       outer_height_mm: float | None = None,
                       inner_root_width_mm: float | None = None,
                       inner_height_mm: float | None = None,
                       angle_deg: float | None = None,
                       clearance_mm: float | None = None,
                       z_width_mm: float | None = None) -> Part:
    """The floating intermediate rail: a flat plate spanning the full
    channel budget (slide_intermediate_thickness_mm()), with a groove
    cut into each face — outer face (local x=0, receives the case rail)
    and inner face (local x=thickness, receives the drawer rail).
    Both grooves use the SAME reference point as their mating rail
    (x=0 for the case side, x=thickness for the drawer side), not a
    point centered on the plate itself."""
    outer_root_width_mm = (P.SLIDE_RAIL_ROOT_WIDTH_MM if outer_root_width_mm is None
                            else outer_root_width_mm)
    outer_height_mm = P.SLIDE_RAIL_HEIGHT_MM if outer_height_mm is None else outer_height_mm
    inner_root_width_mm = (P.SLIDE_RAIL_ROOT_WIDTH_MM if inner_root_width_mm is None
                            else inner_root_width_mm)
    inner_height_mm = P.SLIDE_RAIL_HEIGHT_MM if inner_height_mm is None else inner_height_mm
    angle_deg = P.INTERLOCK_DOVETAIL_ANGLE_DEG if angle_deg is None else angle_deg
    clearance_mm = P.INTERLOCK_SLIDING_CLEARANCE_MM if clearance_mm is None else clearance_mm
    thickness = P.slide_intermediate_thickness_mm()
    if z_width_mm is None:
        # Must clear the WIDE end of whichever groove is larger — a
        # fixed "root + constant" margin broke silently once root/height
        # changed independently (the wide end can exceed root+6 well
        # before root itself gets anywhere close to that), clipping the
        # groove's cut and leaving an invalid, not-fully-enlarged cavity.
        outer_wide = _dovetail_wide(outer_root_width_mm, outer_height_mm, angle_deg)
        inner_wide = _dovetail_wide(inner_root_width_mm, inner_height_mm, angle_deg)
        z_width_mm = max(outer_wide, inner_wide) + 4.0

    plate = Box(thickness, length_mm, z_width_mm,
                align=(Align.MIN, Align.MIN, Align.CENTER))

    outer_groove = _groove_cut(length_mm, +1, outer_root_width_mm, outer_height_mm,
                                angle_deg, clearance_mm)
    inner_groove = _groove_cut(length_mm, -1, inner_root_width_mm, inner_height_mm,
                                angle_deg, clearance_mm)
    inner_groove = inner_groove.translate((thickness, 0, 0))

    return plate - outer_groove - inner_groove


def main() -> Path:
    depth_units = 3  # S's default depth
    length = P.slide_intermediate_length_mm(depth_units)

    part = intermediate_rail(length)

    out_dir = REPO_ROOT / "build"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"slide_intermediate_d{depth_units}.stl"
    export_stl(part, str(out_path), tolerance=P.STL_EXPORT_TOLERANCE_MM,
               angular_tolerance=P.STL_EXPORT_ANGULAR_TOLERANCE)
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    main()
