"""
Drawer box generator.

Builds a plain rectangular, open-top drawer box shell (four walls +
floor) sized entirely from params/params.py. No fillets, no facer, no
side channels — this is the first-pass shape; those come later as
explicit decisions, not guesses.

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
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from build123d import Align, Box, Part, export_stl  # noqa: E402

from params import params as P  # noqa: E402


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


def drawer_box(size: str, depth_units: int, floors: int = 1) -> Part:
    """Build a drawer box Part.

    size: one of "S", "M", "L", "XL" (params.SIZES key)
    depth_units: grid depth units (params.DEPTH_MIN_UNITS..DEPTH_MAX_UNITS)
    floors: one of params.FLOOR_COUNTS_OFFERED
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

    return outer - inner


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
