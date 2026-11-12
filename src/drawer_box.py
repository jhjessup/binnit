"""
Drawer box generator.

Builds a plain rectangular, open-top drawer box shell (four walls +
floor) sized entirely from params/params.py, plus (by default) each
side's fixed slide rail — the drawer's own half of the 3-member
telescoping slide mechanism (src/slide.py; see that module's docstring
for the mechanism and the case's own half, src/case.py). No fillets,
no facer — those are separate decisions/parts.

Wall layout (asymmetric, per params.py):
  - side walls:  DRAWER_BOX_SIDE_WALL_MM on both the left and right
  - back wall:   DRAWER_BOX_BACK_WALL_MM
  - front wall:  DRAWER_BOX_FRONT_WALL_MM (derived — see below)
  - floor:       DRAWER_BOX_FLOOR_THICKNESS_MM
  - top:         open (no wall)

The front wall is not an independent input here: it falls out of
outside_depth - interior_depth - back_wall, and params.py's own
DRAWER_BOX_FRONT_WALL_MM is kept only as a reference figure to check
against (see `_check_front_wall_consistency`).

Slide rail placement: each rail protrudes from the drawer's own
existing side wall OUTER FACE (local x=0 for the left side, x=
outside_width for the right) — those faces are exactly where the case's
channel expects to find them once the drawer is placed (case.py
translates the drawer by CASE_SIDE_TOTAL_MM in X with no further
offset), so no extra positioning math is needed here beyond picking
which direction each rail points.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from build123d import Align, Box, Part, export_stl  # noqa: E402

from params import params as P  # noqa: E402
from src import slide  # noqa: E402


def _check_front_wall_consistency(outside_depth: float, interior_depth: float,
                                   back_wall: float) -> float:
    """The front wall thickness is implied by the other depth-stack
    numbers. Compute it and sanity-check it against the MEASURED
    reference value in params.py rather than silently trusting either."""
    implied_front_wall = outside_depth - interior_depth - back_wall
    if abs(implied_front_wall - P.DRAWER_BOX_FRONT_WALL_MM) > 1e-6:
        raise ValueError(
            "Depth stack is inconsistent: implied front wall "
            f"{implied_front_wall} mm != DRAWER_BOX_FRONT_WALL_MM "
            f"({P.DRAWER_BOX_FRONT_WALL_MM} mm). Check params.py."
        )
    return implied_front_wall


def drawer_box(size: str, depth_units: int, floors: int = 1,
               include_slide_rails: bool = True) -> Part:
    """Build a drawer box Part.

    size: one of "S", "M", "L", "XL" (params.SIZES key)
    depth_units: grid depth units (params.DEPTH_MIN_UNITS..DEPTH_MAX_UNITS)
    floors: one of params.FLOOR_COUNTS_OFFERED
    include_slide_rails: attach each side's fixed slide rail
        (src/slide.py), default True. False gives the plain shell,
        useful for isolating other dimensions in a test.
    """
    if size not in P.SIZES:
        raise ValueError(f"Unknown size {size!r}; expected one of {list(P.SIZES)}")
    if not (P.DEPTH_MIN_UNITS <= depth_units <= P.DEPTH_MAX_UNITS):
        raise ValueError(
            f"depth_units {depth_units} outside allowed range "
            f"[{P.DEPTH_MIN_UNITS}, {P.DEPTH_MAX_UNITS}]"
        )

    outside_width = P.drawer_box_outside_width_mm(size)
    interior_width = P.drawer_box_interior_width_mm(size)
    outside_depth = P.drawer_box_outside_depth_mm(depth_units)
    interior_depth = P.drawer_box_interior_depth_mm(depth_units)
    outside_height = P.drawer_box_outside_height_mm(floors)  # raises for
    # floor counts not in FLOOR_COUNTS_OFFERED

    floor = P.DRAWER_BOX_FLOOR_THICKNESS_MM
    side_wall = P.DRAWER_BOX_SIDE_WALL_MM
    back_wall = P.DRAWER_BOX_BACK_WALL_MM
    _check_front_wall_consistency(outside_depth, interior_depth, back_wall)

    interior_height = outside_height - floor  # open top: no top wall to deduct

    outer = Box(outside_width, outside_depth, outside_height,
                align=(Align.MIN, Align.MIN, Align.MIN))
    inner = Box(interior_width, interior_depth, interior_height,
                align=(Align.MIN, Align.MIN, Align.MIN))
    inner = inner.translate((side_wall, back_wall, floor))

    result = outer - inner

    if include_slide_rails:
        rail_length = P.SLIDE_DRAWER_RAIL_LENGTH_MM
        y_center = (outside_depth - rail_length) / 2.0
        # z center matches the case's own cavity-based rail centering
        # exactly: case.py centers its rail at cavity_z0 + cavity_height/2
        # in case-global Z, and the drawer is placed with its own local
        # z=0 AT cavity_z0 (flush at the cavity's bottom) — so the same
        # center, expressed in the drawer's own local frame, is simply
        # case_interior_height_mm(floors) / 2, with no cavity_z0 offset
        # needed at all.
        z_center = P.case_interior_height_mm(floors) / 2.0

        engagement_depth = P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM
        left_rail = slide.rail(rail_length, direction=-1, depth_mm=engagement_depth)
        left_rail = left_rail.translate((0, y_center, z_center))
        right_rail = slide.rail(rail_length, direction=+1, depth_mm=engagement_depth)
        right_rail = right_rail.translate((outside_width, y_center, z_center))
        result = result + left_rail + right_rail

    return result


def main() -> Path:
    size = "S"
    depth_units = P.SIZES[size].default_depth_units  # 3 for S; a plain int,
    # not OPEN, so this works today — L/XL defaults would raise here.
    floors = 1

    part = drawer_box(size, depth_units, floors=floors)

    out_dir = REPO_ROOT / "build"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"drawer_box_{size}_d{depth_units}_f{floors}.stl"
    export_stl(part, str(out_path), tolerance=P.STL_EXPORT_TOLERANCE_MM,
               angular_tolerance=P.STL_EXPORT_ANGULAR_TOLERANCE)
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    main()
