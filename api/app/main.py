import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from functools import cache
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.board import DESKS, Board, Desk
from app.clues import EVERYONE, Count, More, State
from app.grade import hint
from app.week import Day, Difficulty, load_days

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# UTC+14 (Kiribati): where every day starts first.
EARLIEST = timezone(timedelta(hours=14))


@cache
def days() -> dict[date, tuple[Board, Day]]:
    """Every day in the Week files, read once from `PUZZLES_DIR`."""
    return load_days(Path(os.environ["PUZZLES_DIR"]))


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    days()  # A missing or bad Week file fails the boot, not the first request.
    yield


# ponytail: version mirrors pyproject.toml (the project isn't installed, so
# importlib.metadata can't read it).
app = FastAPI(
    title="Office Lurgy API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    swagger_ui_oauth2_redirect_url=None,
    lifespan=lifespan,
)


def today_anywhere() -> date:
    """The latest date anywhere on Earth right now."""
    return datetime.now(EARLIEST).date()


type Days = Annotated[dict[date, tuple[Board, Day]], Depends(days)]
type Today = Annotated[date, Depends(today_anywhere)]
NOT_FOUND: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"description": "No puzzle for that day yet."}
}


def find(
    on: date, days: dict[date, tuple[Board, Day]], today: date
) -> tuple[Board, Day]:
    """The day's board and puzzle, if it exists and has started somewhere."""
    if on > today or on not in days:
        raise HTTPException(HTTPStatus.NOT_FOUND, "No puzzle for that day yet.")
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
    joke: Annotated[
        str | None,
        Field(
            description="A short joke after a clue; never part of the logic.",
            examples=["Not that I'm counting."],
        ),
    ] = None

    @classmethod
    def at(cls, day: Day, desk: Desk) -> Self:
        reveal = day.reveal(desk)
        return cls(
            desk=desk,
            state=day.state(desk),
            kind="flavour" if reveal.clue is None else "clue",
            text=reveal.text,
            joke=reveal.joke,
        )


class DayResponse(BaseModel):
    date: Annotated[
        date, Field(description="The puzzle's day.", examples=["2026-10-19"])
    ]
    coworkers: Annotated[
        list[SeatedCoworker],
        Field(
            description="Everyone on the board, A1 to D5.",
            examples=[[{"desk": "A1", "name": "Aisha", "department": "Facilities"}]],
        ),
    ]
    start: Annotated[
        RevealedCoworker, Field(description="The coworker revealed at the start.")
    ]
    difficulty: Annotated[
        Difficulty | None,
        Field(
            description="How hard the puzzle is; null for Weeks built before grading.",
            examples=["Medium"],
        ),
    ]


class Declaration(BaseModel):
    desk: Annotated[Desk, Field(description="Who is declared.", examples=["A3"])]
    state: Annotated[
        State, Field(description="Sick or well, as declared.", examples=["sick"])
    ]


class DeclarationRequest(BaseModel):
    date: Annotated[
        date, Field(description="The puzzle's day.", examples=["2026-10-19"])
    ]
    declared: Annotated[
        list[Declaration],
        Field(
            description="Every declaration accepted so far, in order, "
            "not counting the starting coworker.",
            examples=[[{"desk": "A3", "state": "sick"}]],
            # Everyone but the starting coworker and this declaration.
            max_length=len(DESKS) - 2,
        ),
    ]
    declaration: Annotated[Declaration, Field(description="The new declaration.")]


class HintRequest(BaseModel):
    date: Annotated[
        date, Field(description="The puzzle's day.", examples=["2026-10-19"])
    ]
    declared: Annotated[
        list[Declaration],
        Field(
            description="Every declaration accepted so far, in order, "
            "not counting the starting coworker.",
            examples=[[{"desk": "A3", "state": "sick"}]],
            max_length=len(DESKS) - 1,
        ),
    ]


class ExplainedClue(BaseModel):
    desk: Annotated[Desk, Field(description="Who said it.", examples=["B3"])]
    explanation: Annotated[
        str | None,
        Field(
            description="The clue spelled out desk by desk; "
            "puzzles built before explanations existed have none.",
            examples=[
                "Kev's neighbours are Jas and Rosa: exactly one of them is sick."
            ],
        ),
    ]
    desks: Annotated[
        list[Desk],
        Field(description="The desks the clue talks about.", examples=[["A3", "C3"]]),
    ]

    @classmethod
    def at(cls, board: Board, day: Day, desk: Desk) -> Self:
        reveal = day.reveal(desk)
        match reveal.clue:
            case None:  # pragma: no cover (a hint only names clues)
                raise ValueError(desk)
            case Count(group=group):
                bits = board.bits(group)
            case More(a=a, b=b):
                bits = board.bits(a) | board.bits(b)
            case _:  # the rest are about the whole office
                bits = EVERYONE
        return cls(
            desk=desk,
            explanation=reveal.explanation,
            desks=[d for i, d in enumerate(DESKS) if bits >> i & 1],
        )


class Hint(BaseModel):
    clues: Annotated[
        list[Desk],
        Field(
            description="Who said the fewest clues that, together, force someone.",
            examples=[["B3", "A3"]],
        ),
    ]
    coworker: Annotated[
        Desk,
        Field(description="The first coworker those clues force.", examples=["A4"]),
    ]
    explanations: Annotated[
        list[ExplainedClue],
        Field(description="Each of those clues spelled out, in the same order."),
    ]


class Accepted(BaseModel):
    accepted: Annotated[
        Literal[True], Field(description="The declaration was accepted.")
    ] = True
    reveal: Annotated[
        RevealedCoworker, Field(description="The declared coworker, now revealed.")
    ]


class Rejected(BaseModel):
    accepted: Annotated[Literal[False], Field(description="Not enough evidence.")] = (
        False
    )


@app.get("/api/health")
def health() -> Health:
    """Report that the API is up."""
    return Health()


@app.get("/api/days/{day}", responses=NOT_FOUND)
def get_day(day: date, days: Days, today: Today) -> DayResponse:
    """A day's board and its starting coworker's clue.

    404 for a day with no puzzle or one that hasn't started anywhere on Earth yet.
    """
    board, puzzle = find(day, days, today)
    return DayResponse(
        date=day,
        coworkers=[
            SeatedCoworker(desk=desk, name=c.name, department=c.department)
            for desk, c in zip(DESKS, board.coworkers, strict=True)
        ],
        start=RevealedCoworker.at(puzzle, puzzle.start),
        difficulty=puzzle.difficulty,
    )


@app.post("/api/declarations", responses=NOT_FOUND)
def declare(
    request: DeclarationRequest, days: Days, today: Today
) -> Accepted | Rejected:
    """Declare a coworker sick or well.

    Accepted only if every declaration so far, then this one, was correct and forced
    when made. Otherwise rejected, always with the same body, whatever the reason.
    """
    board, puzzle = find(request.date, days, today)
    steps = [(d.desk, d.state) for d in [*request.declared, request.declaration]]
    if not puzzle.accepts(board, steps):
        return Rejected()
    return Accepted(reveal=RevealedCoworker.at(puzzle, request.declaration.desk))


@app.post(
    "/api/hints",
    responses={
        **NOT_FOUND,
        HTTPStatus.BAD_REQUEST: {"description": "Not enough evidence."},
        HTTPStatus.CONFLICT: {"description": "Everyone is already declared."},
    },
)
def get_hint(request: HintRequest, days: Days, today: Today) -> Hint:
    """The fewest revealed clues that force some coworker, and that coworker.

    400 with the same body as any rejection if the declarations sent aren't all
    accepted, so a hint can't probe the solution.
    """
    board, puzzle = find(request.date, days, today)
    steps = [(d.desk, d.state) for d in request.declared]
    if not puzzle.accepts(board, steps):
        raise HTTPException(HTTPStatus.BAD_REQUEST, "Not enough evidence.")
    if len(steps) == len(DESKS) - 1:
        raise HTTPException(HTTPStatus.CONFLICT, "Everyone is already declared.")
    clues, coworker = hint(board, puzzle, steps)
    return Hint(
        clues=clues,
        coworker=coworker,
        explanations=[ExplainedClue.at(board, puzzle, d) for d in clues],
    )


# Vite builds web/ into here, inside api/, the only directory Laravel Cloud ships.
WEB_DIST = Path(__file__).parents[1] / "static"

# Mounted last so /api routes win; check_dir=False lets the API run unbuilt web/.
app.mount("/", StaticFiles(directory=WEB_DIST, html=True, check_dir=False))
