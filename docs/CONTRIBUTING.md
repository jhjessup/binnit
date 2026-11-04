# Contributing to Binnit

Binnit is a parametric design, written as code. The rules below exist to
keep it trustworthy as code: every dimension traceable, every change
small and reviewable, nothing guessed.

## The one rule that matters most

**Never invent a dimension.** If a value isn't stated, measured, or
decided and recorded with its provenance, it does not go into
[`params/params.py`](../params/params.py) as a number. It goes in as an
`OpenParameter(...)` sentinel (see that file's docstring), and gets a row
in [`DESIGN.md`](DESIGN.md)'s Open items table. Using an `OpenParameter`
anywhere raises `OpenParameterError` — if your change needs that value,
resolving the placeholder (with a real decision, documented) is part of
the change, not a follow-up.

This applies whether you're a human or an AI assistant. If you're using
AI to help, read [AI_GUIDE.md](AI_GUIDE.md) too — same rule, more detail
on how it goes wrong in practice.

## Where things live

```
/src       parametric modules (drawer box, case, insert, interlock)
/params    params.py — the single source of truth for every dimension
/tests     fit and envelope checks
/docs      DESIGN.md, CONTRIBUTING.md, AI_GUIDE.md
/.github   workflows, issue and PR templates
```

- A dimension lives in `params/params.py`, once. If you find yourself
  writing a number directly into a file under `/src`, stop — add (or
  reuse) a named constant/formula in `params.py` instead and import it.
- A generator under `/src` builds geometry from `params.py` values and
  nothing else. It should read as "assemble these named numbers," not
  "here is a box of width 134."
- A check under `/tests` verifies either fit (generated geometry matches
  what `params.py` says it should) or envelope (a part fits the usable
  print bed). Both are real, run-on-every-PR CI gates — not advisory.

## Licensing

Binnit is dual-licensed by what's being licensed, not by directory:

- **Hardware** — geometry definitions, generated part designs, and
  CAD-adjacent docs — [CERN-OHL-P-2.0](../LICENSE-HARDWARE).
- **Code** — the Python generator, build scripts, CI, tooling —
  [MIT](../LICENSE-CODE).

By contributing, you agree your contribution is licensed under whichever
of these applies to what you changed (hardware-shaped changes under
CERN-OHL-P-2.0, code-shaped changes under MIT). If a change is genuinely
both, say so in the PR description and we'll sort out attribution there.

Do not port or adapt geometry, dimensions, or code from USSA Vault
(licensed, not open) or from the Gridfinity-derived ecosystem
(CC BY-NC-SA, incompatible with this project's permissive licensing). If
you're starting from a measurement of a Vault part for reference, that's
fine and already how several of Binnit's own reference numbers in
`params.py` originated — but say so explicitly in the comment/PR
(`MEASURED (reference)`, per `params.py`'s provenance tags) and write the
geometry yourself to the resulting numbers. Don't copy a Vault/Gridfinity
STEP/STL or its code.

## Making a change

1. **Small commits.** One logical change per commit — a param change, a
   generator change, a test, a doc update. Don't bundle an unrelated
   cleanup into a dimension change; it makes the dimension change harder
   to review and revert independently.
2. **If you're resolving an OPEN item:** update `params.py` (replace the
   `OpenParameter(...)` with the real value and a provenance comment),
   remove its row from `DESIGN.md`'s Open items table, and say in the PR
   description how the value was decided (measured how, tested how,
   chosen why).
3. **If you're adding a new dimension that the brief/DESIGN.md doesn't
   cover:** same options as any other value — state it with a real
   number and provenance, or add it as `OpenParameter` and document why
   it's open. Don't leave it as a bare literal in a generator file.
4. **Run the checks locally before opening a PR:**
   ```
   python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
   .venv/bin/pytest tests/ -v
   .venv/bin/python src/drawer_box.py   # or whichever generator you touched
   ```
5. **Open the PR.** CI (`.github/workflows/build.yml`) re-runs the test
   suite, regenerates the STL(s), and attaches them as a build artifact
   so reviewers can look at the actual part without owning a slicer.
   CI fails hard if a part exceeds the usable print bed
   (`params.PRINT_BED_USABLE_XY_MM`) — that's by design, not a bug to
   route around; either make the part fit or split it on a grid line.
6. **Never commit generated STL/STEP files.** `.gitignore` already
   excludes them; if you see one staged, that's a sign something's
   generating output into a tracked path.

## Review expectations

A reviewer should be able to answer "where did this number come from?"
for every new or changed constant in `params.py` by reading the comment
next to it, without asking you. If they can't, that's a legitimate
request-changes, not nitpicking — it's the whole point of designing this
as code instead of as opaque CAD files.
