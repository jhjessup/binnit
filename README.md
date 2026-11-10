# Binnit

Binnit is an open, parametric, 3D-printable modular storage system
(drawers + cases + mounting), designed as code: version-controlled,
branchable, and AI-assisted.

It is its own design — not a copy or derivative of USSA Vault or of the
Gridfinity-derived CC BY-NC-SA ecosystems. All geometry is generated from a
single parameter source so the design can be forked, resized, and audited.

**Status:** scaffold stage. See [docs/DESIGN.md](docs/DESIGN.md) for the
full design spec, including an explicit list of open/undecided values.

## Why "designed as code"

- All dimensions live in one place: [`params/params.py`](params/params.py).
- Geometry is generated with [build123d](https://github.com/gumyr/build123d)
  (Python), exported to STEP/STL — never hand-modeled, never hand-edited.
- Every PR rebuilds the STL set in CI and attaches it as a build artifact,
  so a reviewer can see the physical result of a code change without
  owning a slicer locally.
- Because it's code, it's forkable/branchable the way hardware files
  normally aren't: resize a bay, change wall thickness, retarget a
  different printer bed, and the whole family of parts updates together.

## Repo layout

```
/src       parametric modules (drawer box, case, insert, interlock)
/params    shared dimensions — the single source of truth
/tests     fit and envelope checks
/tools     bench.html — offline STL viewer for visually checking a build
/docs      DESIGN.md, CONTRIBUTING.md, AI_GUIDE.md
/.github   workflows, issue and PR templates
```

Generated STL/STEP files are never committed; CI builds and attaches them
per PR.

## Grid system (quick reference)

42 mm Gridfinity-compatible internal pitch, 7 mm height unit, 164 mm bay
pitch. Case outside widths add exactly: S + S = M, S + M = L, M + M = XL.
Full derivation and every placeholder value is in
[docs/DESIGN.md](docs/DESIGN.md).

| Size | Bays | Grid units wide | Case outside width |
|------|------|------------------|---------------------|
| S    | 1    | 3                | 164 mm              |
| M    | 2    | 6                | 328 mm               |
| L    | 3    | 10               | 492 mm               |
| XL   | 4    | 14               | 656 mm               |

## License

Binnit uses two licenses, split by what's being licensed:

- **Hardware** (the physical design: geometry definitions, generated
  part designs, CAD-adjacent docs) — [CERN-OHL-P-2.0](LICENSE-HARDWARE),
  a permissive open hardware license.
- **Code** (the Python generator, build scripts, CI, tooling) —
  [MIT](LICENSE-CODE).

See each file's header/location for which license applies; as a rule of
thumb, anything under `/src` and `/params` that defines or builds a
physical part is hardware-licensed, and anything that is purely tooling
(CI workflows, test harness, dev scripts) is code-licensed. See
[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for contribution terms.

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). If you're using an AI
assistant to contribute, also read [docs/AI_GUIDE.md](docs/AI_GUIDE.md) —
in particular: never invent a dimension; every unmeasured/undecided value
must be a named, flagged placeholder in `params/params.py`, not a guess.
