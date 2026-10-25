import os
from datetime import date, datetime, timedelta, timezone
from functools import cache
from http import HTTPStatus
from pathlib import Path
from typing import Annotated, Literal, Self

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.board import DESKS, Board, Desk
from app.clues import State
from app.week import Day, load_days

# ponytail: version mirrors pyproject.toml (the project isn't installed, so
# importlib.metadata can't read it); title is a placeholder until #16 names the game.
app = FastAPI(
    title="Office bug API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    swagger_ui_oauth2_redirect_url=None,
)

# UTC+14 (Kiribati): where every day starts first.
EARLIEST = timezone(timedelta(hours=14))


@cache
def days() -> dict[date, tuple[Board, Day]]:
    """Every day in the Week files, read once from `PUZZLES_DIR`."""
    return load_days(Path(os.environ["PUZZLES_DIR"]))


def today_anywhere() -> date:
    """The latest date anywhere on Earth right now."""
    return datetime.now(EARLIEST).date()


def playable(
    on: date,
    days: Annotated[dict[date, tuple[Board, Day]], Depends(days)],
    today: Annotated[date, Depends(today_anywhere)],
) -> tuple[Board, Day]:
    """The day's board and puzzle, if it exists and has started somewhere."""
    if on > today or on not in days:
        raise HTTPException(HTTPStatus.NOT_FOUND, "No puzzle for that day.")
    return days[on]


class Health(BaseModel):
    status: Literal["ok"] = Field(
        default="ok", description="Always `ok` while the API is up.", examples=["ok"]
    )


class SeatedCoworker(BaseModel):
    desk: Annotated[Desk, Field(description="Where they sit.", examples=["A1"])]
    name: Annotated[str, Field(description="Their first name.", examples=["Aisha"])]
    department: Annotated[
        str, Field(description="The department they work in.", examples=["HR"])
    ]


class RevealedCoworker(BaseModel):
    desk: Annotated[Desk, Field(description="Where they sit.", examples=["B3"])]
    state: Annotated[
        State, Field(description="Whether they're sick or well.", examples=["well"])
    ]
    kind: Annotated[
        Literal["clue", "flavour"],
        Field(
            description="Whether they gave a clue or only flavour.", examples=["clue"]
        ),
    ]
    text: Annotated[
        str,
        Field(
            description="What they say.",
            examples=["Two people in my column are sick."],
        ),
    ]

    @classmethod
    def at(cls, day: Day, desk: Desk) -> Self:
        reveal = day.reveal(desk)
        return cls(
            desk=desk,
            state="sick" if desk in day.sick else "well",
            kind="flavour" if reveal.clue is None else "clue",
            text=reveal.text,
        )


class DayResponse(BaseModel):
    date: Annotated[date, Field(description="The puzzle's day.")]
    coworkers: Annotated[
        list[SeatedCoworker], Field(description="Everyone on the board, A1 to D5.")
    ]
    start: Annotated[
        RevealedCoworker, Field(description="The coworker revealed at the start.")
    ]


@app.get("/api/health")
def health() -> Health:
    """Report that the API is up."""
    return Health()


@app.get("/api/days/{on}", responses={HTTPStatus.NOT_FOUND: {}})
def get_day(
    on: date, puzzle: Annotated[tuple[Board, Day], Depends(playable)]
) -> DayResponse:
    """A day's board and its starting coworker's clue.

    404 for a day with no puzzle or one that hasn't started anywhere on Earth yet.
    """
    board, day = puzzle
    return DayResponse(
        date=on,
        coworkers=[
            SeatedCoworker(desk=desk, name=c.name, department=c.department)
            for desk, c in zip(DESKS, board.coworkers, strict=True)
        ],
        start=RevealedCoworker.at(day, day.start),
    )


# ponytail: fixed repo-relative path; make it configurable if the deploy (#34) needs.
WEB_DIST = Path(__file__).parents[2] / "web" / "dist"

# Mounted last so /api routes win; check_dir=False lets the API run unbuilt web/.
app.mount("/", StaticFiles(directory=WEB_DIST, html=True, check_dir=False))
