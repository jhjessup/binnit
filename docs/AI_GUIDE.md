# AI_GUIDE: using an AI assistant on Binnit

Binnit is designed to be AI-assisted — that's part of the point of
writing hardware as code. This doc is for whoever is prompting the
assistant (you), not for the assistant to follow unsupervised. It covers
how to prompt well, what to verify before trusting the output, and the
specific ways an AI assistant tends to go wrong on a project like this.

If you only read one section, read [Never invent a dimension](#never-invent-a-dimension-the-failure-mode-to-watch-for).

## Why this doc exists

An AI assistant is good at producing plausible-looking numbers. "Plausible"
is exactly the problem: a wall that's 3.2mm instead of 3.0mm, or a fillet
radius nobody decided, will look completely normal in a generated STL and
still be wrong — wrong enough that a part doesn't fit, or two generators
disagree, or a dimension silently diverges from what's recorded in
`params.py`. CAD review by eyeballing a render won't catch this reliably.
The workflow below exists to catch it structurally instead.

## Never invent a dimension (the failure mode to watch for)

The single most important instruction to give any AI assistant working
on this repo — put it in your prompt explicitly, every time, even though
it's also written here and in `CONTRIBUTING.md`:

> Never invent or guess a dimension. If a value isn't already in
> `params/params.py`, or isn't clearly stated in the task, don't make one
> up to fill the gap — stop and ask, or add it as an `OpenParameter` with
> a comment explaining what's undecided.

Concretely, watch for the assistant:
- Filling in a fillet radius, chamfer, clearance, or wall thickness "to
  make it look right" when none was specified.
- Picking a rounding rule (floor/round/ceil) for a derived value without
  saying so, when the brief or `DESIGN.md` left that rule open (this
  already happened once in this repo — see `SIZES["L"]`/`SIZES["XL"]`
  `default_depth_units`, still `OpenParameter`).
- "Helpfully" resolving an `OpenParameter` by choosing a number instead of
  surfacing the question to you.
- Copying a number pattern it's seen from Gridfinity/Vault-style designs
  because it's a common convention, rather than from this repo's own
  `params.py` or your explicit answer.

None of these are hypothetical — they're the default failure mode of an
assistant trying to be helpful and complete a task without pausing. The
`OpenParameter` sentinel in `params.py` exists specifically to make this
failure loud (`OpenParameterError`) instead of silent, but that only
helps if new code keeps using it correctly rather than working around it.

## How to prompt well

- **Point at `params.py` and `DESIGN.md`, not just a description of the
  part.** "Add a fillet to the drawer box" is underspecified; "add a
  fillet to the drawer box using a new `DRAWER_BOX_FILLET_RADIUS_MM`
  constant you add to `params.py` — ask me for the radius, don't guess
  it" gives the assistant the actual decision to surface.
- **Ask for the provenance tag on every new constant.** `params.py`'s
  tagging scheme (STATED / MEASURED / ASSUMPTION / INFERRED / STARTING /
  FORMULA / OPEN) only works if it's kept up for new values too. If the
  assistant adds a number without one, ask which tag applies before
  merging.
- **Ask it to run the tests, not just write code.** `pytest tests/ -v`
  and `python src/<generator>.py` are cheap; an assistant that writes a
  generator and never runs it will miss the kind of mismatch the fit
  tests exist to catch (see `tests/test_drawer_box.py`'s bounding-box
  check for an example of the kind of claim to verify, not assume).
- **Ask for small, single-purpose diffs**, same as the human contributor
  guidance in `CONTRIBUTING.md`. An assistant asked to "scaffold the next
  piece" tends to over-deliver (extra features, speculative generality);
  a request scoped to one generator, one test, one doc section is easier
  to review and easier to revert if something's off.
- **If you're not sure the assistant has read the current `params.py`**,
  say so and ask it to re-read before changing anything dimensional.
  Context can go stale across a long session.

## What to verify before trusting the output

Before merging anything an AI assistant wrote for this repo:

1. **Every new number in `params.py` has a provenance comment**, and
   that comment is actually true (a "STATED" value should trace to
   something you or the brief actually stated — not to the assistant's
   own earlier inference).
2. **No bare numeric literal appears in `/src`** that isn't either
   imported from `params.py` or a pure geometric/loop constant (like `2`
   for "both sides," not a dimension in mm).
3. **The generator was actually run**, and its output bounding box (or
   another concrete property) was checked against what `params.py`
   implies — not just "the code looks right." Ask to see the check, or
   run it yourself.
4. **Tests pass, including on CI**, not just locally — `tests/` is meant
   to be the thing you trust over a visual read of generated code.
5. **If an `OpenParameter` was touched**, confirm it was either (a) left
   alone, (b) replaced with a real decision you actually made and that's
   now documented with a provenance comment, or (c) narrowed/split into
   a more specific open question — never silently resolved to a number
   nobody decided.
6. **Licensing**: hardware-shaped changes (geometry, generated designs)
   are CERN-OHL-P-2.0; code-shaped changes (generator/tooling/CI) are
   MIT. If the assistant pulled in a reference pattern from elsewhere
   (a common Gridfinity/Vault convention, a StackOverflow snippet), make
   sure it was reimplemented to Binnit's own numbers/structure, not
   copied — see `CONTRIBUTING.md`'s licensing section.

## When the assistant should stop and ask

Tell it to stop and ask you, rather than proceed, whenever it hits:
- A dimension not already in `params.py` and not stated in your prompt.
- A rounding/tie-breaking choice with no stated rule.
- A conflict between two stated facts (e.g. a per-floor formula that
  doesn't reconcile with a separately-stated total — `params.py`'s
  4-floor case numbers are a real example of this already present in the
  repo, deliberately kept as two separate stated facts rather than
  forced to agree).
- Anything that would require loosening or removing an existing test
  (fit or envelope) to pass — that's a sign the change needs a real
  decision from you, not a code fix.
