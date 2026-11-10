"""
Case generator.

Builds the outer shell that a drawer box slides into, plus (by default)
the interlock rail/pad connectors at every bay boundary. Sized entirely
from params/params.py and src/interlock.py — no hardcoded dimensions.

Axis convention (matches src/drawer_box.py): X=width, Y=depth (0=back,
increasing toward the open front), Z=height.

What's modeled:
  - Side walls:  CASE_SIDE_TOTAL_MM on both left and right, with a
                 blind slide-channel pocket cut into each OUTER face
                 (CASE_SIDE_OUTER_WALL_MM stays solid outside it,
                 CASE_SIDE_CHANNEL_DEPTH_MM is removed, and
                 case_side_inner_wall_mm() stays solid facing the
                 cavity). It's a relief/weight feature, not a mating
                 rail — the drawer box has no matching feature and
                 src/drawer_box.py is unchanged. The brief gives the
                 15 mm total and the 3 mm outer wall but no channel
                 depth or profile, so this split is a decision made
                 when this generator was built, not a transcribed fact
                 (see params.py's CASE_SIDE_CHANNEL_* comment).
  - Back wall:   CASE_BACK_WALL_MM (an ASSUMPTION in params.py, not measured)
  - Top/bottom
    skins:       CASE_TOP_BOTTOM_SKIN_MM each
  - Front:       open (no wall) — the drawer box slides in here; a
                 separate facer piece (OPEN, not built) sits proud of it
  - Connectors:  a dovetail rail on top + a pad/groove on the bottom, at
                 every bay boundary (src/interlock.py), each with an
                 end-of-travel detent, unless include_connectors=False

What's NOT modeled: the facer. The slide-channel profile and the
interlock detent are now built (see above and src/interlock.py) —
both were genuinely undecided until this generator resolved them.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from build123d import Align, Box, Part, Sphere, export_stl  # noqa: E402

from params import params as P  # noqa: E402
from src import facer, interlock  # noqa: E402


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


def _side_channel_cut(outside_width: float, depth: float, z_bottom: float,
                       z_top: float, left_side: bool) -> Box:
    """One side's slide-channel pocket: a blind cut into the OUTER face,
    inset by CASE_SIDE_OUTER_WALL_MM (left solid) and
    CASE_SIDE_CHANNEL_DEPTH_MM deep, stopping short of the cavity (left
    solid via case_side_inner_wall_mm() — validated > 0 at params.py
    import time). Inset from the case's own front/back and top/bottom
    by the Y/Z margins so it doesn't breach any opening."""
    outer_wall = P.CASE_SIDE_OUTER_WALL_MM
    channel_depth = P.CASE_SIDE_CHANNEL_DEPTH_MM
    y0 = P.CASE_SIDE_CHANNEL_Y_MARGIN_MM
    y1 = depth - P.CASE_SIDE_CHANNEL_Y_MARGIN_MM
    z0 = z_bottom + P.CASE_SIDE_CHANNEL_Z_MARGIN_MM
    z1 = z_top - P.CASE_SIDE_CHANNEL_Z_MARGIN_MM

    x0 = outer_wall if left_side else outside_width - outer_wall - channel_depth
    pocket = Box(channel_depth, y1 - y0, z1 - z0, align=(Align.MIN, Align.MIN, Align.MIN))
    return pocket.translate((x0, y0, z0))


def _latch_notch_cut(size: str, floors: int, side_wall: float,
                      depth: float, z_shell_bottom: float, skin: float) -> Sphere:
    """A small spherical notch cut into the top skin's front-bottom
    corner, matching src/facer.py's latch bump position exactly (see
    that module's latch_bump_center() for why both coordinates have to
    be exactly at a boundary — same reasoning applies on the case side:
    this notch has to reach forward to y=depth, the front opening
    plane, and down to z=cavity top, or it can never coincide with a
    bump that's only ever on the facer's own side of both boundaries).
    Enlarged by the same sliding clearance the interlock detent reuses,
    rather than inventing a second clearance value."""
    width = P.drawer_box_outside_width_mm(size)
    x = side_wall + width / 2.0
    z = z_shell_bottom + skin + facer.facer_height_mm(floors)
    radius = P.FACER_LATCH_BUMP_RADIUS_MM + P.INTERLOCK_SLIDING_CLEARANCE_MM
    return Sphere(radius).translate((x, depth, z))


def case(size: str, depth_units: int, floors: int = 1,
         include_connectors: bool = True, include_side_channels: bool = True,
         include_latch_notch: bool = True) -> Part:
    """Build a case Part.

    size: one of "S", "M", "L", "XL" (params.SIZES key)
    depth_units: grid depth units (params.DEPTH_MIN_UNITS..DEPTH_MAX_UNITS)
    floors: one of params.FLOOR_COUNTS_OFFERED
    include_connectors: attach the interlock rail/pad at every bay
        boundary (default True). False gives a plain shell, useful for
        isolating shell dimensions from connector geometry in a test.
    include_side_channels: cut the slide-channel pocket into each side
        wall's outer face (default True). False gives a plain solid
        side wall, useful for isolating other dimensions in a test.
    include_latch_notch: cut the facer's matching latch notch into the
        top skin's front corner (default True).
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
    back_wall = P.CASE_BACK_WALL_MM
    back_gap = P.GAP_DRAWER_BACK_TO_CASE_BACK_MM
    # The 1mm gap belongs BEHIND the drawer (between its back wall and the
    # case's), not in front — the brief states the drawer sits flush with
    # the case's front opening. Cavity starts after both the case's own
    # back wall AND that gap, and (checked below) its depth works out to
    # exactly drawer_box_outside_depth_mm(depth_units): back_wall + gap +
    # drawer_outside_depth == case_depth_mm(depth_units) exactly, so the
    # drawer's front face lands precisely at y=depth, flush, with nothing
    # left over. An earlier version of this function started the cavity
    # at y=back_wall alone (no gap), which put the 1mm slack at the FRONT
    # instead — wrong, and only caught when working out the facer's own
    # placement needed the front face position to actually be exact.
    cavity_y0 = back_wall + back_gap
    interior_cavity_depth = depth - cavity_y0
    if abs(interior_cavity_depth - P.drawer_box_outside_depth_mm(depth_units)) > 1e-6:
        raise ValueError(
            f"Case interior cavity depth {interior_cavity_depth} mm != "
            f"drawer_box_outside_depth_mm({depth_units}) "
            f"({P.drawer_box_outside_depth_mm(depth_units)} mm). "
            "Check params.py's depth stack."
        )

    cavity_height = P.case_interior_height_mm(floors)  # raises OpenParameterError /
    # ValueError via drawer_box_outside_height_mm() for unsupported floor counts

    skin = P.CASE_TOP_BOTTOM_SKIN_MM
    side_wall = P.CASE_SIDE_TOTAL_MM

    z_shell_bottom = P.INTERLOCK_PAD_HEIGHT_MM if include_connectors else 0.0
    shell_height = 2.0 * skin + cavity_height
    z_shell_top = z_shell_bottom + shell_height

    outer = Box(outside_width, depth, shell_height,
                align=(Align.MIN, Align.MIN, Align.MIN))
    outer = outer.translate((0, 0, z_shell_bottom))

    cavity = Box(interior_width, interior_cavity_depth, cavity_height,
                 align=(Align.MIN, Align.MIN, Align.MIN))
    cavity = cavity.translate((side_wall, cavity_y0, z_shell_bottom + skin))

    result = outer - cavity

    if include_side_channels:
        left_channel = _side_channel_cut(outside_width, depth, z_shell_bottom,
                                          z_shell_top, left_side=True)
        right_channel = _side_channel_cut(outside_width, depth, z_shell_bottom,
                                           z_shell_top, left_side=False)
        result = result - left_channel - right_channel

    if include_connectors:
        for x in interlock.connector_line_x_positions(bays):
            rail_copy = interlock.rail(depth).translate((x, 0, z_shell_top))
            pad_copy = interlock.pad_with_groove(depth).translate((x, 0, z_shell_bottom))
            result = result + rail_copy + pad_copy

    if include_latch_notch:
        notch = _latch_notch_cut(size, floors, side_wall, depth, z_shell_bottom, skin)
        result = result - notch

    return result


def main() -> Path:
    size = "S"
    depth_units = P.SIZES[size].default_depth_units  # 3 for S
    floors = 1

    part = case(size, depth_units, floors=floors)

    out_dir = REPO_ROOT / "build"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"case_{size}_d{depth_units}_f{floors}.stl"
    export_stl(part, str(out_path), tolerance=P.STL_EXPORT_TOLERANCE_MM,
               angular_tolerance=P.STL_EXPORT_ANGULAR_TOLERANCE)
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    main()
