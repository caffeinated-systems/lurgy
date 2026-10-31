from datetime import UTC, date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Annotated, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

from app.board import DESKS, Board, Desk
from app.clues import BOARDS, EVERYONE, Clue, State, fits

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


# UTC+14 (Kiribati): where every day starts first.
EARLIEST = timezone(timedelta(hours=14))
# UTC-12 (Baker Island): where every day ends last.
LATEST = timezone(timedelta(hours=-12))


def utc_now() -> datetime:
    return datetime.now(UTC)


type Difficulty = Literal["Easy", "Medium", "Hard"]
# A declaration: a coworker's state, or calling BS on them as the fibber.
type Call = State | Literal["fibber"]


class _Model(BaseModel):
    # Week files hold solutions: never echo their contents in a validation error.
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)


class Reveal(_Model):
    """What a coworker says when declared: a clue, or flavour when there's no clue."""

    clue: Clue | None = None
    text: Annotated[str, Field(min_length=1)]
    # The clue spelled out desk by desk; files built before #24 have none.
    explanation: str | None = None
    # A short joke after the clue; files built before #30 have none.
    joke: str | None = None


class Day(_Model):
    date: date
    start: Desk
    # In desk order: a set's order changes with PYTHONHASHSEED, and the file mustn't.
    sick: Annotated[
        frozenset[Desk],
        PlainSerializer(lambda s: sorted(s, key=DESKS.index), when_used="json"),
    ]
    # Files built before #24 have no difficulty.
    difficulty: Difficulty | None = None
    reveals: Annotated[
        tuple[Reveal, ...], Field(min_length=len(DESKS), max_length=len(DESKS))
    ]
    # Overtime only: the sick coworker whose clue is false.
    fibber: Desk | None = None

    @model_validator(mode="after")
    def _fibber_lies(self) -> Day:
        fibber = self.fibber
        if fibber and (fibber not in self.sick or not self.reveal(fibber).clue):
            msg = "the fibber must be sick and give a clue"
            raise ValueError(msg)
        return self

    @property
    def overtime(self) -> bool:
        return self.fibber is not None

    def reveal(self, desk: Desk) -> Reveal:
        return self.reveals[DESKS.index(desk)]

    def state(self, desk: Desk) -> State:
        return "sick" if desk in self.sick else "well"

    def accepts(self, board: Board, steps: Iterable[tuple[Desk, Call]]) -> bool:
        """Whether every step, in order, was correct and forced when it was made.

        The starting coworker is already known, so a step can't name them.
        """
        boards = BOARDS  # every board that fits the declarations so far
        known: set[Desk] = set()
        said: dict[Desk, Clue] = {}
        named = False
        for i, (desk, call) in enumerate(
            [(self.start, self.state(self.start)), *steps]
        ):
            # ponytail: every clue is rechecked on every step, but only over the
            # boards the declarations allow, which halve with each one.
            masks = [clue.mask(board, boards) for clue in said.values()]
            liars = [self.overtime and d in self.sick for d in said]
            undeclared = EVERYONE & ~sum(1 << DESKS.index(d) for d in known)
            fitting = (
                fits(masks, liars, elsewhere=(boards & np.uint32(undeclared)) != 0)
                if said
                else np.ones(boards.shape, dtype=np.bool_)
            )
            if call == "fibber":
                # Forced: their clue is false on every board that fits.
                truthful = (
                    np.count_nonzero(masks[[*said].index(desk)][fitting])
                    if desk in said
                    else 1
                )
                if named or desk != self.fibber or truthful:
                    return False
                named = True
                continue
            fit = boards[fitting]
            # Every step scans in full before deciding, so a wrong guess and a right
            # but unforced one take the same time. Forced: no board left with the
            # opposite state, which only means something once the state is correct.
            sick = (fit >> DESKS.index(desk) & 1).astype(np.bool_)
            opposite = np.count_nonzero(sick != (call == "sick"))
            if desk in known or call != self.state(desk) or (i and opposite):
                return False
            known.add(desk)
            boards = boards[(boards >> DESKS.index(desk) & 1) == (call == "sick")]
            if clue := self.reveal(desk).clue:
                said[desk] = clue
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
