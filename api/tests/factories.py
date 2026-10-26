from datetime import date
from pathlib import Path

from app.board import DESKS, Board, Coworker, Desk

FIXTURES = Path(__file__).parent / "fixtures" / "puzzles"
STORIES = Path(__file__).parent / "fixtures" / "stories"
MONDAY = date(2026, 10, 19)  # the Monday sample's day in the fixture Week

# The Monday sample from the voice prototype: names run A to T across the floor.
DEPARTMENTS = (
    "Facilities", "Facilities", "HR", "Marketing",
    "IT", "Facilities", "Marketing", "Finance",
    "IT", "HR", "IT", "Sales",
    "Finance", "Sales", "Sales", "Marketing",
    "Finance", "Sales", "HR", "IT",
)  # fmt: skip
NAMES = (
    "Aisha", "Barry", "Carol", "Dev",
    "Erin", "Fergus", "Gemma", "Hamid",
    "Imogen", "Jas", "Kev", "Linda",
    "Mo", "Nadia", "Ollie", "Priya",
    "Quentin", "Rosa", "Steve", "Tariq",
)  # fmt: skip

SAMPLE_BOARD = Board(
    coworkers=tuple(
        Coworker(name=n, department=d) for n, d in zip(NAMES, DEPARTMENTS, strict=True)
    )
)


def desks(bits: int) -> set[Desk]:
    return {d for i, d in enumerate(DESKS) if bits >> i & 1}


def board_index(sick: set[Desk]) -> int:
    """The board (an index into all 2^20) where exactly these desks are sick."""
    return sum(1 << DESKS.index(d) for d in sick)
