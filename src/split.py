"""
Splitting oversized parts to fit the print bed.

The design brief says a part larger than the print envelope is "split on
grid lines" but doesn't say which grid — the 42 mm internal pitch
(params.GRID_PITCH_MM) or the 164 mm bay pitch (params.BAY_PITCH_MM),
where the interlock connectors already sit. That's recorded as OPEN
(params.SPLIT_GRID_PITCH_MM) rather than guessed, so split_to_fit() below
takes grid_pitch_mm as a *required* argument: pass params.SPLIT_GRID_PITCH_MM
as a default and it will raise OpenParameterError the moment it's used,
the same way every other OPEN value in this repo does.

What (if anything) joins two split halves back together after printing is
also undecided (params.SPLIT_JOINT_TYPE / SPLIT_JOINT_FEATURE_SIZE_MM).
The geometry produced here is a flat butt cut with no joint feature; this
module does not add one.
"""

from dataclasses import dataclass

from build123d import Align, Box, Part

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


def split_to_fit(part: Part, grid_pitch_mm: float,
                  bed_xy_mm: float | None = None) -> list[SplitPiece]:
    """
    Split `part` on lines spaced `grid_pitch_mm` apart (measured from its
    own bounding-box minimum corner) so that every returned piece's X/Y
    footprint fits within `bed_xy_mm` (default: params.PRINT_BED_USABLE_XY_MM).

    Only X and Y are split — Z is left alone, same as the envelope check
    in src/envelope.py (the brief gives no Z/gantry limit to split against).

    If the part already fits, returns a single SplitPiece wrapping the
    unmodified part at grid_index (0, 0).

    Raises SplitError if `grid_pitch_mm` doesn't divide the oversize
    cleanly enough to produce bed-sized pieces (e.g. the grid is too
    coarse). Raises OpenParameterError (not SplitError) if grid_pitch_mm
    itself is params.SPLIT_GRID_PITCH_MM, i.e. the caller didn't supply a
    real decision.
    """
    bed_xy_mm = P.PRINT_BED_USABLE_XY_MM if bed_xy_mm is None else bed_xy_mm

    bb = part.bounding_box()
    size_x, size_y = bb.size.X, bb.size.Y

    # Force any OpenParameter to raise now, with its real message, rather
    # than deep inside arithmetic below.
    float(grid_pitch_mm)

    cuts_x = _choose_cut_positions(size_x, grid_pitch_mm, bed_xy_mm, "X")
    cuts_y = _choose_cut_positions(size_y, grid_pitch_mm, bed_xy_mm, "Y")

    bounds_x = [0.0] + cuts_x + [size_x]
    bounds_y = [0.0] + cuts_y + [size_y]

    z_margin = 1.0
    full_z = bb.size.Z + 2 * z_margin
    z_start = bb.min.Z - z_margin

    pieces: list[SplitPiece] = []
    for iy in range(len(bounds_y) - 1):
        y0, y1 = bounds_y[iy], bounds_y[iy + 1]
        for ix in range(len(bounds_x) - 1):
            x0, x1 = bounds_x[ix], bounds_x[ix + 1]

            window = Box(x1 - x0, y1 - y0, full_z,
                         align=(Align.MIN, Align.MIN, Align.MIN))
            window = window.translate((bb.min.X + x0, bb.min.Y + y0, z_start))

            piece = part & window
            if piece.volume <= 1e-9:
                continue  # this cell is entirely outside the part's material

            piece_bb = piece.bounding_box()
            piece = piece.translate((-piece_bb.min.X, -piece_bb.min.Y, 0))

            if piece_bb.size.X > bed_xy_mm + 1e-6 or piece_bb.size.Y > bed_xy_mm + 1e-6:
                raise SplitError(
                    f"Internal error: piece ({ix},{iy}) footprint "
                    f"{piece_bb.size.X:.1f} x {piece_bb.size.Y:.1f} mm still "
                    f"exceeds the {bed_xy_mm:.1f} mm bed after splitting."
                )

            pieces.append(SplitPiece(
                part=piece,
                grid_index=(ix, iy),
                original_offset=(piece_bb.min.X, piece_bb.min.Y, piece_bb.min.Z),
            ))

    return pieces
