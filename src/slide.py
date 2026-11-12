"""
Drawer slide mechanism: a 3-member telescoping slide, Binnit's own
design — not Vault's.

Three members, same general mechanical pattern used in ball-bearing-
free full-extension slides generally (wooden/plastic "Euro-style"
slides use this same principle; it's not anyone's proprietary design):
  - CASE   — contributes no added part at all. Its own already-open
             channel (src/case.py's _channel_open_cut, bounded top and
             bottom by its skins) directly serves as the outer
             capture — that pre-existing, already-paid-for geometry
             IS the outer channel, not a separate feature duplicating
             what's already there.
  - INTERMEDIATE RAIL — a free-floating plate: a tall, plain OUTER
             portion sized to fit (with clearance) inside the case's
             existing channel opening, and a built channel on its
             INNER face receiving the drawer's own rail. It's what
             makes full extension possible — without it, a 2-piece
             slide can only extend the drawer until its own rail nears
             the end of the case's own channel, well short of fully
             clear.
  - DRAWER RAIL — a flat tab protruding from the drawer box's own side
             wall (fixed), engaging the intermediate's inner channel.

WHY A CAPTURED CHANNEL, NOT A DOVETAIL (this module's first version
used the interlock connector's dovetail cross-section, by default,
without checking whether that shape fit this load case):
A dovetail's 45-degree taper resists being pulled apart ALONG the
insertion axis — a direction that essentially never gets loaded in
normal drawer use. What actually loads this joint is the drawer's
WEIGHT, acting vertically, which a plain captured channel (a flat tab
trapped between two flanges) resists exactly as completely, via simple
wall containment — no taper needed. Two further wins: a channel's
flanges are plain 90-degree walls (no overhang — a dovetail's wide end
sits right at the ~45-degree limit most FDM printers can bridge
without support), and insertion depth and capture width become
INDEPENDENT dimensions (the dovetail's fixed angle locked wide-end
spread to engagement height, so giving one interface more depth always
ballooned its footprint in lockstep; a channel has no such coupling).

WHY THE CASE GETS NO ADDED RAIL: once the dovetail was dropped, there
was no reason left to duplicate capture structure the case already
has. The case's open channel (full open height between its own skins)
already bounds the intermediate's outer portion in Z just by the
intermediate sitting inside it — building a smaller separate channel
feature there would just be spending material re-creating a function
the skins already provide for free.

WHY DEPTH FAVORS THE DRAWER SIDE: the two interfaces don't see equal
duty. The inner (drawer-side) channel does all the sliding work in
ordinary use (the whole stage-1 range); the outer (case-side) capture
only moves during stage 2 (full extension), which nothing currently
guarantees even happens reliably (no stop/catch tab — see below). The
joint used constantly is the one worth making harder to wear loose.

SIMPLIFICATIONS, not covered by the brief and not fully engineered here
(flagged rather than silently skipped, per this project's own rule):
- No explicit end-of-travel stop/catch tab forcing the handoff between
  stage 1 (drawer sliding on the intermediate) and stage 2 (intermediate
  sliding in the case's channel) — declined explicitly for this round.
  The lengths chosen make a working slide possible, but nothing
  GUARANTEES the intermediate starts moving at the mechanically ideal
  moment; in practice this relies on friction and/or the user's own
  care, not a hard mechanical trigger.
- No pull-out retention stop either (also declined) — the drawer can be
  pulled completely free of the case once fully extended.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from build123d import Align, Box, Part, Plane, export_stl  # noqa: E402

from params import params as P  # noqa: E402


def rail(length_mm: float, direction: int, depth_mm: float,
         width_mm: float | None = None) -> Part:
    """A flat rectangular tab (no taper — see module docstring for why
    a dovetail isn't needed here), protruding along X from local x=0
    (its base, where it attaches to a parent wall) running `length_mm`
    along +Y. `direction`: +1 or -1, which way it points. Used for the
    drawer's own rail only — the case contributes no rail at all."""
    width_mm = P.slide_tab_width_mm() if width_mm is None else width_mm
    tab = Box(depth_mm, length_mm, width_mm, align=(Align.MIN, Align.MIN, Align.CENTER))
    if direction < 0:
        tab = tab.mirror(Plane.YZ)  # flips +X to -X, verified directly (build123d's
        # own mirror() default is Plane.XY, which flips Z, not X — easy to get wrong)
    return tab


def intermediate_rail(length_mm: float, floors: int,
                       drawer_engagement_depth_mm: float | None = None,
                       channel_width_mm: float | None = None,
                       flange_thickness_mm: float | None = None,
                       clearance_mm: float | None = None) -> Part:
    """The floating intermediate rail.

    Local frame: x=0 is the OUTER face (sits inside the case's own
    channel, no feature of its own there); x=thickness is the INNER
    face, where a channel is cut to receive the drawer's rail (that
    rail's own reference point — see src/drawer_box.py — is x=thickness
    exactly, the same boundary, not a point centered on this plate).

    Z-height is uniform along the whole plate, sized by
    slide_intermediate_z_height_mm(floors) to fit the case's own
    channel opening with clearance — the OUTER portion relies entirely
    on that fit; only the INNER portion additionally gets a built
    channel (its own, smaller, flanged slot) for the drawer's rail.
    """
    drawer_engagement_depth_mm = (P.SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM
                                   if drawer_engagement_depth_mm is None
                                   else drawer_engagement_depth_mm)
    channel_width_mm = P.SLIDE_CHANNEL_WIDTH_MM if channel_width_mm is None else channel_width_mm
    flange_thickness_mm = (P.SLIDE_FLANGE_THICKNESS_MM if flange_thickness_mm is None
                            else flange_thickness_mm)
    clearance_mm = P.INTERLOCK_SLIDING_CLEARANCE_MM if clearance_mm is None else clearance_mm

    thickness = P.slide_intermediate_thickness_mm()
    z_height = P.slide_intermediate_z_height_mm(floors)

    plate = Box(thickness, length_mm, z_height, align=(Align.MIN, Align.MIN, Align.CENTER))

    # Inner channel: a rectangular slot cut into the plate's inner
    # portion, open at x=thickness (the drawer rail's own reference
    # face), reaching back by drawer_engagement_depth_mm. Enlarged by
    # clearance so the drawer's (nominal-width) rail actually fits.
    slot_width = channel_width_mm - 2.0 * flange_thickness_mm + 2.0 * clearance_mm
    slot = Box(drawer_engagement_depth_mm, length_mm, slot_width,
               align=(Align.MIN, Align.MIN, Align.CENTER))
    slot = slot.translate((thickness - drawer_engagement_depth_mm, 0, 0))

    return plate - slot


def main() -> Path:
    depth_units = 3  # S's default depth
    floors = 1
    length = P.slide_intermediate_length_mm(depth_units)

    part = intermediate_rail(length, floors)

    out_dir = REPO_ROOT / "build"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"slide_intermediate_d{depth_units}.stl"
    export_stl(part, str(out_path), tolerance=P.STL_EXPORT_TOLERANCE_MM,
               angular_tolerance=P.STL_EXPORT_ANGULAR_TOLERANCE)
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    main()
