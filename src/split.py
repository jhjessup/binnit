"""
Splitting oversized parts to fit the print bed.

The design brief says a part larger than the print envelope is "split on
grid lines" but doesn't say which grid. DECIDED: the 42 mm internal grid
(params.GRID_PITCH_MM, aliased as params.SPLIT_GRID_PITCH_MM), not the
164 mm bay pitch — a small bed (e.g. a Voron Zero's 120x120 mm) can't fit
even one whole bay pitch in a single piece, so only the finer internal
grid is useful across the range of beds this project targets.
split_to_fit() defaults grid_pitch_mm to params.SPLIT_GRID_PITCH_MM but
still accepts an override, for experimenting with a different pitch.

What joins two split halves back together after printing is also
DECIDED: a repeating chevron ("zigzag finger joint") cut into the split
plane itself, rather than a flat butt cut — see params.SPLIT_JOINT_TYPE
and friends for the dimensions and reasoning. It self-aligns the two
halves on straight-on contact (no sliding together, unlike the stacking
interlock's dovetail — appropriate since this joint is meant to be
glued) and multiplies the bonded surface area versus a flat cut. Pass
`joint=False` to split_to_fit() for the old flat-cut behavior instead.

Scope note: chevron teeth are applied independently per axis, in two
sequential passes (split X, then split Y on each resulting column). A
part that needs splitting on both axes gets chevron teeth on every cut,
but the four-piece corner where an X cut crosses a Y cut is not
specially mitered — each piece simply carries whichever boundary each
pass gave it. That's a known cosmetic/structural approximation, not a
correctness bug: every cut is still a true boolean split of the real
part, pieces still partition it exactly (minus the deliberate clearance
gap), and every piece still fits the bed.
"""

import math
from dataclasses import dataclass

from build123d import Part, Polyline, extrude, make_face

from params import params as P


class SplitError(RuntimeError):
    """Raised when a part cannot be split to fit the bed on the given grid."""


@dataclass
class SplitPiece:
    part: Part
    grid_index: tuple[int, int]        # (ix, iy) cell coordinates, 0-based
    original_offset: tuple[float, float, float]
    # ^ (x, y, z) this piece's new local origin (its bbox min) occupied in
    #   the original, unsplit part's coordinate frame — what you'd add
    #   back to reassemble the pieces positionally.

    @property
    def label(self) -> str:
        return f"x{self.grid_index[0]}y{self.grid_index[1]}"


def _choose_cut_positions(size_mm: float, pitch_mm: float, bed_mm: float,
                           axis_label: str) -> list[float]:
    """Pick the minimal set of grid-line positions (multiples of
    pitch_mm, measured from 0) that split [0, size_mm] into pieces each
    no larger than bed_mm. Greedy: from each cut, jump to the farthest
    reachable grid line."""
    if size_mm <= bed_mm:
        return []

    candidates = []
    n = 1
    while n * pitch_mm < size_mm - 1e-9:
        candidates.append(n * pitch_mm)
        n += 1

    cuts: list[float] = []
    start = 0.0
    while size_mm - start > bed_mm + 1e-9:
        reachable = [c for c in candidates if start < c <= start + bed_mm + 1e-9]
        if not reachable:
            raise SplitError(
                f"{axis_label}: cannot split {size_mm:.1f} mm to fit a "
                f"{bed_mm:.1f} mm bed on a {pitch_mm:.1f} mm grid — no grid "
                f"line falls within reach of the previous cut at "
                f"{start:.1f} mm. The grid is too coarse for this bed size."
            )
        cuts.append(max(reachable))
        start = cuts[-1]

    return cuts


def _boundary_points(axis_val: float, shift: float, other_lo: float,
                      other_hi: float, zigzag: bool, feature_size: float,
                      pitch: float) -> list[tuple[float, float]]:
    """Points tracing a boundary line (axis_coord, other_coord) from
    other_lo to other_hi. Flat at `axis_val + shift` if not zigzag;
    otherwise a triangle wave of the given amplitude/pitch centered on
    `axis_val + shift`."""
    center = axis_val + shift
    if not zigzag or feature_size <= 0:
        return [(center, other_lo), (center, other_hi)]

    pts = [(center, other_lo)]
    half_pitch = pitch / 2.0
    o = other_lo
    n = 0
    while o < other_hi - 1e-9:
        nxt = min(o + half_pitch, other_hi)
        sign = 1.0 if n % 2 == 0 else -1.0
        pts.append((center + sign * feature_size, nxt))
        o = nxt
        n += 1
    return pts


def _region_solid(axis: str, lo_val: float, hi_val: float, other_lo: float,
                   other_hi: float, lo_is_cut: bool, hi_is_cut: bool,
                   feature_size: float, pitch: float, clearance: float,
                   z0: float, zheight: float) -> Part:
    """A prism covering the region between `lo_val` and `hi_val` along
    `axis` ("X" or "Y"), spanning [other_lo, other_hi] on the other axis
    and [z0, z0+zheight] in Z. Boundaries flagged `*_is_cut` get a
    chevron zigzag (shifted inward by half the clearance, so two
    neighboring pieces built from the same nominal boundary leave a gap
    of `clearance` between them); the rest are flat."""
    lo_shift = clearance / 2.0 if lo_is_cut else 0.0   # shrink inward from below
    hi_shift = -clearance / 2.0 if hi_is_cut else 0.0  # shrink inward from above

    lo_pts = _boundary_points(lo_val, lo_shift, other_lo, other_hi,
                               lo_is_cut, feature_size, pitch)
    hi_pts = _boundary_points(hi_val, hi_shift, other_lo, other_hi,
                               hi_is_cut, feature_size, pitch)

    poly_axis_other = lo_pts + list(reversed(hi_pts))

    if axis == "X":
        poly_xy = [(a, o) for (a, o) in poly_axis_other]
    else:  # axis == "Y": a is the Y coordinate, o is the X coordinate
        poly_xy = [(o, a) for (a, o) in poly_axis_other]

    face = make_face(Polyline(*poly_xy, close=True))
    solid = extrude(face, amount=zheight)
    return solid.translate((0, 0, z0))


def _split_along_axis(part: Part, axis: str, cut_positions_abs: list[float],
                       feature_size: float, pitch: float, clearance: float,
                       joint: bool) -> list[Part]:
    if not cut_positions_abs:
        return [part]

    bb = part.bounding_box()
    if axis == "X":
        lo_overall, hi_overall = bb.min.X, bb.max.X
        other_lo, other_hi = bb.min.Y, bb.max.Y
    else:
        lo_overall, hi_overall = bb.min.Y, bb.max.Y
        other_lo, other_hi = bb.min.X, bb.max.X

    other_margin = 5.0
    other_lo -= other_margin
    other_hi += other_margin

    outer_margin = (hi_overall - lo_overall) + 1000.0
    boundaries = [lo_overall - outer_margin] + list(cut_positions_abs) + \
        [hi_overall + outer_margin]

    z_margin = 1.0
    z0 = bb.min.Z - z_margin
    zheight = bb.size.Z + 2 * z_margin

    pieces = []
    for i in range(len(boundaries) - 1):
        lo_val, hi_val = boundaries[i], boundaries[i + 1]
        lo_is_cut = joint and i > 0
        hi_is_cut = joint and i < len(boundaries) - 2
        solid = _region_solid(axis, lo_val, hi_val, other_lo, other_hi,
                               lo_is_cut, hi_is_cut, feature_size, pitch,
                               clearance, z0, zheight)
        piece = part & solid
        if piece.volume > 1e-9:
            pieces.append(piece)
    return pieces


def split_to_fit(part: Part, grid_pitch_mm: float | None = None,
                  bed_xy_mm: float | None = None, joint: bool = True,
                  feature_size_mm: float | None = None,
                  angle_deg: float | None = None,
                  clearance_mm: float | None = None) -> list[SplitPiece]:
    """
    Split `part` on lines spaced `grid_pitch_mm` apart (measured from its
    own bounding-box minimum corner) so that every returned piece's X/Y
    footprint fits within `bed_xy_mm` (default: params.PRINT_BED_USABLE_XY_MM).

    `grid_pitch_mm` defaults to params.SPLIT_GRID_PITCH_MM (the 42 mm
    internal grid — see module docstring for why that one, not the bay
    pitch).

    By default (`joint=True`) each internal cut is a repeating chevron
    joint — see params.SPLIT_JOINT_* for the dimensions and the module
    docstring for the reasoning — sized from `feature_size_mm`/`angle_deg`
    (defaulting to params.SPLIT_JOINT_FEATURE_SIZE_MM /
    params.SPLIT_JOINT_ANGLE_DEG) with a `clearance_mm` gap (default
    params.SPLIT_JOINT_CLEARANCE_MM) between mating faces. Pass
    `joint=False` for a plain flat butt cut instead.

    Only X and Y are split — Z is left alone, same as the envelope check
    in src/envelope.py (the brief gives no Z/gantry limit to split against).

    If the part already fits, returns a single SplitPiece wrapping the
    unmodified part at grid_index (0, 0).

    Raises SplitError if `grid_pitch_mm` doesn't divide the oversize
    cleanly enough to produce bed-sized pieces (e.g. the grid is too
    coarse for the bed), or if a resulting piece still doesn't fit.
    """
    grid_pitch_mm = P.SPLIT_GRID_PITCH_MM if grid_pitch_mm is None else grid_pitch_mm
    bed_xy_mm = P.PRINT_BED_USABLE_XY_MM if bed_xy_mm is None else bed_xy_mm
    feature_size_mm = (P.SPLIT_JOINT_FEATURE_SIZE_MM if feature_size_mm is None
                        else feature_size_mm)
    angle_deg = P.SPLIT_JOINT_ANGLE_DEG if angle_deg is None else angle_deg
    clearance_mm = (P.SPLIT_JOINT_CLEARANCE_MM if clearance_mm is None
                     else clearance_mm)

    if joint:
        pitch_mm = P.chevron_pitch_mm(float(feature_size_mm), float(angle_deg))
    else:
        pitch_mm, feature_size_mm, clearance_mm = 0.0, 0.0, 0.0

    bb = part.bounding_box()
    size_x, size_y = bb.size.X, bb.size.Y

    cuts_x_local = _choose_cut_positions(size_x, grid_pitch_mm, bed_xy_mm, "X")
    cuts_y_local = _choose_cut_positions(size_y, grid_pitch_mm, bed_xy_mm, "Y")
    cuts_x_abs = [bb.min.X + c for c in cuts_x_local]
    cuts_y_abs = [bb.min.Y + c for c in cuts_y_local]

    x_pieces = _split_along_axis(part, "X", cuts_x_abs, feature_size_mm,
                                  pitch_mm, clearance_mm, joint)

    raw_pieces: list[Part] = []
    for xp in x_pieces:
        raw_pieces.extend(_split_along_axis(xp, "Y", cuts_y_abs, feature_size_mm,
                                             pitch_mm, clearance_mm, joint))

    pieces: list[SplitPiece] = []
    for raw in raw_pieces:
        raw_bb = raw.bounding_box()
        cx = (raw_bb.min.X + raw_bb.max.X) / 2.0
        cy = (raw_bb.min.Y + raw_bb.max.Y) / 2.0
        ix = sum(1 for c in cuts_x_abs if c <= cx)
        iy = sum(1 for c in cuts_y_abs if c <= cy)

        offset = (raw_bb.min.X, raw_bb.min.Y, raw_bb.min.Z)
        located = raw.translate((-raw_bb.min.X, -raw_bb.min.Y, 0))
        located_bb = located.bounding_box()

        if (located_bb.size.X > bed_xy_mm + 1e-3 or
                located_bb.size.Y > bed_xy_mm + 1e-3):
            raise SplitError(
                f"Internal error: piece ({ix},{iy}) footprint "
                f"{located_bb.size.X:.1f} x {located_bb.size.Y:.1f} mm still "
                f"exceeds the {bed_xy_mm:.1f} mm bed after splitting."
            )

        pieces.append(SplitPiece(part=located, grid_index=(ix, iy),
                                  original_offset=offset))

    return pieces
