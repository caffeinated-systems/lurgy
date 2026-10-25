import pytest
from pydantic import TypeAdapter

from app.board import Corners, Department, Desk, Direction, Neighbours, Row
from app.clues import Clue, Count, More, NoMoreThan, Total, forced
from tests.factories import SAMPLE_BOARD, board_index


@pytest.mark.parametrize(
    ("clue", "sick", "expected"),
    [
        # exactly 2 sick in row 1
        (Count(group=Row(row=1), n=2), {"A1", "B1"}, True),
        (Count(group=Row(row=1), n=2), {"A1"}, False),
        (Count(group=Row(row=1), n=2), {"A1", "B1", "A2"}, True),
        # "no" is exactly 0
        (Count(group=Row(row=1), n=0), set(), True),
        (Count(group=Row(row=1), n=0), {"D1"}, False),
        # at least 2 sick among A1's neighbours
        (Count(group=Neighbours(of="A1"), op="at_least", n=2), {"B1", "B2"}, True),
        (Count(group=Neighbours(of="A1"), op="at_least", n=2), {"B1"}, False),
        (
            Count(group=Neighbours(of="A1"), op="at_least", n=2),
            {"B1", "A2", "B2"},
            True,
        ),
        # exactly 3 well in row 1
        (Count(group=Row(row=1), n=3, state="well"), {"A1"}, True),
        (Count(group=Row(row=1), n=3, state="well"), set(), False),
        # in total
        (Total(n=2), {"A1", "D5"}, True),
        (Total(n=2), {"A1"}, False),
        (Total(op="at_least", n=1), {"C3"}, True),
        (Total(op="at_least", n=1), set(), False),
        (Total(n=19, state="well"), {"C3"}, True),
        # no row / column / department has more than 1 sick
        (NoMoreThan(family="rows", n=1), {"A1", "A2"}, True),
        (NoMoreThan(family="rows", n=1), {"A1", "B1"}, False),
        (NoMoreThan(family="columns", n=1), {"A1", "B1"}, True),
        (NoMoreThan(family="columns", n=1), {"A1", "A2"}, False),
        (NoMoreThan(family="departments", n=1), {"D2", "A1"}, True),
        (NoMoreThan(family="departments", n=1), {"D2", "A4"}, False),  # Finance
        (
            NoMoreThan(family="rows", n=3, state="well"),
            {"A1", "A2", "A3", "A4", "A5"},
            True,
        ),
        (NoMoreThan(family="rows", n=3, state="well"), {"A1"}, False),
        # more sick in row 3 than to the right of B3
        (More(a=Row(row=3), b=Direction(of="B3", direction="right")), {"A3"}, True),
        (More(a=Row(row=3), b=Direction(of="B3", direction="right")), {"C3"}, False),
        (More(a=Row(row=3), b=Direction(of="B3", direction="right")), set(), False),
        (
            More(a=Row(row=3), b=Direction(of="B3", direction="right"), state="well"),
            set(),
            True,
        ),
    ],
)
def test_mask(clue: Clue, sick: set[Desk], expected: bool) -> None:  # noqa: FBT001
    assert clue.mask(SAMPLE_BOARD)[board_index(sick)] == expected


def test_clues_round_trip_as_json() -> None:
    adapter: TypeAdapter[Clue] = TypeAdapter(Clue)
    clue = Count(group=Department(name="HR"), op="at_least", n=1, state="well")

    assert adapter.validate_json(adapter.dump_json(clue)) == clue


def test_nothing_known_forces_nothing() -> None:
    assert forced(SAMPLE_BOARD, [], {}) == {}


def test_a_clue_alone_can_force() -> None:
    assert forced(SAMPLE_BOARD, [Count(group=Corners(), n=4)], {}) == {
        "A1": True,
        "D1": True,
        "A5": True,
        "D5": True,
    }


def test_declarations_count_and_are_left_out() -> None:
    result = forced(SAMPLE_BOARD, [Count(group=Row(row=1), n=1)], {"A1": True})

    assert result == {"B1": False, "C1": False, "D1": False}


def test_declared_well_counts_too() -> None:
    clues = [Count(group=Neighbours(of="A1"), n=1)]

    assert forced(SAMPLE_BOARD, clues, {"B1": False, "A2": False}) == {"B2": True}


def test_contradiction_raises() -> None:
    with pytest.raises(ValueError, match="no board fits"):
        forced(SAMPLE_BOARD, [Count(group=Row(row=1), n=0)], {"A1": True})
