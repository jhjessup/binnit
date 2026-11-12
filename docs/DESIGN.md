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

## Status (as of this pause point)

**Built and tested:** drawer box (`src/drawer_box.py`), case
(`src/case.py`), interlock stacking connector (`src/interlock.py`),
facer with knob + latch (`src/facer.py`), the 3-member telescoping
drawer slide (`src/slide.py`), and the oversized-part splitter
(`src/split.py`). 65 tests, all passing; CI builds and uploads STLs on
every PR. S and M sizes generated and verified; `tools/bench.html`
loads the current S assembly for visual inspection.

**Deliberately not built yet**, in rough order of how blocking they
are:
- **Insert** — the one component whose shape/role was never pinned
  down (see Open items below); nothing to build until that's decided.
- **L and XL sizes** — blocked on `SIZES["L"/"XL"].default_depth_units`
  (Open items below); the depth-rounding rule was never resolved.
- **Case↔split integration** — `src/split.py` exists and is tested in
  isolation, but no generator calls it yet; L/XL cases will need it
  once they exist (both exceed the print bed in width alone).
- **Slide mechanism gaps**, both explicitly declined when asked, not
  overlooked: no end-of-travel stop/catch tab forcing the stage
  handoff (relies on friction), and no pull-out retention stop (a
  fully-extended drawer can be pulled completely free).

See "Open items" further down for the complete, current list of
undecided `params.py` values.

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
  (latch + knob) sits proud of it. **RESOLVED** (`src/facer.py`): facer
  thickness **3 mm** (`FACER_THICKNESS_MM`, reuses `CASE_TOP_BOTTOM_SKIN_MM`'s
  value), knob **16 mm** diameter x **12 mm** projection
  (`KNOB_DIAMETER_MM`, `KNOB_PROJECTION_MM` — resolves the brief's OPEN
  item), latch as a tactile detent bump, not a lock (see
  "Facer geometry" below). All STATED decisions, not measured.
  Fixing a real bug while placing the facer: an earlier version of
  `src/case.py` put the drawer's 1mm back gap at the *front* instead
  (see `case()`'s own comment) — caught only once the facer's exact
  attachment plane actually had to be computed.

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
  (`INTERLOCK_SIDE_ZONE_MM`, STATED) — the same physical 15 mm as the
  case's own side wall (`CASE_SIDE_TOTAL_MM`), not a coincidence: the
  end connector lines sit within that wall.
- Dovetail root width: **3 mm**, at the narrow end where the rail meets
  the skin (`INTERLOCK_DOVETAIL_WIDTH_MM`, **STATED decision** — resolved
  from OPEN; see `dovetail_wide_width_mm()` in `params.py`). A 5 mm tall,
  45° dovetail spreads 10 mm wider across its height, so root width + 10 mm
  must fit inside the 15 mm zone; 3 mm leaves 1 mm margin per side (13 mm
  wide end). Chosen for a bit of printable margin, not derived — flagged
  STARTING like the sliding clearance, pending a real print/load test.
- End-of-travel detent: a small (**1 mm radius**) spherical bump on each
  rail's +X flank, matched by an enlarged dimple in the groove at the
  same position — **5 mm in from the back end** (where the connector
  sits once fully slid home), at the **midpoint** of the dovetail's
  height taper (`INTERLOCK_DETENT_RADIUS_MM`, `_OFFSET_FROM_BACK_MM`,
  `_HEIGHT_FRACTION` — all STATED decisions, resolved from OPEN). A
  real caveat: a rigid CAD boolean can't represent a snap-fit's elastic
  "push past it" give — the bump is sized larger than the sliding
  clearance on purpose, so it genuinely interferes with a *plain*
  groove wall everywhere except the one spot with a matching dimple
  (`tests/test_interlock.py` checks this directly: the boss against a
  plain groove shows real interference, and against the matching
  dimple shows none).

### Interlock and case geometry (`src/interlock.py`, `src/case.py`)

The rail (male, protrudes from a case's top skin) and the pad+groove
(female, hangs below a case's bottom skin) share one dovetail
cross-section, oriented so a **flush-skin stack** (the two cases' skins
touch directly — the connector doesn't add extra separation) nests
correctly: the rail is narrow at its base and wide at its tip; the
groove, in the pad's own frame, is wide at its attachment-to-skin face
and narrow at its tip — the *opposite* taper assignment from the rail,
not a mirror of it. Getting this backwards was a real bug caught by
`tests/test_interlock.py`'s fit check (stack a rail and a groove,
confirm zero overlap at the correct clearance, confirm a deliberate
lateral misalignment *does* show up as interference — so the check
can't be a silent no-op).

Connector lines run the **full case depth**, flush with both the front
and back faces (`ASSUMPTION`, not stated in the brief — needed to give
the connector a length; front-referencing is what lets a shallower
case's connector still line up with a deeper case's, per the brief's
"shallower on deeper" stacking allowance).

Connector line **positions** follow the stated n+1-per-bay rule, with
one DERIVED adjustment: the two end lines are inset by half
`INTERLOCK_SIDE_ZONE_MM` so their footprint lands inside the case's own
side wall instead of straddling the outer edge; interior lines (for
M/L/XL) need no adjustment since they sit on the continuous top/bottom
skin, which spans the case's full width regardless of bay position.

**Case height**, for any floor count, is a FORMULA — not stated directly
in the brief, but reconciled exactly against the one number it does
give (the 4-floor case's 185 mm interior):
`drawer_box_outside_height_mm(floors) + GAP_ABOVE_CASE_BOTTOM_MM` gives
184 + 1 = 185 mm for 4 floors, matching `CASE_4FLOOR_INTERIOR_MM`
exactly (`case_interior_height_mm()`, checked at import time by
`_validate_case_4floor_height_reconciles()`). Outside height then adds
both skins and both connectors (`case_outside_height_mm()`).

**Case side slide channels** used to be a blind cosmetic relief pocket
here — replaced with the real slide mechanism once research into how
full-extension drawer slides generally work (see "Drawer slide
mechanism" below) made clear the 15 mm "including slide channels"
allowance is meant to physically house a mechanism, not just save
material.

The case is open at the front (no front wall) for the drawer box and
the facer (`src/facer.py`, see below).

### Drawer slide mechanism (`src/slide.py`, `src/case.py`, `src/drawer_box.py`)

A real 3-member telescoping slide — Binnit's own design, not Vault's.
Researched generally (public marketing copy and a parts-list page, not
any Vault file) to understand the *mechanism type*: Vault's own parts
list names a Runner Guide, Runner Slide, and S Rail per drawer —
language consistent with the classic 3-member telescoping pattern used
in ball-bearing-free full-extension slides generally (wooden/plastic
"Euro-style" slides use the same principle; it's generic engineering,
not anyone's proprietary design). Three members, current design:

- **Case** (`src/case.py`) — contributes NO added part. Its own
  already-open channel (`_channel_open_cut`, bounded top and bottom by
  its skins) directly serves as the outer capture. This went through
  two earlier, more complicated versions (a dovetail rail, then a flat
  tab) before the simplest version — just reuse the case's existing
  geometry — was recognized as sufficient. See "History" below.
- **Intermediate rail** (`src/slide.py`) — a free-floating plate: a
  tall, plain OUTER portion sized to fit (with clearance) inside the
  case's own channel opening (no feature of its own there), and a
  built, flanged channel on its INNER face receiving the drawer's
  rail. Makes full extension possible at all — without it, a 2-piece
  slide can only extend the drawer until its own rail nears the end of
  the case's channel, well short of fully clear.
- **Drawer rail** (`src/drawer_box.py`) — a flat tab protruding from
  the drawer box's own side wall, engaging the intermediate's inner
  channel. First change ever made to `drawer_box.py` since it was
  built.

**Captured channel, not a dovetail** — the mechanism's current, and
probably final, cross-section shape. A dovetail's 45° taper resists
being pulled apart *along the insertion axis*, a direction that
essentially never gets loaded in normal drawer use; what actually loads
this joint is the drawer's **weight**, acting vertically, which a plain
captured channel (a flat tab trapped between two flanges) resists just
as completely, via simple wall containment — no taper needed. Two
further, concrete wins: a channel's flanges are plain 90° walls (no
overhang — a dovetail's wide end sits right at the ~45° limit most FDM
printers can bridge without support), and insertion depth and capture
width become **independent** dimensions (a dovetail's fixed angle locks
wide-end spread to engagement height, so giving one interface more
depth always balloons its footprint in lockstep; a channel has no such
coupling).

That decoupling is what makes the depth split intentionally asymmetric:
`SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM` = **6 mm**, `SLIDE_CASE_...` doesn't
exist as a separate number anymore — the case side needs no engagement
depth of its own at all, since it adds no feature. The two interfaces
don't see equal duty: the inner (drawer-side) channel does all the
sliding work in ordinary use (the whole stage-1 range); the outer
(case-side) capture only moves during stage 2 (full extension), which
nothing currently guarantees even happens reliably (no stop/catch tab —
see Simplifications below). The joint used constantly is the one worth
making harder to wear loose, so it gets the depth.

STATED decisions: `SLIDE_CHANNEL_WIDTH_MM` (**10 mm**, Z-extent of the
inner channel), `SLIDE_FLANGE_THICKNESS_MM` (**2 mm**, top/bottom
capture), `SLIDE_DRAWER_ENGAGEMENT_DEPTH_MM` (**6 mm**),
`SLIDE_INNER_CHANNEL_BACKING_MM` (**2 mm**, solid material behind the
channel's own far wall), `SLIDE_DRAWER_RAIL_LENGTH_MM` (**20 mm**,
fixed, not scaled to case depth), `SLIDE_Y_MARGIN_MM` / `_Z_MARGIN_MM`
(5 mm each). FORMULAs, not independent numbers:
`slide_intermediate_thickness_mm()` (fixed at 12 mm by the case and
drawer walls' own positions — the real constraint that makes the depth
trade-offs here meaningful rather than arbitrary), `slide_outer_portion_length_mm()`
(whatever's left after the inner channel's depth and backing — 4 mm),
`slide_tab_width_mm()`, `slide_case_channel_z_mm(floors)` and
`slide_intermediate_z_height_mm(floors)` (the case's existing channel
opening, and the intermediate's own height fit inside it with
clearance), `slide_case_channel_length_mm()` / `slide_intermediate_length_mm()`
(half of that).

**History, worth keeping rather than quietly erasing** — this mechanism
went through three real iterations in one session, each caught and
explained rather than silently patched over:
1. A dovetail cross-section, reused by default from the interlock
   connector without checking whether that shape fit *this* load case.
   It worked, but spent only 1/3 of the 12 mm budget on the engagements
   that actually bear load, leaving 2/3 as an inert solid core — a
   real weakness noticed by comparing against how Vault's own design
   allocates its cross-section (general terms only, never copied).
2. Rebalanced within the dovetail shape (engagement 2→4 mm, root
   6→7 mm) — better, but exposed that the dovetail's fixed 45° angle
   locks footprint to depth, so favoring one interface over the other
   (the actual goal, once duty-cycle asymmetry was recognized) was
   fighting the shape's own geometry rather than being served by it.
   Also exposed a real bug: `intermediate_rail()`'s plate Z-width
   defaulted to `root + 6`, silently clipping the groove once the
   *wide end* (not root) exceeded that margin.
3. Switched to a captured channel entirely, which resolved both: no
   coupling between depth and footprint, and the dominant real load
   (vertical sag) handled just as completely with a simpler, more
   print-friendly shape. In the process, recognized the case didn't
   need an added rail at all — its existing open channel already does
   the job.

A separate wrong turn worth recording too: in the dovetail version, a
groove's cross-section had to match its rail's cross-section using the
*rail's own reference point*, not a point centered on the receiving
part — a first draft (mirroring the interlock's own groove logic by
instinct) got this backwards and showed real interference, caught by
the same fit-check method as the interlock and facer bugs, not by
inspection. `tests/test_slide.py` also checks the drawer rail stays
clear across its *entire* stage-1 travel range, not just one static
position.

**Simplifications, not fully engineered** (flagged, not silently
skipped — both explicitly declined for this round when asked): no
end-of-travel stop/catch tab forcing the stage-1-to-stage-2 handoff
(the chosen lengths make a working slide possible, but nothing
mechanically guarantees the intermediate starts moving at the ideal
moment — in practice this relies on friction and/or care); no pull-out
retention stop (the drawer can be pulled completely free once fully
extended).

### Facer geometry (`src/facer.py`)

The facer's plate spans `drawer_box_outside_width_mm(size)` — but its
HEIGHT is `facer_height_mm(floors)`, which equals
`case_interior_height_mm(floors)`, not `drawer_box_outside_height_mm(floors)`
directly. Those two differ by exactly the same 1 mm
(`GAP_ABOVE_CASE_BOTTOM_MM`) that lives above the drawer once it's
placed flush at the cavity's bottom — a facer sized to only the
drawer's own height would leave a sliver of the case's interior
visible above it, and (the thing that actually forced this) its own
top edge would sit 1 mm short of the cavity's ceiling, too short for
the latch bump below to ever reach what it's supposed to catch on.

The **latch** (a tactile detent, not a security lock — resisting drift
in transit or on a bar, same "rigid CAD can't model elastic give"
caveat as the interlock's own detent) is a small bump
(`FACER_LATCH_BUMP_RADIUS_MM`, STARTING) centered exactly at
`(width/2, 0, facer_height)` — the facer's own back-top **corner**, not
a point centered within its plate. Both coordinates being exactly at a
boundary is load-bearing to the design, not incidental: the facer's
whole volume sits at y≥0 (forward of the case's opening, once
attached) and the case's whole volume sits at y≤0 in that same frame —
a bump centered mid-plate can never geometrically cross back to touch
anything on the case, at any height. Centering it at y=0 (and at
z=facer_height, clear of the drawer's own shorter height) is what lets
part of the sphere reach the skin's exposed front-bottom corner at
all. `src/case.py` cuts the matching notch at the identical position,
enlarged by `INTERLOCK_SLIDING_CLEARANCE_MM` (reused, not a new
number). Both tested directly in `tests/test_facer.py`: the bump
genuinely interferes with a case built without the notch, and clears
cleanly with it.

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
| `HEIGHT_STACK_GAP_MM` | Whether/where a 1 mm gap exists in the height stack, and its size |
| *(the insert, as a component)* | No param name yet — the brief only gives `INSERT_SIDE_CHANNEL_MM` (the insert's side channel widths); its overall shape and role (a liner inside the case? a tray inside the drawer? something else?) isn't described anywhere, and asking didn't resolve it this round — deferred, not modeled |

Also explicitly out of scope for now, per the brief, rather than open
questions to resolve:
- Drawer box floor counts other than 1, 2, 4 (3-floor is not offered).
- Partial (non-full) horizontal rows in the interlock.
- Numeric pass/fail criteria for the two informal tests above.
