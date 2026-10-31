"""How hard a day is for a person: the most clues they must combine at any step."""

from dataclasses import dataclass, field
from itertools import combinations
from typing import TYPE_CHECKING

import numpy as np

from app.board import DESKS, Board, Desk
from app.clues import BOARDS, EVERYONE, WIDE, fits, settled

if TYPE_CHECKING:
    from collections.abc import Container, Iterator, Sequence

    from app.clues import Boards, Clue, Mask
    from app.week import Call, Day, Difficulty

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


@dataclass(frozen=True)
class Suspects:
    """What the office manager knows of the fibber: whose clues could be lies.

    The default is a day with no fibber: every clue is true.
    """

    liars: frozenset[int] = frozenset()  # clues by someone who could be the fibber
    # Per board: the fibber could be someone yet to speak.
    unspoken: Mask | bool = field(default=True, compare=False)
    caught: bool = True  # nobody left to call BS on


def suspects(  # noqa: PLR0913
    fibber: Desk | None,
    sick: Container[Desk],
    speakers: Sequence[Desk],
    boards: Boards,
    declared: Container[Desk],
    *,
    caught: bool,
) -> Suspects:
    """What's known of the fibber once these coworkers have spoken.

    Before BS is called, any sick speaker could be the fibber, or someone not yet
    declared. After, only the fibber's clue is false.
    """
    if fibber is None:
        return Suspects()
    if caught:  # BS can only be called on someone who has spoken
        return Suspects(
            liars=frozenset(i for i, d in enumerate(speakers) if d == fibber),
            unspoken=False,
        )
    undeclared = EVERYONE & ~_bits({d for d in DESKS if d in declared})
    return Suspects(
        liars=frozenset(i for i, d in enumerate(speakers) if d in sick),
        unspoken=(boards & np.uint32(undeclared)) != 0,
        caught=False,
    )


def grade(board: Board, day: Day) -> Grade:
    """Replay a day greedily, declaring whatever the fewest clues force each time.

    Local clues are tried before whole-board ones at each size, the way a person
    looks at the desks a clue names before counting the whole office. On Overtime,
    calling BS on the fibber is a step like any other.
    """
    declared = {day.start}
    caught = not day.overtime
    speakers: list[Desk] = []
    steps: list[Step] = []
    new = [day.start]
    while len(declared) < len(DESKS) or not caught:
        speakers += [d for d in new if day.reveal(d).clue]
        alive = BOARDS[
            (BOARDS & np.uint32(_bits(declared))) == _bits(declared & day.sick)
        ]
        clues = [c for d in speakers if (c := day.reveal(d).clue)]
        step, forced, fibber = next_step(
            clues,
            [c.mask(board, alive) for c in clues],
            alive,
            declared,
            suspects(day.fibber, day.sick, speakers, alive, declared, caught=caught),
        )
        steps.append(step)
        new = sorted(forced)
        declared |= forced
        caught = caught or fibber is not None
    return Grade(tuple(steps))


def next_step(
    clues: list[Clue],
    masks: list[Mask],
    boards: Boards,
    declared: Container[Desk],
    fibber: Suspects = Suspects(),  # noqa: B008 (frozen, so safe to share)
) -> tuple[Step, set[Desk], int | None]:
    """Everyone forced at the first size and reach that forces anyone, and the
    clue caught lying there, if any; the search stops at the end of that level."""
    level: tuple[int, bool] | None = None
    forced: set[Desk] = set()
    caught: int | None = None
    for k, whole_board, _, more, liar in _subsets(
        clues, masks, boards, declared, fibber
    ):
        if level and level != (k, whole_board):
            break
        if more or liar is not None:
            level = k, whole_board
            forced |= more
            caught = liar if liar is not None else caught
    if level is None:
        msg = "no clue forces anyone: the day can't be solved without guessing"
        raise ValueError(msg)
    k, whole_board = level
    breadth = len(forced) + (caught is not None)
    return Step(min(k, MOST), breadth, whole_board), forced, caught


def _subsets(
    clues: list[Clue],
    masks: list[Mask],
    boards: Boards,
    declared: Container[Desk],
    fibber: Suspects,
) -> Iterator[tuple[int, bool, tuple[int, ...], set[Desk], int | None]]:
    """Every subset of clues the way a person tries them, whom it forces, and
    which clue it catches lying.

    Fewest clues first, local before whole-board. Lazy, so a caller stops the
    search where it likes; a subset that forces no one yields an empty set.
    """
    wide = [isinstance(c, WIDE) for c in clues]
    sizes = [*range(1, min(MOST, len(clues)) + 1)]
    if len(clues) > MOST:
        sizes.append(len(clues))  # past MOST, everything at once
    for k in sizes:
        for whole_board in (False, True):
            for subset in combinations(range(len(clues)), k):
                if any(wide[i] for i in subset) != whole_board:
                    continue
                # The fibber is one of these speakers, or anyone else who could be.
                alive = fits(
                    [masks[i] for i in subset],
                    [i in fibber.liars for i in subset],
                    elsewhere=fibber.unspoken
                    | any(i not in subset for i in fibber.liars),
                )
                liar = (
                    None
                    if fibber.caught
                    else next(
                        (
                            i
                            for i in subset
                            if i in fibber.liars and not masks[i][alive].any()
                        ),
                        None,
                    )
                )
                yield (
                    k,
                    whole_board,
                    subset,
                    set(settled(boards[alive], declared)),
                    liar,
                )


def hint(
    board: Board, day: Day, steps: Sequence[tuple[Desk, Call]]
) -> tuple[list[Desk], Desk]:
    """The fewest revealed clues that force someone, and the first they force.

    On Overtime that can be the fibber, once those clues catch them lying.
    `steps` must already be accepted: the hint is computed from the solution.
    """
    declared = {day.start, *(desk for desk, call in steps if call != "fibber")}
    caught = not day.overtime or any(call == "fibber" for _, call in steps)
    speakers = [d for d in DESKS if d in declared and day.reveal(d).clue]
    alive = BOARDS[(BOARDS & np.uint32(_bits(declared))) == _bits(declared & day.sick)]
    clues = [c for d in speakers if (c := day.reveal(d).clue)]
    masks = [c.mask(board, alive) for c in clues]
    found = (
        (subset, forced, liar)
        for _, _, subset, forced, liar in _subsets(
            clues,
            masks,
            alive,
            declared,
            suspects(day.fibber, day.sick, speakers, alive, declared, caught=caught),
        )
        if forced or liar is not None
    )
    if (first := next(found, None)) is None:  # pragma: no cover (a solvable day)
        msg = "no clue forces anyone"
        raise ValueError(msg)
    subset, forced, liar = first
    # Someone to declare before someone to call BS on.
    if forced or liar is None:
        return [speakers[i] for i in subset], min(forced, key=DESKS.index)
    return [speakers[i] for i in subset], speakers[liar]


def _bits(desks: set[Desk] | frozenset[Desk]) -> int:
    return sum(1 << DESKS.index(d) for d in desks)
