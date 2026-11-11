"""
Binnit — single source of truth for all dimensions.

Every number a generator, test, or doc needs comes from here. Nothing in
/src or /tests should hardcode a dimension that belongs in this file.

Provenance tags used in the comments below (so a reviewer can see at a
glance how solid a number is, without re-reading the design brief):

  STATED       — given directly and exactly in the design brief.
  MEASURED     — taken from a measured reference unit (a Vault L4), used
                 only as a width-stack *reference*. Binnit's own geometry
                 is written independently to its own numbers below, never
                 copied or derived from Vault/Gridfinity files.
  ASSUMPTION   — explicitly flagged as a guess in the design brief. Usable
                 as a working default, but not verified.
  INFERRED     — estimated rather than measured; same caveat as ASSUMPTION.
  STARTING     — a deliberately provisional value (e.g. a clearance) meant
                 to be tuned by printing and testing, not trusted as final.
  FORMULA      — computed from other named parameters here; never a bare
                 literal.
  OPEN         — genuinely undecided. Represented by the OpenParameter()
                 sentinel below, which raises OpenParameterError on any
                 attempted arithmetic use. Do NOT replace one of these with
                 a guessed number. Replace it with the real decision, and
                 say in a comment how it was decided (measured, chosen,
                 tested, etc).

See docs/DESIGN.md "Open items" for the narrative list of every OPEN name
below, with context on why it's unresolved and what resolving it needs.
"""

import math
from dataclasses import dataclass
from typing import Union


# ---------------------------------------------------------------------------
# OPEN parameter sentinel
# ---------------------------------------------------------------------------

class OpenParameterError(RuntimeError):
    """Raised when code tries to actually use an undecided (OPEN) dimension."""


class OpenParameter:
    """
    Placeholder for a dimension the design brief explicitly left undecided.

    This is NOT a default value and NOT a guess — it carries no number at
    all. Any arithmetic or geometry call that touches one raises
    OpenParameterError immediately, so an OPEN value can never silently
    flow into a generated part. Resolve it by replacing the OpenParameter()
    call with a real number and a provenance comment, not by editing this
    class.
    """

    __slots__ = ("name", "note")

    def __init__(self, name: str, note: str):
        self.name = name
        self.note = note

    def __repr__(self):
        return f"OPEN({self.name})"

    def _blocked(self, *_args, **_kwargs):
        raise OpenParameterError(
            f"'{self.name}' is an OPEN (undecided) parameter and cannot be "
            f"used yet: {self.note}"
        )

    __add__ = __radd__ = __sub__ = __rsub__ = _blocked
    __mul__ = __rmul__ = __truediv__ = __rtruediv__ = _blocked
    __float__ = __int__ = _blocked


Number = Union[float, OpenParameter]


# ---------------------------------------------------------------------------
# Grid system                                                        STATED
# ---------------------------------------------------------------------------

GRID_PITCH_MM = 42.0          # Gridfinity-compatible internal grid pitch
HEIGHT_UNIT_MM = 7.0          # base height unit
BAY_PITCH_MM = 164.0          # width of one bay (S case outside width)


# ---------------------------------------------------------------------------
# Case sizes                                                         STATED
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Size:
    name: str
    bays: int
    grid_units_wide: int
    case_outside_width_mm: float
    default_depth_units: Number  # grid units; OPEN for L/XL (rounding undecided)


SIZES: dict[str, Size] = {
    "S":  Size("S",  bays=1, grid_units_wide=3,  case_outside_width_mm=164.0,
               default_depth_units=3),
    "M":  Size("M",  bays=2, grid_units_wide=6,  case_outside_width_mm=328.0,
               default_depth_units=4),
    "L":  Size("L",  bays=3, grid_units_wide=10, case_outside_width_mm=492.0,
               default_depth_units=OpenParameter(
                   "L.default_depth_units",
                   "Spec says 'about two thirds of width in units' "
                   "(10 * 2/3 = 6.67) but the rounding rule (floor/round/"
                   "ceil) is explicitly left OPEN in the brief.",
               )),
    "XL": Size("XL", bays=4, grid_units_wide=14, case_outside_width_mm=656.0,
               default_depth_units=OpenParameter(
                   "XL.default_depth_units",
                   "Same as L: 14 * 2/3 = 9.33, rounding rule OPEN.",
               )),
}


def validate_width_addition_rule() -> None:
    """STATED rule: S + S = M, S + M = L, M + M = XL (outside widths add
    exactly). Run at import time so a bad edit to SIZES fails loudly."""
    w = {k: v.case_outside_width_mm for k, v in SIZES.items()}
    assert w["S"] + w["S"] == w["M"], "S + S must equal M"
    assert w["S"] + w["M"] == w["L"], "S + M must equal L"
    assert w["M"] + w["M"] == w["XL"], "M + M must equal XL"


# ---------------------------------------------------------------------------
# Width stack
# ---------------------------------------------------------------------------
# Reference numbers come from a measured Vault L4 and are used ONLY to size
# Binnit's own, independently-written geometry — never copied from Vault
# files (which are licensed) or from Gridfinity derivatives (CC BY-NC-SA).

DRAWER_BOX_SIDE_WALL_MM = 4.0      # MEASURED (reference)
DRAWER_BOX_BACK_WALL_MM = 3.0      # MEASURED (reference)
DRAWER_BOX_FRONT_WALL_MM = 7.0     # MEASURED (reference) — brief says "about
                                   # 7 mm"; treat as provisional pending a
                                   # direct check against real stock.
DRAWER_BOX_FLOOR_THICKNESS_MM = 3.0  # STATED (scaffold decision) — not in
                                      # the original brief (which only gave
                                      # side/back/front wall thickness);
                                      # decided when building the step-4
                                      # generator rather than guessed.

CASE_WALL_MM = 3.0                 # MEASURED (reference)
CASE_SIDE_TOTAL_MM = 15.0          # MEASURED (reference) — per side, includes
                                   # slide channels
CASE_SIDE_OUTER_WALL_MM = 3.0      # MEASURED (reference) — outer wall on the
                                   # outside of each slide-channel cutout,
                                   # included within CASE_SIDE_TOTAL_MM above

# Slide mechanism: a real 3-member telescoping slide (fixed case rail +
# floating intermediate rail + fixed drawer rail), not a cosmetic relief
# pocket — an earlier version of this file described a blind weight-
# relief pocket here; that was replaced once research into how full-
# extension drawer slides work in general (three-member telescoping,
# a well-known mechanical pattern — see src/slide.py's module docstring)
# made clear the 15 mm "including slide channels" allowance is meant to
# physically house the mechanism, not just save material.
#
# Each of the two dovetail interfaces (case<->intermediate,
# intermediate<->drawer) uses the SAME angle and clearance already
# established for the interlock connector (INTERLOCK_DOVETAIL_ANGLE_DEG,
# INTERLOCK_SLIDING_CLEARANCE_MM) — reused, not duplicated, since it's
# the same kind of captured sliding joint. Root width and engagement
# height are new, STATED decisions sized to fit twice (plus the
# intermediate's own solid core) inside the channel budget of
# CASE_SIDE_TOTAL_MM - CASE_SIDE_OUTER_WALL_MM = 12 mm: 2 mm engagement
# each side leaves an 8 mm solid core in the intermediate rail — see
# slide_intermediate_thickness_mm() below.
SLIDE_RAIL_HEIGHT_MM = 2.0          # STATED decision — engagement depth,
                                     # each of the two interfaces
SLIDE_RAIL_ROOT_WIDTH_MM = 6.0      # STATED decision — narrow-end width
SLIDE_DRAWER_RAIL_LENGTH_MM = 20.0  # STATED decision — the drawer's own
                                     # rail is short and fixed-length,
                                     # not scaled to case depth
SLIDE_Y_MARGIN_MM = 5.0             # STATED decision — inset from the
                                     # case's front opening and back wall
                                     # so the case rail doesn't breach
                                     # either (reused name/spirit from
                                     # the old CASE_SIDE_CHANNEL_Y_MARGIN_MM)
SLIDE_Z_MARGIN_MM = 5.0             # STATED decision — inset from the
                                     # top and bottom of the shell

CASE_TOP_BOTTOM_SKIN_MM = 3.0      # MEASURED (reference)
CASE_BACK_WALL_MM = 2.0            # ASSUMPTION — stated explicitly as an
                                   # assumption in the brief, not measured

# Side channels cut into the insert, by size. S has none.           INFERRED
INSERT_SIDE_CHANNEL_MM: dict[str, float] = {
    "S": 0.0,
    "M": 19.0,
    "L": 17.0,
    "XL": 15.0,
}


def drawer_box_outside_width_mm(size: str) -> float:
    """FORMULA: drawer box outside width = case outside width - 30 mm."""
    return SIZES[size].case_outside_width_mm - 30.0


def drawer_box_interior_width_mm(size: str) -> float:
    """FORMULA: drawer box interior width = outside width - 8 mm."""
    return drawer_box_outside_width_mm(size) - 8.0


# ---------------------------------------------------------------------------
# Depth
# ---------------------------------------------------------------------------

DEPTH_MIN_UNITS = 3                # STATED
DEPTH_MAX_UNITS = 10               # STATED

GAP_DRAWER_BACK_TO_CASE_BACK_MM = 1.0   # STATED
GAP_ABOVE_CASE_BOTTOM_MM = 1.0          # STATED

# Facer: a plate attached to the drawer box's (already flush) front
# face, projecting forward beyond the case's own front opening by its
# own thickness. All STATED decisions below, resolving what the brief
# left OPEN — none of these are measured or derived.
FACER_THICKNESS_MM = 3.0           # STATED decision — reuses
                                   # CASE_TOP_BOTTOM_SKIN_MM's value for
                                   # consistency with the rest of the
                                   # design, not an independent guess
KNOB_DIAMETER_MM = 16.0            # STATED decision — plain cylindrical
                                   # knob, roughly a common drawer-pull size
KNOB_PROJECTION_MM = 12.0          # STATED decision — resolves the
                                   # brief's OPEN item

# Latch: not a security lock — a small tactile detent so the drawer
# doesn't drift open on its own (in transit, hanging on a bar), same
# family as the interlock's end-of-travel detent (see its comment for
# the same rigid-CAD-can't-model-elastic-give caveat, which applies
# here too). A bump centered on the facer's TOP face, projecting
# upward (+Z) past the drawer's own top surface, into the 1mm gap that
# case_interior_height_mm() leaves above the drawer (GAP_ABOVE_CASE_
# BOTTOM_MM — the drawer sits flush at the cavity's bottom, so that 1mm
# lives above it, not below, despite the constant's name) and slightly
# beyond it, engaging a shallow notch cut into the underside of the
# case's top skin right at the front opening. The bump's radius is
# deliberately bigger than that 1mm nominal clearance (same reasoning
# as the interlock detent) — it has to interfere with the plain
# underside everywhere except the one designed spot to do anything.
FACER_LATCH_BUMP_RADIUS_MM = 1.5          # STARTING — untested


def grid_depth_mm(depth_units: int) -> float:
    """Depth, in mm, for a given number of 42 mm grid units."""
    return depth_units * GRID_PITCH_MM


def drawer_box_interior_depth_mm(depth_units: int) -> float:
    """FORMULA: drawer box interior depth = grid depth + 8 mm."""
    return grid_depth_mm(depth_units) + 8.0


def drawer_box_outside_depth_mm(depth_units: int) -> float:
    """FORMULA: drawer box outside depth = interior depth + 10 mm."""
    return drawer_box_interior_depth_mm(depth_units) + 10.0


def case_depth_mm(depth_units: int) -> float:
    """FORMULA: case depth = grid depth + 21 mm
    (2 mm back wall + 1 mm gap + drawer box at grid + 18 mm)."""
    return grid_depth_mm(depth_units) + 21.0


# ---------------------------------------------------------------------------
# Height
# ---------------------------------------------------------------------------

FLOOR_COUNTS_OFFERED = (1, 2, 4)   # STATED — no 3-floor option

DRAWER_BOX_FLOOR1_OUTSIDE_MM = 37.0   # MEASURED
DRAWER_BOX_FLOOR1_INSIDE_MM = 34.0    # MEASURED
DRAWER_BOX_EXTRA_FLOOR_MM = 49.0      # MEASURED — each additional floor adds
                                      # this much outside height

# Case built from 4 floors — given directly in the brief as its own fact,
# not derived from the per-floor formula above (the two are not required
# to reconcile; both are recorded as stated).
CASE_4FLOOR_INTERIOR_MM = 185.0       # STATED
CASE_4FLOOR_SKIN_TOP_BOTTOM_MM = 3.0  # STATED (matches CASE_TOP_BOTTOM_SKIN_MM)
CASE_4FLOOR_CONNECTOR_MM = 5.0        # STATED — connectors top and bottom

HEIGHT_STACK_GAP_MM = OpenParameter(
    "HEIGHT_STACK_GAP_MM",
    "Brief notes a 1 mm gap exists somewhere in the height stack (as with "
    "the depth and width stacks) but does not say where/how much; left "
    "OPEN rather than assumed equal to the depth/width gaps.",
)


def drawer_box_outside_height_mm(floors: int) -> float:
    """FORMULA: outside height for a given floor count.
    Only floor counts in FLOOR_COUNTS_OFFERED are supported designs;
    other counts are OPEN (brief says so explicitly)."""
    if floors not in FLOOR_COUNTS_OFFERED:
        raise OpenParameterError(
            f"{floors}-floor drawer boxes are OPEN — only "
            f"{FLOOR_COUNTS_OFFERED} are offered per the brief."
        )
    return DRAWER_BOX_FLOOR1_OUTSIDE_MM + DRAWER_BOX_EXTRA_FLOOR_MM * (floors - 1)


def drawer_box_inside_height_mm(floors: int) -> float:
    if floors not in FLOOR_COUNTS_OFFERED:
        raise OpenParameterError(
            f"{floors}-floor drawer boxes are OPEN — only "
            f"{FLOOR_COUNTS_OFFERED} are offered per the brief."
        )
    return DRAWER_BOX_FLOOR1_INSIDE_MM + DRAWER_BOX_EXTRA_FLOOR_MM * (floors - 1)


# ---------------------------------------------------------------------------
# Interlock (Binnit's own design — not Vault-compatible)
# ---------------------------------------------------------------------------

INTERLOCK_RAIL_HEIGHT_MM = 5.0         # STATED — dovetail rail, top of bay
INTERLOCK_PAD_HEIGHT_MM = 5.0          # STATED — raised pad, bottom of bay,
                                       # with the dovetail groove cut into it
INTERLOCK_DOVETAIL_ANGLE_DEG = 45.0    # STATED — per side, from vertical
INTERLOCK_SLIDING_CLEARANCE_MM = 0.3   # STARTING — per side; untested

INTERLOCK_SIDE_ZONE_MM = 15.0          # STATED — available width at the bay
                                       # edge for the connector

INTERLOCK_DOVETAIL_WIDTH_MM = 3.0   # STATED decision — see note below
# This is the dovetail's width at its ROOT (narrow end, where the rail
# meets the top skin / the groove meets the pad) — not the wide end it
# flares out to over its 5 mm height. Chosen, not measured: a 5 mm tall,
# 45-degree dovetail spreads 2 * 5 * tan(45) = 10 mm wider across its
# height (see dovetail_wide_width_mm()), and the available side zone is
# only 15 mm (INTERLOCK_SIDE_ZONE_MM) — so root width + 10 mm must fit
# inside 15 mm. 3 mm leaves 1 mm margin per side (13 mm wide end inside
# the 15 mm zone); 4 mm would leave only 0.5 mm/side, 5 mm leaves none.
# Picked for a bit of printable margin, not derived from a stated fact —
# flagged STARTING like INTERLOCK_SLIDING_CLEARANCE_MM: a real print/load
# test (see the stand/hang test stubs) could still move this.
# End-of-travel detent — STATED decision: a small bump on the rail,
# matched by a slightly-larger dimple cut into the groove at the same
# position, near the back end (where the connector sits once fully
# slid home — see src/interlock.py's module docstring on the front-to-
# back assembly motion). Self-contained within the rail/groove parts
# (not the case shell): placed at a fixed fraction of the dovetail's
# own height-taper, so the two line up once stacked regardless of
# which case sizes are paired.
#
# A real caveat, not glossed over: a rigid CAD boolean can't represent
# the elastic "push past it" feel of a plastic snap detent — the bump
# is deliberately sized larger than the nominal sliding clearance, so
# a literal rigid intersection check WOULD show interference everywhere
# along the slide except at the exact designed position (where the
# dimple is enlarged to match). That's the intended behavior, not a
# bug; tests/test_interlock.py checks fit at the designed position only.
INTERLOCK_DETENT_RADIUS_MM = 1.0              # STARTING — untested, like
                                               # the sliding clearance
INTERLOCK_DETENT_OFFSET_FROM_BACK_MM = 5.0    # STATED decision — close to
                                               # full engagement, not
                                               # partway through the slide
INTERLOCK_DETENT_HEIGHT_FRACTION = 0.5        # STATED decision — midway
                                               # up the dovetail's taper


def dovetail_wide_width_mm(root_width_mm: float = INTERLOCK_DOVETAIL_WIDTH_MM,
                            rail_height_mm: float = INTERLOCK_RAIL_HEIGHT_MM,
                            angle_deg: float = INTERLOCK_DOVETAIL_ANGLE_DEG) -> float:
    """FORMULA: the dovetail's width at its wide end (tip of the rail /
    opening of the groove), where root_width_mm is the narrow end. Not
    an independent guess — it falls out of the rail height and angle."""
    return root_width_mm + 2.0 * rail_height_mm * math.tan(math.radians(angle_deg))


def _validate_dovetail_fits_side_zone() -> None:
    wide = dovetail_wide_width_mm()
    assert wide <= INTERLOCK_SIDE_ZONE_MM, (
        f"Dovetail wide-end width {wide} mm exceeds the "
        f"{INTERLOCK_SIDE_ZONE_MM} mm side zone — INTERLOCK_DOVETAIL_WIDTH_MM, "
        "INTERLOCK_RAIL_HEIGHT_MM, or INTERLOCK_DOVETAIL_ANGLE_DEG changed "
        "without rechecking this fit."
    )


def slide_intermediate_thickness_mm() -> float:
    """FORMULA: the intermediate rail's plate spans the ENTIRE channel
    budget left after the outer wall — from the case rail's own
    reference face to the drawer rail's own reference face, with
    nothing left over. Its solid core, after both dovetail grooves are
    cut into it, is this minus both engagement depths — see
    _validate_slide_intermediate_has_a_real_core() below."""
    return CASE_SIDE_TOTAL_MM - CASE_SIDE_OUTER_WALL_MM


def _validate_slide_intermediate_has_a_real_core() -> None:
    core = slide_intermediate_thickness_mm() - 2.0 * SLIDE_RAIL_HEIGHT_MM
    assert core > 0, (
        f"slide_intermediate_thickness_mm() ({slide_intermediate_thickness_mm()} mm) "
        f"minus both SLIDE_RAIL_HEIGHT_MM engagements "
        f"({2.0 * SLIDE_RAIL_HEIGHT_MM} mm) must stay positive — the two dovetail "
        "cuts can't consume the entire intermediate rail and leave nothing solid "
        "between them."
    )


def slide_case_rail_length_mm(depth_units: int) -> float:
    """FORMULA: the case's own rail runs the case depth, inset front and
    back by SLIDE_Y_MARGIN_MM so it doesn't breach either wall."""
    return case_depth_mm(depth_units) - 2.0 * SLIDE_Y_MARGIN_MM


def slide_intermediate_length_mm(depth_units: int) -> float:
    """FORMULA: half the case rail's own length. Not a stop-tab-timed
    full-extension calculation (src/slide.py's module docstring is
    explicit about that simplification) — just the proportion that
    lets the intermediate travel meaningfully along the case rail
    while the drawer travels meaningfully along the intermediate,
    rather than one stage dominating the other."""
    return slide_case_rail_length_mm(depth_units) / 2.0


def _validate_slide_lengths_nest(depth_units: int = DEPTH_MIN_UNITS) -> None:
    assert SLIDE_DRAWER_RAIL_LENGTH_MM < slide_intermediate_length_mm(depth_units), (
        f"SLIDE_DRAWER_RAIL_LENGTH_MM ({SLIDE_DRAWER_RAIL_LENGTH_MM} mm) must be "
        f"shorter than slide_intermediate_length_mm({depth_units}) "
        f"({slide_intermediate_length_mm(depth_units)} mm) at the minimum supported "
        "depth, or the drawer's own rail can't fit within the intermediate's groove "
        "at all."
    )

# Design assumption stated in the brief: horizontal rows are assumed full;
# partial rows (a connector line with no case on one side) are not covered
# by this design yet. Not a dimension, but recorded here since it bounds
# which geometry the interlock generator is allowed to assume.
INTERLOCK_ASSUMES_FULL_ROWS = True


def interlock_connector_line_count(bays: int) -> int:
    """STATED rule: connectors sit at every bay boundary — n+1 lines for
    n bays, including the center line(s) over the 3 mm case skin."""
    return bays + 1


# ---------------------------------------------------------------------------
# Case height — FORMULA, reconciled against the one stated case-height
# fact in the brief (the 4-floor case), not invented.
# ---------------------------------------------------------------------------
#
# The brief gives the 4-floor case's interior (185 mm) and its skin/
# connector thicknesses as separate stated facts, but never states a
# general "case height" formula for any floor count. Reconciling them:
#   drawer_box_outside_height_mm(4) + GAP_ABOVE_CASE_BOTTOM_MM
#     = 184 + 1 = 185 mm == CASE_4FLOOR_INTERIOR_MM  (checked below)
# So case interior height = drawer box outside height (for that floor
# count) + the already-stated 1 mm bottom gap — which generalizes to any
# floor count in FLOOR_COUNTS_OFFERED, not just 4. Case outside height
# then stacks the two skins and the two interlock connectors (the brief
# names these once generically under Interlock — RAIL/PAD_HEIGHT_MM —
# and once again specifically for the 4-floor case as
# CASE_4FLOOR_CONNECTOR_MM; both are 5 mm, confirming it's the same
# floor-independent feature, not two different facts).

def case_interior_height_mm(floors: int) -> float:
    """FORMULA: drawer_box_outside_height_mm(floors) + the 1 mm gap above
    the case bottom. Raises OpenParameterError for floor counts the
    drawer box itself doesn't support (same restriction, inherited)."""
    return drawer_box_outside_height_mm(floors) + GAP_ABOVE_CASE_BOTTOM_MM


def case_outside_height_mm(floors: int) -> float:
    """FORMULA: interior height + top/bottom skins + top/bottom interlock
    connectors (rail height on top, pad height on bottom)."""
    return (case_interior_height_mm(floors)
            + 2.0 * CASE_TOP_BOTTOM_SKIN_MM
            + INTERLOCK_RAIL_HEIGHT_MM
            + INTERLOCK_PAD_HEIGHT_MM)


def _validate_case_4floor_height_reconciles() -> None:
    derived_interior = case_interior_height_mm(4)
    assert derived_interior == CASE_4FLOOR_INTERIOR_MM, (
        f"Derived 4-floor case interior height {derived_interior} mm != "
        f"the brief's stated CASE_4FLOOR_INTERIOR_MM ({CASE_4FLOOR_INTERIOR_MM} mm). "
        "Something in the height stack (DRAWER_BOX_FLOOR1_OUTSIDE_MM, "
        "DRAWER_BOX_EXTRA_FLOOR_MM, or GAP_ABOVE_CASE_BOTTOM_MM) no longer "
        "reconciles with that stated fact — check before trusting "
        "case_outside_height_mm() for any floor count."
    )


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------

PRINT_BED_XY_MM = 256.0            # STATED default (stock Bambu Lab bed)
PRINT_BED_USABLE_XY_MM = 250.0     # STATED — "about 250 mm usable"; CI and
                                   # generators should treat this, not the
                                   # raw bed size, as the real envelope
PRINT_PROFILE_NOTE = (
    "Default target: stock Bambu Lab standard profile, light build "
    "(matching the Vault's lighter reinforcement). Not a dimension — "
    "documented here for traceability to the brief."
)

# STL export mesh quality — STATED decision, not a dimension of the
# part itself. build123d's own default (tolerance=0.001mm) is far
# finer than any FDM printer's resolution, and gets expensive fast on
# curved features: the interlock detent's small sphere alone pushed a
# case export from ~8KB to ~860KB at the default before this was tuned
# down. 0.1mm linear / 0.3mm angular deflection is still well under
# typical nozzle/layer resolution (~0.1-0.4mm) and cuts case file sizes
# by roughly 5-8x. Every generator's export_stl() call should pass
# these rather than relying on build123d's own default.
STL_EXPORT_TOLERANCE_MM = 0.1           # STATED decision
STL_EXPORT_ANGULAR_TOLERANCE = 0.3      # STATED decision (radians)

# --- Splitting oversized parts (brief: "split on grid lines") ------------
#
# DECIDED: splits land on the 42 mm internal grid (GRID_PITCH_MM), not the
# 164 mm bay pitch. Reasoning (given directly, not inferred): a small bed
# like a Voron Zero's 120x120 mm can't even fit one whole bay pitch
# (164 mm) in a single piece, so bay-pitch splitting would be useless on
# it — the internal grid is the only one fine enough to be useful across
# the range of beds this project targets.
SPLIT_GRID_PITCH_MM = GRID_PITCH_MM

# What holds two split halves together after printing — DECIDED: a
# repeating chevron ("zigzag finger joint") cut into the split plane
# itself, self-aligning on straight-on contact (unlike the stacking
# interlock's dovetail, this doesn't slide together — good, since it's
# meant to be glued, and sliding glue-covered faces together is a mess).
# Glue carries the actual bonding strength; the zigzag's job is to
# register the two halves exactly and multiply the bonded surface area
# versus a flat butt cut.
SPLIT_JOINT_TYPE = "chevron"          # STATED decision

SPLIT_JOINT_ANGLE_DEG = 45.0          # STATED decision — matches
                                      # INTERLOCK_DOVETAIL_ANGLE_DEG, for
                                      # visual/structural consistency
                                      # across the whole design

# Tooth amplitude: sized to fit inside the thinnest walls a split is
# likely to cross without a tooth poking through the far face or leaving
# an unsupported sliver. Derived from the two 3mm skins named directly as
# the limiting case (not a bare literal): the drawer box floor and the
# case top/bottom skins.
SPLIT_JOINT_FEATURE_SIZE_MM = min(               # FORMULA — see note above
    DRAWER_BOX_FLOOR_THICKNESS_MM, CASE_TOP_BOTTOM_SKIN_MM
) / 2.0
# Note: this does NOT account for CASE_BACK_WALL_MM (2mm, itself only an
# ASSUMPTION) or any other wall thinner than 3mm. A split crossing
# thinner material should pass a smaller feature_size_mm explicitly to
# src/split.py rather than rely on this default.


def chevron_pitch_mm(feature_size_mm: float, angle_deg: float) -> float:
    """FORMULA: tooth pitch for a triangular zigzag of the given leg
    angle and amplitude. A triangle wave with `angle_deg`-from-vertical
    legs and amplitude `feature_size_mm` has half-pitch =
    feature_size_mm / tan(angle_deg); this is the full pitch. Not an
    independent guess — it falls out of the angle and amplitude once
    both of those are chosen."""
    return 2.0 * feature_size_mm / math.tan(math.radians(angle_deg))


SPLIT_JOINT_PITCH_MM = chevron_pitch_mm(       # FORMULA — see function above
    SPLIT_JOINT_FEATURE_SIZE_MM, SPLIT_JOINT_ANGLE_DEG
)  # = 3.0 mm at the defaults above

SPLIT_JOINT_CLEARANCE_MM = 0.15       # STARTING — untested starting value,
                                      # half of INTERLOCK_SLIDING_CLEARANCE_MM.
                                      # This joint is hand-registered and
                                      # glued, not slid together, so a
                                      # tighter gap is reasonable to try
                                      # first — but like that other
                                      # clearance, this needs tuning by
                                      # actually printing it, not trusted
                                      # as final.

# Tip relief: FDM prints tend to round/bulge slightly at sharp convex
# (outside) corners — the nozzle can't reverse direction instantly, so
# material pools a bit at each direction change — while the matching
# concave (inside) corner on the neighboring piece prints close to
# nominal. Every chevron peak is exactly that pairing (one piece's
# convex tip nesting into the other's concave notch), so a perfectly
# sharp modeled point risks interference right at the tip even though
# the flat faces have clearance. Fix: truncate every peak/trough into a
# small flat (on both pieces) instead of modeling a sharp point.
#
# DECIDED: reuse SPLIT_JOINT_CLEARANCE_MM for this rather than inventing
# a second, independent provisional number — both represent the same
# underlying "how much print tolerance to allow for" judgment call.
SPLIT_JOINT_TIP_RELIEF_MM = SPLIT_JOINT_CLEARANCE_MM


# ---------------------------------------------------------------------------
# Self-check — run at import time so a broken edit to this file fails loudly
# rather than silently producing a bad part.
# ---------------------------------------------------------------------------

validate_width_addition_rule()
_validate_dovetail_fits_side_zone()
_validate_case_4floor_height_reconciles()
_validate_slide_intermediate_has_a_real_core()
_validate_slide_lengths_nest()


if __name__ == "__main__":
    print("Binnit params OK.")
    for size in SIZES.values():
        print(f"  {size.name}: outside width {size.case_outside_width_mm} mm, "
              f"drawer interior width {drawer_box_interior_width_mm(size.name)} mm")
