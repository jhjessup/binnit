# Binnit — Design

Binnit is an open, parametric, 3D-printable modular storage system
(drawer boxes + cases + inserts + an interlock), designed as code. This
document is the narrative companion to [`params/params.py`](../params/params.py),
which is the actual single source of truth for every number. If this
document and `params.py` ever disagree, `params.py` wins — file an issue
or PR to fix the mismatch.

Binnit is its own design. Geometry here is written independently to the
dimensions in this document; nothing is copied or derived from USSA Vault
files (licensed) or from the popular Gridfinity derivatives (CC BY-NC-SA).
A measured Vault L4 unit is used only as a *reference* for a handful of
width-stack numbers, called out explicitly below as `MEASURED`.

## Provenance key

Every dimension in `params.py` and in this document is tagged with how
solid it is:

| Tag | Meaning |
|-----|---------|
| STATED | Given directly and exactly in the design brief. |
| MEASURED | Taken from a measured reference unit (Vault L4), reference only. |
| ASSUMPTION | Explicitly flagged as a guess in the brief. Usable, not verified. |
| INFERRED | Estimated, not measured. Same caveat as ASSUMPTION. |
| STARTING | Deliberately provisional (e.g. a clearance); meant to be tuned by printing/testing. |
| FORMULA | Computed from other named parameters; never a bare literal. |
| OPEN | Genuinely undecided — see [Open items](#open-items). Represented in code by the `OpenParameter` sentinel, which raises rather than silently computing with a guess. |

## Grid system

- Internal grid pitch: **42 mm**, Gridfinity-compatible (`GRID_PITCH_MM`).
- Height unit: **7 mm** (`HEIGHT_UNIT_MM`).
- Bay pitch: **164 mm**, one S-sized bay (`BAY_PITCH_MM`).
- All case widths are whole numbers of bays.

### Sizes

| Size | Bays | Grid units wide | Case outside width |
|------|------|------------------|---------------------|
| S    | 1    | 3                | 164 mm |
| M    | 2    | 6                | 328 mm |
| L    | 3    | 10               | 492 mm |
| XL   | 4    | 14               | 656 mm |

Rule (enforced by `validate_width_addition_rule()` at import time):
**S + S = M**, **S + M = L**, **M + M = XL** — outside widths add exactly.

## Width stack

Reference numbers below come from a measured Vault L4 and size Binnit's
own, independently-written geometry — they are not copied Vault geometry.

- Drawer box side wall: **4 mm** (`DRAWER_BOX_SIDE_WALL_MM`, MEASURED)
- Drawer box back wall: **3 mm** (`DRAWER_BOX_BACK_WALL_MM`, MEASURED)
- Drawer box front wall: **~7 mm** (`DRAWER_BOX_FRONT_WALL_MM`, MEASURED —
  brief says "about 7 mm"; treat as provisional pending a direct check)
- Case wall: **3 mm** (`CASE_WALL_MM`, MEASURED)
- Case sides: **15 mm total** per side, including slide channels, with a
  **3 mm** outer wall on the outside of each cutout
  (`CASE_SIDE_TOTAL_MM`, `CASE_SIDE_OUTER_WALL_MM`, MEASURED)
- Case top/bottom skins: **3 mm** (`CASE_TOP_BOTTOM_SKIN_MM`, MEASURED)
- Case back wall: **2 mm** (`CASE_BACK_WALL_MM`, **ASSUMPTION** — the brief
  flags this one explicitly as a guess, not a measurement)
- Insert side channels (INFERRED, not measured): S none, M ~19 mm,
  L ~17 mm, XL ~15 mm (`INSERT_SIDE_CHANNEL_MM`)
- Drawer box floor thickness: **3 mm** (`DRAWER_BOX_FLOOR_THICKNESS_MM`,
  STATED as a scaffold decision — not in the original brief, which only
  gave side/back/front wall thickness; decided explicitly when building
  the first generator rather than assumed)

Formulas:
- Drawer box outside width = case outside width − 30 mm
  (`drawer_box_outside_width_mm()`)
- Drawer box interior width = outside width − 8 mm
  (`drawer_box_interior_width_mm()`)

## Depth

- Depth is a parameter from **3 to 10** grid units
  (`DEPTH_MIN_UNITS`, `DEPTH_MAX_UNITS`).
- Defaults: S = 3, M = 4 units. L and XL default to "about two thirds of
  width in units" — **the rounding rule is OPEN**, so `SIZES["L"]` and
  `SIZES["XL"]` carry an `OpenParameter` instead of a number; see
  [Open items](#open-items).
- Drawer box interior depth = grid depth + 8 mm
  (`drawer_box_interior_depth_mm()`)
- Drawer box outside depth = interior depth + 10 mm
  (`drawer_box_outside_depth_mm()`)
- Case depth = grid depth + 21 mm (2 mm back wall + 1 mm gap + drawer box
  at grid + 18 mm) (`case_depth_mm()`)
- 1 mm gap between drawer box back and case back
  (`GAP_DRAWER_BACK_TO_CASE_BACK_MM`, STATED)
- 1 mm vertical gap above the case bottom
  (`GAP_ABOVE_CASE_BOTTOM_MM`, STATED)
- The drawer box sits flush with the case front; a separate facer piece
  (latch + knob) sits proud of it. Facer thickness and knob projection
  are **OPEN** (`FACER_THICKNESS_MM`, `KNOB_PROJECTION_MM`).

## Height

From measurement of the reference unit:

- 1 floor: **37 mm** outside, **34 mm** inside
- 2 floors: **86 mm** outside, **83 mm** inside
- Each additional floor adds **49 mm**
  (`DRAWER_BOX_FLOOR1_OUTSIDE_MM`, `DRAWER_BOX_FLOOR1_INSIDE_MM`,
  `DRAWER_BOX_EXTRA_FLOOR_MM`)
- Floor counts offered: **1, 2, 4** — no 3 (`FLOOR_COUNTS_OFFERED`).
  `drawer_box_outside_height_mm()` / `drawer_box_inside_height_mm()` raise
  for any other count, since the brief treats those as OPEN rather than
  letting the per-floor formula silently extrapolate to them.
- A 4-floor case is given directly as its own stated fact (not required
  to reconcile with the per-floor formula above): **185 mm** interior,
  **3 mm** skin top and bottom, plus **5 mm** connectors top and bottom
  (`CASE_4FLOOR_INTERIOR_MM`, `CASE_4FLOOR_SKIN_TOP_BOTTOM_MM`,
  `CASE_4FLOOR_CONNECTOR_MM`).
- The 1 mm gap mentioned for the height stack is **OPEN**
  (`HEIGHT_STACK_GAP_MM`) — unlike the depth stack's two 1 mm gaps, the
  brief doesn't say where in the height stack this gap sits or whether
  it's exactly 1 mm here too.

## Interlock

Binnit's own design — not Vault-compatible.

- Tool-free; must carry a hanging load (two joined cases, one mounted to
  a bar, the other hanging off it).
- Top/bottom stacking only; no side-by-side interlock.
- Slides in from the front.
- **5 mm** tall dovetail rail on the top of each bay; **5 mm** raised pad
  on the bottom of each bay with the dovetail groove cut into it
  (`INTERLOCK_RAIL_HEIGHT_MM`, `INTERLOCK_PAD_HEIGHT_MM`, STATED).
  Connectors are in addition to the 3 mm skin; when stacked, the rail
  seats into the groove.
- Dovetail angle: **45°** per side from vertical
  (`INTERLOCK_DOVETAIL_ANGLE_DEG`, STATED).
- Sliding clearance: **0.3 mm** per side
  (`INTERLOCK_SLIDING_CLEARANCE_MM`, **STARTING** — explicitly an
  untested starting value, meant to be tuned).
- Load must transfer down the case sides. Connectors sit at every bay
  boundary — **n+1 lines for n bays**, including the center line(s) over
  the 3 mm skin (`interlock_connector_line_count()`).
- **Design assumption**: horizontal rows are assumed full; partial rows
  (a connector line with no case on one side) are not covered by this
  design (`INTERLOCK_ASSUMES_FULL_ROWS`).
- Smaller cases may stack on larger ones — including shallower on
  deeper — on the shared 164 mm bay pitch.
- Available side zone for the connector: **15 mm**
  (`INTERLOCK_SIDE_ZONE_MM`, STATED) — this is the constraint that makes
  dovetail width an open question (see below).

## Printing

- Default target: stock Bambu Lab standard profile, light build, matching
  the Vault's lighter reinforcement (`PRINT_PROFILE_NOTE`).
- `print_bed_xy` parameter, default **256 mm**
  (`PRINT_BED_XY_MM`), about **250 mm** usable
  (`PRINT_BED_USABLE_XY_MM`) — generators and CI should check against the
  usable figure, not the raw bed size.
- Parts larger than the envelope are split on grid lines. CI must fail
  any generated part that exceeds the envelope (see `/tests` and the
  build workflow).

### Splitting oversized parts

`src/split.py`'s `split_to_fit(part, grid_pitch_mm=None, bed_xy_mm=None,
joint=True, ...)` is the interface for this: it cuts a part on lines
spaced `grid_pitch_mm` apart (X and Y only, same as the envelope check —
no stated Z/gantry limit to split against) into the minimal number of
pieces that each fit `bed_xy_mm` (default `PRINT_BED_USABLE_XY_MM`),
returning a `SplitPiece` per piece with its grid cell index and its
offset back into the original part's coordinate frame.

**Which grid — DECIDED.** Splits land on the **42 mm internal grid**
(`GRID_PITCH_MM`, aliased as `SPLIT_GRID_PITCH_MM` and the default for
`grid_pitch_mm`), not the 164 mm bay pitch. Reasoning: a small bed — a
Voron Zero's 120x120 mm was the deciding example — can't fit even one
whole bay pitch (164 mm) in a single piece, so bay-pitch splitting would
be useless on it; the finer internal grid works across the range of beds
this project targets. `tests/test_split.py` proves this out directly: a
164 mm-wide (one bay) part correctly splits to fit a 120 mm bed on the
internal grid, while attempting the same split on the bay pitch raises
`SplitError` (the first grid line already exceeds the bed).

**What joins the pieces back together — DECIDED.** A repeating chevron
("zigzag finger joint") cut into the split plane itself
(`SPLIT_JOINT_TYPE = "chevron"`), self-aligning on straight-on contact —
unlike the stacking interlock's dovetail, it does not slide together,
which matters here because this joint is meant to be glued and sliding
glue-covered faces together is a mess. Glue carries the bonding
strength; the zigzag registers the two halves exactly and multiplies the
bonded surface area versus a flat cut.

Dimensions, all in `params.py`:
- `SPLIT_JOINT_ANGLE_DEG` = **45°** — matches `INTERLOCK_DOVETAIL_ANGLE_DEG`.
- `SPLIT_JOINT_FEATURE_SIZE_MM` = **1.5 mm** (FORMULA: half of the
  thinner of `DRAWER_BOX_FLOOR_THICKNESS_MM` / `CASE_TOP_BOTTOM_SKIN_MM`,
  both 3 mm) — sized to fit inside the thinnest walls a split is likely
  to cross without a tooth poking through the far face. Doesn't account
  for `CASE_BACK_WALL_MM` (2 mm, itself only an ASSUMPTION) or any wall
  thinner than 3 mm; a split through thinner material should pass a
  smaller `feature_size_mm` explicitly.
- `SPLIT_JOINT_PITCH_MM` = **3.0 mm** (FORMULA via `chevron_pitch_mm()`:
  pitch follows from angle + amplitude, not a separate guess).
- `SPLIT_JOINT_CLEARANCE_MM` = **0.15 mm** per mating face (STARTING —
  untested, half of `INTERLOCK_SLIDING_CLEARANCE_MM` since this joint is
  hand-registered and glued rather than slid together; needs tuning by
  printing it, same as that other clearance).
- `SPLIT_JOINT_TIP_RELIEF_MM` = **0.15 mm** (`= SPLIT_JOINT_CLEARANCE_MM`
  — reused rather than a second independent guess). Every peak/trough is
  truncated into a small flat by this amount on both mating pieces,
  rather than modeled as a perfect sharp point: FDM prints tend to
  round/bulge slightly at sharp convex corners (the nozzle can't reverse
  direction instantly), and every chevron peak is exactly that convex
  tip on one piece nesting into the matching concave notch on its
  neighbor. Truncating gives that expected deformation somewhere planned
  to go instead of an uncontrolled interference right at the tip.

`joint=True` is `split_to_fit()`'s default; `joint=False` reverts to a
plain flat butt cut (used for the pure splitting-mechanism tests).
Scope note: chevron teeth are applied per axis in two sequential passes
(split X, then split Y per column) — every cut gets its teeth, but the
corner where an X cut crosses a Y cut isn't specially mitered. Still a
true boolean partition of the real part either way, just a cosmetic/
structural approximation at that corner.

No generator produces an oversized part yet (the only generator so far,
the S drawer box, fits the bed). The interface — both the grid choice
and the chevron joint — is validated against synthetic oversized test
boxes in `tests/test_split.py`, and is meant to be wired into the case
generator once that exists — likely needed for L (492 mm) and XL
(656 mm), both over the 250 mm usable bed in width alone.

## Testing (protocol stub)

Placeholder only — no load figures or pass criteria yet, by design (the
brief is explicit that these are informal, Vault-style checks, not an
engineering spec):

1. **Stand test** — stand on a finished, assembled unit.
2. **Hang test** — join two units; mount one to a bar and let the other
   hang fully loaded off the interlock.

Neither test has numeric pass/fail criteria defined. Do not invent any —
this stays a protocol stub until real criteria are decided and added
here and to `/tests`.

## Open items

Every value below is genuinely undecided. In code each is an
`OpenParameter` sentinel in `params/params.py` — attempting to use one in
arithmetic raises `OpenParameterError` immediately, so none of these can
silently reach a generated part. Resolve one by replacing its
`OpenParameter(...)` call with a real number (or decision) and a
provenance comment explaining how it was decided, and remove it from this
list in the same change.

| Name (in `params.py`) | What's undecided |
|---|---|
| `SIZES["L"].default_depth_units` | Rounding rule for "about two thirds of width in units" (10 × 2/3 = 6.67) |
| `SIZES["XL"].default_depth_units` | Same rounding rule, for 14 × 2/3 = 9.33 |
| `FACER_THICKNESS_MM` | Thickness of the facer (latch + knob) piece |
| `KNOB_PROJECTION_MM` | How far the facer's knob projects |
| `HEIGHT_STACK_GAP_MM` | Whether/where a 1 mm gap exists in the height stack, and its size |
| `INTERLOCK_DOVETAIL_WIDTH_MM` | Dovetail width — tight because a 5 mm tall, 45° dovetail spreads ~10 mm wider across its height, against only a 15 mm side zone (`INTERLOCK_SIDE_ZONE_MM`) |
| `INTERLOCK_END_OF_TRAVEL_DETENT` | Mechanism and dimensions for the end-of-travel detent |

Also explicitly out of scope for now, per the brief, rather than open
questions to resolve:
- Drawer box floor counts other than 1, 2, 4 (3-floor is not offered).
- Partial (non-full) horizontal rows in the interlock.
- Numeric pass/fail criteria for the two informal tests above.
