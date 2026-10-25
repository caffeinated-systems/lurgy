"""Replay the voice prototype's Monday sample (seed 4) as written."""

from itertools import pairwise

from app.board import (
    DESKS,
    Between,
    Column,
    Corners,
    Department,
    Desk,
    Direction,
    Neighbours,
    Row,
)
from app.clues import Clue, Count, More, forced
from tests.factories import SAMPLE_BOARD, board_index

SICK: set[Desk] = {"A1", "C1", "D1", "A2", "C2", "A3", "A5", "D5"}

# In reveal order: each coworker's clue, starting with Jas, who starts revealed.
REVEALS: list[tuple[Desk, Clue | None]] = [
    ("B3", More(a=Row(row=3), b=Direction(of="B3", direction="right"))),  # Jas
    ("A3", Count(group=Between(a="A3", b="A5"), n=0)),  # Imogen
    ("A4", Count(group=Direction(of="A4", direction="below"), n=1)),  # Mo
    ("A5", Count(group=Department(name="Finance"), n=1)),  # Quentin
    ("D2", Count(group=Direction(of="D2", direction="above"), n=1)),  # Hamid
    ("D1", Count(group=Between(a="D1", b="D4"), n=0)),  # Dev
    ("D3", Count(group=Row(row=3), n=1)),  # Linda
    ("C3", Count(group=Between(a="C3", b="C1"), n=1)),  # Kev
    ("C2", Count(group=Department(name="Marketing"), n=2)),  # Gemma
    ("D4", Count(group=Column(column="D"), n=2)),  # Priya
    ("D5", Count(group=Corners(), n=4)),  # Tariq
    ("A1", Count(group=Column(column="A"), n=4)),  # Aisha
    ("A2", Count(group=Direction(of="A2", direction="right"), n=1)),  # Erin
    ("B2", Count(group=Department(name="Facilities"), n=1)),  # Fergus
    ("B1", Count(group=Row(row=1), n=3)),  # Barry
    ("C1", Count(group=Department(name="HR"), n=1)),  # Carol
    ("C5", Count(group=Row(row=5), n=2)),  # Steve
    ("B5", Count(group=Column(column="C"), n=2)),  # Rosa
    ("C4", Count(group=Neighbours(of="C4"), n=1)),  # Ollie
    ("B4", None),  # Nadia: flavour, no clue
]


def test_every_clue_is_true() -> None:
    solution = board_index(SICK)

    for _, clue in REVEALS:
        if clue:
            assert clue.mask(SAMPLE_BOARD)[solution], clue


def test_each_reveal_is_forced_by_the_clues_before_it() -> None:
    declared: dict[Desk, bool] = {"B3": False}  # Jas starts revealed, well
    clues: list[Clue] = []

    for (_, clue), (desk, _) in pairwise(REVEALS):
        assert clue
        clues.append(clue)
        now = forced(SAMPLE_BOARD, clues, declared)
        assert now.get(desk) == (desk in SICK), desk
        declared[desk] = desk in SICK

    assert len(declared) == len(DESKS)
