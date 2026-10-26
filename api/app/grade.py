"""How hard a day is for a person: the most clues they must combine at any step."""

from dataclasses import dataclass
from itertools import combinations
from typing import TYPE_CHECKING

import numpy as np

from app.board import DESKS, Board, Desk
from app.clues import BOARDS, NoMoreThan, Total

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from app.clues import Clue, Mask
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
        step, forced = _step(clues, [m[alive] for m in masks], BOARDS[alive], declared)
        steps.append(step)
        new = sorted(forced)
        declared |= forced
    return Grade(tuple(steps))


def _step(
    clues: list[Clue],
    masks: list[Mask],
    boards: NDArray[np.uint32],
    declared: set[Desk],
) -> tuple[Step, set[Desk]]:
    wide = [isinstance(c, Total | NoMoreThan) for c in clues]
    sizes = [*range(1, min(MOST, len(clues)) + 1)]
    if len(clues) > MOST:
        sizes.append(len(clues))  # past MOST, everything at once
    for k in sizes:
        for whole_board in (False, True):
            forced: set[Desk] = set()
            for subset in combinations(range(len(clues)), k):
                if any(wide[i] for i in subset) != whole_board:
                    continue
                alive = np.logical_and.reduce([masks[i] for i in subset])
                forced |= _forced(boards[alive], declared)
            if forced:
                return Step(min(k, MOST), len(forced), whole_board), forced
    msg = "no clue forces anyone: the day can't be solved without guessing"
    raise ValueError(msg)


def _forced(boards: NDArray[np.uint32], declared: set[Desk]) -> set[Desk]:
    always = int(np.bitwise_and.reduce(boards))
    ever = int(np.bitwise_or.reduce(boards))
    return {
        d
        for i, d in enumerate(DESKS)
        if d not in declared and (always >> i & 1 or not ever >> i & 1)
    }


def _bits(desks: set[Desk] | frozenset[Desk]) -> int:
    return sum(1 << DESKS.index(d) for d in desks)
