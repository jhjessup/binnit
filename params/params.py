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

FACER_THICKNESS_MM = OpenParameter(
    "FACER_THICKNESS_MM",
    "Facer (latch + knob) piece sits proud of the case front; its "
    "thickness is explicitly OPEN in the brief.",
)
KNOB_PROJECTION_MM = OpenParameter(
    "KNOB_PROJECTION_MM",
    "How far the facer's knob projects is explicitly OPEN in the brief.",
)


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

INTERLOCK_DOVETAIL_WIDTH_MM = OpenParameter(
    "INTERLOCK_DOVETAIL_WIDTH_MM",
    "A 5 mm tall, 45-degree dovetail spreads ~10 mm wider across its "
    "height, and the side zone is only 15 mm (INTERLOCK_SIDE_ZONE_MM) — "
    "brief flags the actual width as OPEN given that tight margin.",
)
INTERLOCK_END_OF_TRAVEL_DETENT = OpenParameter(
    "INTERLOCK_END_OF_TRAVEL_DETENT",
    "Mechanism and dimensions for the end-of-travel detent are OPEN.",
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


# ---------------------------------------------------------------------------
# Self-check — run at import time so a broken edit to this file fails loudly
# rather than silently producing a bad part.
# ---------------------------------------------------------------------------

validate_width_addition_rule()


if __name__ == "__main__":
    print("Binnit params OK.")
    for size in SIZES.values():
        print(f"  {size.name}: outside width {size.case_outside_width_mm} mm, "
              f"drawer interior width {drawer_box_interior_width_mm(size.name)} mm")
