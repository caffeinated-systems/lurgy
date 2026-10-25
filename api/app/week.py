from datetime import date
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.board import DESKS, Board, Desk
from app.clues import Clue

if TYPE_CHECKING:
    from pathlib import Path


class _Model(BaseModel):
    # Week files hold solutions: never echo their contents in a validation error.
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)


class Reveal(_Model):
    """What a coworker says when declared: a clue, or flavour when there's no clue."""

    clue: Clue | None = None
    text: Annotated[str, Field(min_length=1)]


class Day(_Model):
    date: date
    start: Desk
    sick: frozenset[Desk]
    reveals: Annotated[
        tuple[Reveal, ...], Field(min_length=len(DESKS), max_length=len(DESKS))
    ]

    def reveal(self, desk: Desk) -> Reveal:
        return self.reveals[DESKS.index(desk)]


class Week(_Model):
    """One built Week file: the same board all Week, and its days."""

    board: Board
    days: Annotated[tuple[Day, ...], Field(min_length=1)]


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
    return days
