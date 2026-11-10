"""
Case generator.

Builds the outer shell that a drawer box slides into, plus (by default)
the interlock rail/pad connectors at every bay boundary. Sized entirely
from params/params.py and src/interlock.py — no hardcoded dimensions.

Axis convention (matches src/drawer_box.py): X=width, Y=depth (0=back,
increasing toward the open front), Z=height.

What's modeled:
  - Side walls:  CASE_SIDE_TOTAL_MM on both left and right, plain
                 thickness — no slide-channel cutout. The brief gives
                 15 mm total "including slide channels" but no channel
                 width/depth/profile; v1 treats the 15 mm as solid wall
                 (decided when this generator was built, not guessed).
  - Back wall:   CASE_BACK_WALL_MM (an ASSUMPTION in params.py, not measured)
  - Top/bottom
    skins:       CASE_TOP_BOTTOM_SKIN_MM each
  - Front:       open (no wall) — the drawer box slides in here; a
                 separate facer piece (OPEN, not built) sits proud of it
  - Connectors:  a dovetail rail on top + a pad/groove on the bottom, at
                 every bay boundary (src/interlock.py), unless
                 include_connectors=False

What's NOT modeled: the slide-channel profile itself, the facer, and
the interlock end-of-travel detent — all explicitly OPEN or deferred,
not silently skipped.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from build123d import Align, Box, Part, export_stl  # noqa: E402

from params import params as P  # noqa: E402
from src import interlock  # noqa: E402


def _check_interior_width_consistency(size: str) -> float:
    """Case interior width (where the drawer box sits) is implied by
    the outer width minus both side walls. Cross-check it against the
    independently-stated drawer_box_outside_width_mm() rather than
    silently trusting either — same pattern as drawer_box.py's front
    wall check."""
    outside_width = P.SIZES[size].case_outside_width_mm
    implied_interior = outside_width - 2.0 * P.CASE_SIDE_TOTAL_MM
    expected = P.drawer_box_outside_width_mm(size)
    if abs(implied_interior - expected) > 1e-6:
        raise ValueError(
            f"Case interior width {implied_interior} mm (outside width - "
            f"2x side wall) != drawer_box_outside_width_mm({size!r}) "
            f"({expected} mm). Check params.py's width stack."
        )
    return implied_interior


def case(size: str, depth_units: int, floors: int = 1,
         include_connectors: bool = True) -> Part:
    """Build a case Part.

    size: one of "S", "M", "L", "XL" (params.SIZES key)
    depth_units: grid depth units (params.DEPTH_MIN_UNITS..DEPTH_MAX_UNITS)
    floors: one of params.FLOOR_COUNTS_OFFERED
    include_connectors: attach the interlock rail/pad at every bay
        boundary (default True). False gives a plain shell, useful for
        isolating shell dimensions from connector geometry in a test.
    """
    if size not in P.SIZES:
        raise ValueError(f"Unknown size {size!r}; expected one of {list(P.SIZES)}")
    if not (P.DEPTH_MIN_UNITS <= depth_units <= P.DEPTH_MAX_UNITS):
        raise ValueError(
            f"depth_units {depth_units} outside allowed range "
            f"[{P.DEPTH_MIN_UNITS}, {P.DEPTH_MAX_UNITS}]"
        )

    outside_width = P.SIZES[size].case_outside_width_mm
    bays = P.SIZES[size].bays
    interior_width = _check_interior_width_consistency(size)

    depth = P.case_depth_mm(depth_units)
    interior_cavity_depth = depth - P.CASE_BACK_WALL_MM  # open at the front

    cavity_height = P.case_interior_height_mm(floors)  # raises OpenParameterError /
    # ValueError via drawer_box_outside_height_mm() for unsupported floor counts

    skin = P.CASE_TOP_BOTTOM_SKIN_MM
    side_wall = P.CASE_SIDE_TOTAL_MM
    back_wall = P.CASE_BACK_WALL_MM

    z_shell_bottom = P.INTERLOCK_PAD_HEIGHT_MM if include_connectors else 0.0
    shell_height = 2.0 * skin + cavity_height
    z_shell_top = z_shell_bottom + shell_height

    outer = Box(outside_width, depth, shell_height,
                align=(Align.MIN, Align.MIN, Align.MIN))
    outer = outer.translate((0, 0, z_shell_bottom))

    cavity = Box(interior_width, interior_cavity_depth, cavity_height,
                 align=(Align.MIN, Align.MIN, Align.MIN))
    cavity = cavity.translate((side_wall, back_wall, z_shell_bottom + skin))

    result = outer - cavity

    if include_connectors:
        for x in interlock.connector_line_x_positions(bays):
            rail_copy = interlock.rail(depth).translate((x, 0, z_shell_top))
            pad_copy = interlock.pad_with_groove(depth).translate((x, 0, z_shell_bottom))
            result = result + rail_copy + pad_copy

    return result


def main() -> Path:
    size = "S"
    depth_units = P.SIZES[size].default_depth_units  # 3 for S
    floors = 1

    part = case(size, depth_units, floors=floors)

    out_dir = REPO_ROOT / "build"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"case_{size}_d{depth_units}_f{floors}.stl"
    export_stl(part, str(out_path))
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    main()
