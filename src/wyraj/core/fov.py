"""Symmetric shadowcasting FOV.

Implementation of Albert Ford's symmetric shadowcasting
(https://www.albertford.com/shadowcasting/): floor tile B is visible from
floor tile A if and only if A is visible from B. Walls are additionally
revealed for aesthetics (wall visibility is not symmetric by design).
"""

from collections.abc import Callable, Iterator
from fractions import Fraction

# Quadrant transforms: (row, col) in quadrant space -> (dx, dy) offset.
_QUADRANTS: tuple[Callable[[int, int], tuple[int, int]], ...] = (
    lambda row, col: (col, -row),  # north
    lambda row, col: (col, row),  # south
    lambda row, col: (row, col),  # east
    lambda row, col: (-row, col),  # west
)


def _slope(row: int, col: int) -> Fraction:
    return Fraction(2 * col - 1, 2 * row)


def _round_ties_up(n: Fraction) -> int:
    return int((n + Fraction(1, 2)).__floor__())


def _round_ties_down(n: Fraction) -> int:
    return int((n - Fraction(1, 2)).__ceil__())


def compute_fov(
    origin: tuple[int, int],
    radius: int,
    is_blocking: Callable[[int, int], bool],
) -> set[tuple[int, int]]:
    ox, oy = origin
    visible: set[tuple[int, int]] = {origin}
    radius_sq = radius * radius

    for transform in _QUADRANTS:

        def to_world(row: int, col: int) -> tuple[int, int]:
            dx, dy = transform(row, col)  # noqa: B023 — consumed within the same iteration
            return ox + dx, oy + dy

        def blocked(row: int, col: int) -> bool:
            return is_blocking(*to_world(row, col))

        def reveal(row: int, col: int) -> None:
            x, y = to_world(row, col)
            if (x - ox) ** 2 + (y - oy) ** 2 <= radius_sq:
                visible.add((x, y))

        def tiles_in_row(depth: int, start: Fraction, end: Fraction) -> Iterator[int]:
            min_col = _round_ties_up(depth * start)
            max_col = _round_ties_down(depth * end)
            yield from range(min_col, max_col + 1)

        def scan(depth: int, start_slope: Fraction, end_slope: Fraction) -> None:
            if depth > radius:
                return
            prev_was_wall: bool | None = None
            for col in tiles_in_row(depth, start_slope, end_slope):
                is_wall = blocked(depth, col)
                is_symmetric = depth * start_slope <= col <= depth * end_slope
                if is_wall or is_symmetric:
                    reveal(depth, col)
                if prev_was_wall is True and not is_wall:
                    start_slope = _slope(depth, col)
                if prev_was_wall is False and is_wall:
                    scan(depth + 1, start_slope, _slope(depth, col))
                prev_was_wall = is_wall
            if prev_was_wall is False:
                scan(depth + 1, start_slope, end_slope)

        scan(1, Fraction(-1), Fraction(1))

    return visible
