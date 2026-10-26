from typing import TYPE_CHECKING

import numpy as np
import pytest

from app.board import DESKS, Column, Corners, Desk, Direction, Neighbours, Row
from app.clues import Clue, Count, Total
from app.grade import Step, grade, next_step
from app.week import Day, Reveal, load_days
from tests.factories import FIXTURES, MONDAY, SAMPLE_BOARD

if TYPE_CHECKING:
    from collections.abc import Mapping

# Says nothing new once row 2 is known: the filler for desks a test doesn't need.
NOTHING = Count(group=Row(row=2), n=0)


def day(sick: set[Desk], clues: Mapping[Desk, Clue | None]) -> Day:
    """A day starting at A1, with these clues (None: flavour) and NOTHING elsewhere."""
    return Day(
        date=MONDAY,
        start="A1",
        sick=frozenset(sick),
        reveals=tuple(Reveal(clue=clues.get(d, NOTHING), text="…") for d in DESKS),
    )


def test_one_clue_at_a_time_is_easy() -> None:
    # Everyone in row r says row r + 1 is all well; row 5 is A1's row's next.
    clues: dict[Desk, Clue] = {
        d: Count(group=Row(row=DESKS.index(d) // 4 + 2), n=0) for d in DESKS[:16]
    }
    clues["A1"] = Count(group=Row(row=1), n=0)
    flavour: dict[Desk, Clue | None] = {"D4": None}  # row 5 still has three

    graded = grade(SAMPLE_BOARD, day(set(), clues | flavour))

    assert graded.steps == (
        Step(hardness=1, breadth=3, whole_board=False),
        Step(hardness=1, breadth=4, whole_board=False),
        Step(hardness=1, breadth=4, whole_board=False),
        Step(hardness=1, breadth=4, whole_board=False),
        Step(hardness=1, breadth=4, whole_board=False),
    )
    assert graded.difficulty == "Easy"


# Column A all well, then rows 2 to 5 and row 1's one sick coworker, C1.
SETUP: dict[Desk, Clue] = {
    "A1": Count(group=Column(column="A"), n=0),
    "A2": Count(group=Row(row=2), n=0),
    "A3": Count(group=Row(row=3), n=0),
    "A4": Count(group=Row(row=4), n=0),
    "C2": Count(group=Row(row=5), n=0),
    "A5": Count(group=Row(row=1), n=1),  # one of B1, C1, D1
}


def test_two_clues_together_is_medium() -> None:
    graded = grade(
        SAMPLE_BOARD,
        day(
            {"C1"},
            SETUP
            | {
                "B2": Count(group=Direction(of="B1", direction="right"), n=1),
                "B1": Count(group=Corners(), n=0),
            },
        ),
    )

    assert [(s.hardness, s.breadth) for s in graded.steps] == [
        (1, 4),  # column A
        (1, 9),  # rows 2 to 4
        (1, 3),  # row 5
        (2, 1),  # B1: row 1 has one sick, and so do C1 and D1
        (1, 1),  # D1, a corner
        (1, 1),  # C1
    ]
    assert graded.difficulty == "Medium"


def test_three_clues_together_is_hard() -> None:
    clues: dict[Desk, Clue] = SETUP | {
        "B2": Count(group=Neighbours(of="C1"), n=1),
        "D2": Count(group=Neighbours(of="B2"), n=1),
        "B3": Count(group=Neighbours(of="D2"), op="at_least", n=1),
    }
    del clues["A5"]

    graded = grade(SAMPLE_BOARD, day({"C1", "D1"}, clues))

    # Row 1, found by a search: no two of the three neighbour counts force anyone.
    assert graded.steps[3] == Step(hardness=3, breadth=3, whole_board=False)
    assert graded.difficulty == "Hard"


def test_needing_a_whole_board_clue_is_hard() -> None:
    graded = grade(SAMPLE_BOARD, day(set(), {"A1": Total(n=0)}))

    assert graded.steps == (Step(hardness=1, breadth=19, whole_board=True),)
    assert graded.difficulty == "Hard"


def test_more_than_three_clues_at_once_counts_as_three() -> None:
    # Four implications round A1 to D1: not A1 → B1 → C1 → D1 → A1. Any three
    # leave everyone open; all four force A1 sick. Boards are row 1 only.
    boards = np.arange(16, dtype=np.uint32)
    a, b, c, d = ((boards >> i & 1).astype(np.bool_) for i in range(4))
    masks = [a | b, ~b | c, ~c | d, ~d | a]

    step, forced = next_step([NOTHING] * 4, masks, boards, set(DESKS[4:]))

    assert step == Step(hardness=3, breadth=1, whole_board=False)
    assert forced == {"A1"}


def test_a_day_that_needs_a_guess_does_not_grade() -> None:
    with pytest.raises(ValueError, match="guessing"):
        grade(SAMPLE_BOARD, day({"C1"}, {"A1": NOTHING}))


def test_the_monday_sample_declares_everyone_once() -> None:
    board, sample = load_days(FIXTURES)[MONDAY]

    graded = grade(board, sample)

    assert sum(s.breadth for s in graded.steps) == len(DESKS) - 1
