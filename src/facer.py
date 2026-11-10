"""
Facer generator.

A plate attached to the drawer box's (already flush) front face,
projecting forward past the case's own front opening by its own
thickness — "a separate facer piece (latch and knob) sits proud of it"
per the brief. Carries a knob (pull handle) and a latch (a tactile
detent, not a lock — see below).

Axis convention: local y=0 is the facer's BACK face (the one against
the drawer box's front wall / level with the case's front opening);
y=FACER_THICKNESS_MM is the facer's own FRONT face. X matches the
drawer box's own width frame (0 at the drawer box's left edge), so the
plate's width lines up with drawer_box_outside_width_mm(size) without
any additional offset.

Z does NOT match the drawer box's height directly — see facer_height_mm()
below for why.

What's modeled:
  - Plate:  FACER_THICKNESS_MM thick (STATED decision: 3mm, reusing
            CASE_TOP_BOTTOM_SKIN_MM's value — not an independent guess),
            facer_height_mm(floors) tall (see below), spanning the
            drawer box's own outside width.
  - Knob:   a plain cylinder (STATED decision: 16mm diameter, 12mm
            projection — resolves the brief's OPEN KNOB_PROJECTION_MM),
            centered on the facer, projecting from its front face.
  - Latch:  a small spherical bump (STARTING, untested — same family as
            the interlock's end-of-travel detent, same honest caveat: a
            rigid CAD boolean can't model a snap-fit's elastic "push
            past it" give) centered on the facer's own top edge. It
            reaches up to case_interior_height_mm()'s own ceiling — see
            facer_height_mm() — and projects slightly past it into the
            underside of src/case.py's top skin, which cuts a matching
            notch at the same X/Y position. Not a security lock — a
            tactile detent so the drawer doesn't drift open in transit
            or when the unit is hung on a bar.

What's NOT modeled: nothing from the brief's facer description is left
out, but the whole feature (latch + knob shape, and all its dimensions)
was genuinely undecided until this generator resolved it — see
docs/DESIGN.md for the reasoning behind each choice.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from build123d import Align, Box, Cylinder, Part, Sphere, export_stl  # noqa: E402

from params import params as P  # noqa: E402


def facer_height_mm(floors: int) -> float:
    """FORMULA, not drawer_box_outside_height_mm(floors) directly: the
    facer spans the FULL interior cavity height
    (case_interior_height_mm()), not just the drawer box's own height.
    Those two differ by exactly GAP_ABOVE_CASE_BOTTOM_MM — the 1mm the
    drawer sits short of the cavity's own ceiling (case.py places the
    drawer flush at the cavity's bottom, so that gap lives above it).
    A facer sized to only the drawer's own height would leave a 1mm
    sliver of the case's dark interior visible above it at the front,
    and — the thing that actually forced this — its own top edge would
    sit 1mm below the cavity's ceiling, too short for a latch bump
    there to ever reach the underside it's supposed to catch on."""
    return P.case_interior_height_mm(floors)


def latch_bump_center(size: str, floors: int) -> tuple[float, float, float]:
    """Where the facer's latch bump sits, in the facer's own local
    frame — shared with src/case.py so the matching notch lands in the
    same place: (width/2, 0, facer_height_mm()), the facer's own
    back-top CORNER, not a point centered within its plate.

    Both coordinates being exactly at a boundary matters: the facer's
    entire volume sits at y>=0 (forward of the case's front opening,
    once attached) and the case's entire volume sits at y<=0 in this
    same frame (y=0 IS the opening plane) — a bump centered mid-plate
    (y>0) can never geometrically reach back across that boundary to
    touch anything on the case, regardless of its Z height. Centering
    it AT y=0 is what lets half the sphere dip into the case's own
    territory. z = facer_height_mm() matters for the same reason on
    the other axis: that height is exactly where the cavity's own
    ceiling (and the drawer's own top, 1mm lower) sit, so a bump there
    is clear of the drawer and reaches the skin's material at the same
    time it crosses y=0 — landing exactly on the skin's exposed
    front-bottom corner, not buried behind either part's own solid body
    where neither could ever touch it."""
    width = P.drawer_box_outside_width_mm(size)
    height = facer_height_mm(floors)
    return (width / 2.0, 0.0, height)


def facer(size: str, floors: int, with_latch: bool = True) -> Part:
    """Build a facer Part.

    size: one of "S", "M", "L", "XL" (params.SIZES key) — sets width
    floors: one of params.FLOOR_COUNTS_OFFERED — sets height, via
        facer_height_mm(), not drawer_box_outside_height_mm() directly
    with_latch: include the latch bump (default True)
    """
    if size not in P.SIZES:
        raise ValueError(f"Unknown size {size!r}; expected one of {list(P.SIZES)}")

    width = P.drawer_box_outside_width_mm(size)
    height = facer_height_mm(floors)  # raises for unsupported floor counts
    # via drawer_box_outside_height_mm() inside case_interior_height_mm()
    thickness = P.FACER_THICKNESS_MM

    plate = Box(width, thickness, height, align=(Align.MIN, Align.MIN, Align.MIN))

    knob = Cylinder(
        radius=P.KNOB_DIAMETER_MM / 2.0,
        height=P.KNOB_PROJECTION_MM,
        rotation=(-90, 0, 0),
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    knob = knob.translate((width / 2.0, thickness, height / 2.0))

    result = plate + knob

    if with_latch:
        x, y, z = latch_bump_center(size, floors)
        bump = Sphere(P.FACER_LATCH_BUMP_RADIUS_MM).translate((x, y, z))
        result = result + bump

    return result


def main() -> Path:
    size = "S"
    floors = 1

    part = facer(size, floors)

    out_dir = REPO_ROOT / "build"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"facer_{size}_f{floors}.stl"
    export_stl(part, str(out_path), tolerance=P.STL_EXPORT_TOLERANCE_MM,
               angular_tolerance=P.STL_EXPORT_ANGULAR_TOLERANCE)
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    main()
