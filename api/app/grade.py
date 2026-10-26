"""How hard a day is for a person: the most clues they must combine at any step."""

from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING

import numpy as np

from app.board import DESKS, Board, Desk
from app.clues import BOARDS, NoMoreThan, Total, settled

if TYPE_CHECKING:
    from collections.abc import Container, Iterator, Sequence

    from app.clues import Boards, Clue, Mask, State
    from app.week import Day, Difficulty

# Combining more than this many clues counts as one "3+" step.
MOST = 3


@dataclass(frozen=True)
class Step:
    hardness: int  # the fewest clues that force someone; MOST means MOST or more
    breadth: int  # how many coworkers those clues force
    whole_board: bool  # only a whole-board clue would do


@dataclass(frozen=True)
class Grade:
    steps: tuple[Step, ...]

    @property
    def difficulty(self) -> Difficulty:
        if any(s.hardness >= MOST or s.whole_board for s in self.steps):
            return "Hard"
        return "Medium" if any(s.hardness > 1 for s in self.steps) else "Easy"


def grade(board: Board, day: Day) -> Grade:
    """Replay a day greedily, declaring whatever the fewest clues force each time.

    Local clues are tried before whole-board ones at each size, the way a person
    looks at the desks a clue names before counting the whole office.
    """
    declared = {day.start}
    clues: list[Clue] = []
    masks: list[Mask] = []
    steps: list[Step] = []
    new = [day.start]
    while len(declared) < len(DESKS):
        for desk in new:
            if clue := day.reveal(desk).clue:
                clues.append(clue)
                masks.append(clue.mask(board))
        known = _bits(declared)
        alive = np.flatnonzero(
            (BOARDS & np.uint32(known)) == _bits(declared & day.sick)
        )
        step, forced = next_step(
            clues, [m[alive] for m in masks], BOARDS[alive], declared
        )
        steps.append(step)
        new = sorted(forced)
        declared |= forced
    return Grade(tuple(steps))


def next_step(
    clues: list[Clue],
    masks: list[Mask],
    boards: Boards,
    declared: Container[Desk],
) -> tuple[Step, set[Desk]]:
    # Everyone forced at the first size and reach that forces anyone, not just by
    # the first subset there; the search stops at the end of that level.
    level: tuple[int, bool] | None = None
    forced: set[Desk] = set()
    for k, whole_board, _, more in _subsets(clues, masks, boards, declared):
        if level and level != (k, whole_board):
            break
        if more:
            level = k, whole_board
            forced |= more
    if level is None:
        msg = "no clue forces anyone: the day can't be solved without guessing"
        raise ValueError(msg)
    k, whole_board = level
    return Step(min(k, MOST), len(forced), whole_board), forced


def _subsets(
    clues: list[Clue],
    masks: list[Mask],
    boards: Boards,
    declared: Container[Desk],
) -> Iterator[tuple[int, bool, tuple[int, ...], set[Desk]]]:
    """Every subset of clues the way a person tries them, and whom it forces.

    Fewest clues first, local before whole-board. Lazy, so a caller stops the
    search where it likes; a subset that forces no one yields an empty set.
    """
    wide = [isinstance(c, Total | NoMoreThan) for c in clues]
    sizes = [*range(1, min(MOST, len(clues)) + 1)]
    if len(clues) > MOST:
        sizes.append(len(clues))  # past MOST, everything at once
    for k in sizes:
        for whole_board in (False, True):
            for subset in combinations(range(len(clues)), k):
                if any(wide[i] for i in subset) != whole_board:
                    continue
                alive = np.logical_and.reduce([masks[i] for i in subset])
                yield k, whole_board, subset, set(settled(boards[alive], declared))


def hint(
    board: Board, day: Day, steps: Sequence[tuple[Desk, State]]
) -> tuple[list[Desk], Desk]:
    """The fewest revealed clues that force someone, and the first they force.

    `steps` must already be accepted: the hint is computed from the solution.
    """
    declared = {day.start, *(desk for desk, _ in steps)}
    speakers = [d for d in DESKS if d in declared and day.reveal(d).clue]
    alive = BOARDS[(BOARDS & np.uint32(_bits(declared))) == _bits(declared & day.sick)]
    clues = [c for d in speakers if (c := day.reveal(d).clue)]
    masks = [c.mask(board, alive) for c in clues]
    found = (
        (subset, forced)
        for _, _, subset, forced in _subsets(clues, masks, alive, declared)
        if forced
    )
    if (first := next(found, None)) is None:  # pragma: no cover (a solvable day)
        msg = "no clue forces anyone"
        raise ValueError(msg)
    subset, forced = first
    return [speakers[i] for i in subset], min(forced, key=DESKS.index)


def _bits(desks: set[Desk] | frozenset[Desk]) -> int:
    return sum(1 << DESKS.index(d) for d in desks)
