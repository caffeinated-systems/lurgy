from datetime import date
from typing import TYPE_CHECKING, Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.board import DESKS, Board, Desk
from app.clues import BOARDS, Clue, State

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


type Difficulty = Literal["Easy", "Medium", "Hard"]


class _Model(BaseModel):
    # Week files hold solutions: never echo their contents in a validation error.
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)


class Reveal(_Model):
    """What a coworker says when declared: a clue, or flavour when there's no clue."""

    clue: Clue | None = None
    text: Annotated[str, Field(min_length=1)]
    # The clue spelled out desk by desk; files built before #24 have none.
    explanation: str | None = None


class Day(_Model):
    date: date
    start: Desk
    # In desk order: a set's order changes with PYTHONHASHSEED, and the file mustn't.
    sick: Annotated[
        frozenset[Desk], PlainSerializer(lambda s: sorted(s, key=DESKS.index))
    ]
    # Files built before #24 have no difficulty.
    difficulty: Difficulty | None = None
    reveals: Annotated[
        tuple[Reveal, ...], Field(min_length=len(DESKS), max_length=len(DESKS))
    ]

    def reveal(self, desk: Desk) -> Reveal:
        return self.reveals[DESKS.index(desk)]

    def state(self, desk: Desk) -> State:
        return "sick" if desk in self.sick else "well"

    def accepts(self, board: Board, steps: Iterable[tuple[Desk, State]]) -> bool:
        """Whether every step, in order, was correct and forced when it was made.

        The starting coworker is already known, so a step can't name them.
        """
        # ponytail: masks span all 2^20 boards, ~140 ms to replay a whole day; index
        # the surviving boards instead if #42's limits or hints need it faster.
        alive = np.ones(BOARDS.shape, dtype=np.bool_)
        known: set[Desk] = set()
        for i, (desk, state) in enumerate(
            [(self.start, self.state(self.start)), *steps]
        ):
            sick = (BOARDS >> DESKS.index(desk) & 1).astype(np.bool_)
            # Every step scans in full before deciding, so a wrong guess and a right
            # but unforced one take the same time. Forced: no board left with the
            # opposite state, which only means something once the state is correct.
            opposite = np.count_nonzero(alive & (sick != (state == "sick")))
            if desk in known or state != self.state(desk) or (i and opposite):
                return False
            known.add(desk)
            alive &= sick == (state == "sick")
            if clue := self.reveal(desk).clue:
                alive &= clue.mask(board)
        return True


class Generator(_Model):
    """What built a Week: rerunning this commit with this seed rebuilds it."""

    commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}(-dirty)?$")]
    seed: int  # from `secrets`; as secret as the solutions, so never logged


class Week(_Model):
    """One built Week file: the same board all Week, and its days."""

    board: Board
    days: Annotated[tuple[Day, ...], Field(min_length=1)]
    # Files built before #24 have no generator.
    generator: Generator | None = None


def load_days(directory: Path) -> dict[date, tuple[Board, Day]]:
    """Every day in the Week files in a directory, by date."""
    days: dict[date, tuple[Board, Day]] = {}
    for path in sorted(directory.glob("*.json")):
        week = Week.model_validate_json(path.read_bytes())
        for day in week.days:
            if day.date in days:
                msg = f"{day.date} is in more than one Week file"
                raise ValueError(msg)
            days[day.date] = (week.board, day)
    if not days:
        msg = f"no Week files in {directory}"
        raise ValueError(msg)
    return days
