from typing import TYPE_CHECKING

import numpy as np
import pytest

from app.board import (
    DESKS,
    Between,
    Column,
    Corners,
    Desk,
    Direction,
    Neighbours,
    Row,
)
from app.clues import Clue, Count, Total
from app.grade import Step, Suspects, grade, hint, next_step, suspects
from app.week import Day, Reveal, load_days
from tests.factories import FIXTURES, MONDAY, SAMPLE_BOARD

if TYPE_CHECKING:
    from collections.abc import Mapping

    from app.week import Call

# Says nothing new once row 2 is known: the filler for desks a test doesn't need.
NOTHING = Count(group=Row(row=2), n=0)


def day(
    sick: set[Desk], clues: Mapping[Desk, Clue | None], fibber: Desk | None = None
) -> Day:
    """A day starting at A1, with these clues (None: flavour) and NOTHING elsewhere."""
    return Day(
        date=MONDAY,
        start="A1",
        sick=frozenset(sick),
        reveals=tuple(Reveal(clue=clues.get(d, NOTHING), text="…") for d in DESKS),
        fibber=fibber,
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

    step, forced, _ = next_step([NOTHING] * 4, masks, boards, set(DESKS[4:]))

    assert step == Step(hardness=3, breadth=1, whole_board=False)
    assert forced == {"A1"}


def test_a_day_that_needs_a_guess_does_not_grade() -> None:
    with pytest.raises(ValueError, match="guessing"):
        grade(SAMPLE_BOARD, day({"C1"}, {"A1": NOTHING}))


def test_the_monday_sample_declares_everyone_once() -> None:
    board, sample = load_days(FIXTURES)[MONDAY]

    graded = grade(board, sample)

    assert sum(s.breadth for s in graded.steps) == len(DESKS) - 1


def overtime() -> Day:
    """Everyone is well but D5, the fibber, who says nobody is ill: a lie caught
    as soon as D5 is found. Rows 1 to 4 clear the row below; row 4 finds D5."""
    clues: dict[Desk, Clue] = {
        d: Count(group=Row(row=DESKS.index(d) // 4 + 2), n=0) for d in DESKS[:12]
    }
    clues |= {
        "A1": Count(group=Row(row=1), n=0),
        "A4": Count(group=Between(a="A5", b="D5"), n=0),
        "B4": Count(group=Column(column="A"), n=0),
        "C4": Count(group=Row(row=5), n=1),
        "D5": Total(n=0),
    }
    return day({"D5"}, clues, fibber="D5")


def test_calling_bs_is_a_step_of_its_own() -> None:
    graded = grade(SAMPLE_BOARD, overtime())

    # D5 is found sick, then their whole-board lie is caught on its own.
    assert graded.steps[-2:] == (
        Step(hardness=1, breadth=1, whole_board=False),
        Step(hardness=1, breadth=1, whole_board=True),
    )


def test_hints_lead_to_calling_bs_on_the_fibber() -> None:
    puzzle = overtime()
    steps: list[tuple[Desk, Call]] = []
    while len(steps) < len(DESKS):  # everyone but A1, and BS
        clues, coworker = hint(SAMPLE_BOARD, puzzle, steps)
        declared = coworker in {d for d, _ in steps}
        steps.append((coworker, "fibber" if declared else puzzle.state(coworker)))

    assert (clues, coworker) == (["D5"], "D5")
    assert steps[-1] == ("D5", "fibber")
    assert puzzle.accepts(SAMPLE_BOARD, steps)


def test_a_suspect_alone_forces_no_one_while_the_fibber_could_be_elsewhere() -> None:
    boards = np.arange(16, dtype=np.uint32)
    a = (boards & 1).astype(np.bool_)
    fibber = Suspects(liars=frozenset({0}), unspoken=True, caught=False)

    with pytest.raises(ValueError, match="guessing"):
        next_step([NOTHING], [a], boards, set(DESKS[4:]), fibber)


def test_two_suspects_who_disagree_dont_say_which_is_lying() -> None:
    boards = np.arange(16, dtype=np.uint32)
    a = (boards & 1).astype(np.bool_)
    fibber = Suspects(liars=frozenset({0, 1}), unspoken=False, caught=False)

    with pytest.raises(ValueError, match="guessing"):
        next_step([NOTHING] * 2, [a, ~a], boards, set(DESKS[4:]), fibber)


def test_a_suspect_who_contradicts_the_truth_is_caught() -> None:
    # A well coworker says A1 or B1 is sick; a sick one says neither is.
    boards = np.arange(16, dtype=np.uint32)
    a, b = ((boards >> i & 1).astype(np.bool_) for i in range(2))
    fibber = Suspects(liars=frozenset({1}), unspoken=True, caught=False)

    step, forced, caught = next_step(
        [NOTHING] * 2, [a | b, ~a & ~b], boards, set(DESKS[4:]), fibber
    )

    assert (step, forced, caught) == (Step(2, 1, whole_board=False), set(), 1)


def test_once_bs_is_called_only_the_fibbers_clue_is_a_lie() -> None:
    boards = np.arange(4, dtype=np.uint32)

    known = suspects("D5", {"D5"}, ["A1", "B1", "D5"], boards, {"A1"}, caught=True)

    assert known == Suspects(liars=frozenset({2}))
    assert known.unspoken is False  # not compared: it can be a mask
