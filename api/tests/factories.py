from datetime import date
from pathlib import Path

from app.board import DESKS, Desk
from app.cast import STUB_BOARD

FIXTURES = Path(__file__).parent / "fixtures" / "puzzles"
MONDAY = date(2026, 10, 19)  # the Monday sample's day in the fixture Week

# The Monday sample from the voice prototype, which is also the stub cast.
SAMPLE_BOARD = STUB_BOARD


def desks(bits: int) -> set[Desk]:
    return {d for i, d in enumerate(DESKS) if bits >> i & 1}


def board_index(sick: set[Desk]) -> int:
    """The board (an index into all 2^20) where exactly these desks are sick."""
    return sum(1 << DESKS.index(d) for d in sick)
