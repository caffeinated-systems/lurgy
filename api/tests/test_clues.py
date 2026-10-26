import pytest
from pydantic import TypeAdapter, ValidationError

from app.board import (
    DESKS,
    Column,
    Corners,
    Department,
    Desk,
    Direction,
    Neighbours,
    Row,
)
from app.clues import (
    AllIn,
    Clue,
    Connected,
    ContradictionError,
    Count,
    Directly,
    Equal,
    More,
    Most,
    NoMoreThan,
    OneOf,
    OnlyOne,
    OnlyOneNeighbours,
    Overlap,
    Parity,
    SickVsWell,
    Total,
    forced,
)
from tests.factories import SAMPLE_BOARD, board_index, desks


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
        # odd / even, and even includes zero
        (Parity(group=Row(row=1), parity="odd"), {"A1"}, True),
        (Parity(group=Row(row=1), parity="odd"), {"A1", "B1"}, False),
        (Parity(group=Row(row=1), parity="even"), set(), True),
        (Parity(group=Row(row=1), parity="odd", state="well"), {"A1"}, True),
        # as many sick in row 1 as in row 3, none included
        (Equal(a=Row(row=1), b=Row(row=3)), {"A1", "C3"}, True),
        (Equal(a=Row(row=1), b=Row(row=3)), {"A1"}, False),
        (Equal(a=Row(row=1), b=Row(row=3)), set(), True),
        # more sick than well in row 1, the reverse, and as many
        (SickVsWell(group=Row(row=1), more="sick"), {"A1", "B1", "C1"}, True),
        (SickVsWell(group=Row(row=1), more="sick"), {"A1", "B1"}, False),
        (SickVsWell(group=Row(row=1), more="well"), {"A1"}, True),
        (SickVsWell(group=Row(row=1), more=None), {"A1", "B1"}, True),
        (SickVsWell(group=Row(row=1), more=None), {"A1"}, False),
        # the most means more than every other: a tie isn't the most
        (Most(group=Column(column="D")), {"D1"}, True),
        (Most(group=Column(column="D")), {"D1", "A1"}, False),
        (Most(group=Column(column="D")), set(), False),
        (Most(group=Row(row=3), state="well"), {"A1"}, False),  # rows 2-5 tie
        (Most(group=Department(name="Sales"), state="well"), set(), False),  # IT
        (Most(group=Department(name="Sales"), state="well"), {"A2"}, True),
        # only one row / column / department has exactly n
        (OnlyOne(family="columns", n=1), {"A1"}, True),
        (OnlyOne(family="columns", n=1), {"A1", "B1"}, False),
        (OnlyOne(family="columns", n=1), set(), False),
        (OnlyOne(family="rows", n=0), {"A1", "A2", "A3", "A4"}, True),
        (OnlyOne(family="departments", n=0, state="well"), {"C1", "B3", "C5"}, True),
        # only one corner has exactly n sick neighbours; B2 neighbours A1 alone
        (OnlyOneNeighbours(group=Corners(), n=1), {"B2"}, True),
        (OnlyOneNeighbours(group=Corners(), n=0), {"B2"}, False),
        (OnlyOneNeighbours(group=Corners(), n=1), {"B2", "C4"}, False),
        (OnlyOneNeighbours(group=Corners(), n=2, state="well"), {"B2"}, True),
        # overlaps: row 3 meets Fergus's (B2) neighbours at A3, B3 and C3
        (Overlap(a=Row(row=3), b=Neighbours(of="B2"), n=2), {"A3", "B3"}, True),
        (Overlap(a=Row(row=3), b=Neighbours(of="B2"), n=2), {"A3", "D3"}, False),
        (
            Overlap(a=Row(row=3), b=Neighbours(of="B2"), n=2),
            {"A3", "B3", "C3"},
            False,
        ),
        (AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=1), {"A3"}, True),
        (AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=1), {"D3"}, False),
        (AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=1), {"A3", "B3"}, False),
        (AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=2), {"A3", "B3"}, True),
        (AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=2), {"A3", "D3"}, False),
        # "all" means at least one
        (AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=None), {"A3", "B3", "C3"}, True),
        (AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=None), set(), False),
        (
            AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=None, state="well"),
            {"D3"},
            True,
        ),
        # connected: one unbroken run along a line, a single coworker included
        (Connected(group=Row(row=1), n=None), {"A1", "B1"}, True),
        (Connected(group=Row(row=1), n=None), {"A1", "C1"}, False),
        (Connected(group=Row(row=1), n=None), {"B1"}, True),
        (Connected(group=Row(row=1), n=None), set(), False),
        (Connected(group=Row(row=1), n=2), {"B1", "C1"}, True),
        (Connected(group=Row(row=1), n=2), {"B1", "C1", "D1"}, False),
        (Connected(group=Row(row=1), n=2), {"A1", "C1"}, False),
        (Connected(group=Column(column="A"), n=None, state="well"), {"A3"}, False),
        (Connected(group=Column(column="A"), n=None, state="well"), {"A1"}, True),
        # directly: the next desk only; a desk at the edge has no one there
        (
            Directly(group=Row(row=1), direction="below", n=None),
            {"A2", "B2", "C2", "D2"},
            True,
        ),
        (
            Directly(group=Row(row=1), direction="below", n=None),
            {"A2", "B2", "C2"},
            False,
        ),
        (Directly(group=Row(row=1), direction="below", n=0), set(), True),
        (Directly(group=Row(row=1), direction="below", n=0), {"B2"}, False),
        (Directly(group=Row(row=1), direction="below", n=2), {"A2", "C2"}, True),
        (Directly(group=Row(row=1), direction="below", n=2), {"A2"}, False),
        (Directly(group=Row(row=5), direction="below", n=None), set(DESKS), False),
        (
            Directly(group=Column(column="A"), direction="right", n=5, state="well"),
            set(),
            True,
        ),
        # about one coworker
        (OneOf(desk="C3", group=Row(row=3), n=2), {"C3", "A3"}, True),
        (OneOf(desk="C3", group=Row(row=3), n=2), {"C3"}, False),
        (OneOf(desk="C3", group=Row(row=3), n=2), {"A3", "B3"}, False),
        # "one of the" means at least two
        (OneOf(desk="C3", group=Row(row=3), n=None), {"C3", "A3", "B3"}, True),
        (OneOf(desk="C3", group=Row(row=3), n=None), {"C3"}, False),
        (OneOf(desk="C3", group=Row(row=3), n=None, state="well"), {"A3"}, True),
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


ROW_3: set[Desk] = {"A3", "B3", "C3", "D3"}


@pytest.mark.parametrize(
    ("clue", "covered"),
    [
        (Count(group=Row(row=3), n=1), ROW_3),
        (
            Parity(group=Direction(of="B3", direction="below"), parity="odd"),
            {"B4", "B5"},
        ),
        (SickVsWell(group=Row(row=3), more=None), ROW_3),
        (More(a=Direction(of="B3", direction="right"), b=Row(row=3)), ROW_3),
        (
            Equal(
                a=Direction(of="B3", direction="above"),
                b=Direction(of="B3", direction="below"),
            ),
            {"B1", "B2", "B4", "B5"},
        ),
        # the rest are about the whole office
        (Total(n=1), set(DESKS)),
        (NoMoreThan(family="rows", n=1), set(DESKS)),
        (OneOf(desk="C3", group=Row(row=3), n=None), ROW_3),
        # the people in the group and their neighbours
        (
            OnlyOneNeighbours(group=Direction(of="B2", direction="above"), n=1),
            {"B1", "A1", "C1", "A2", "B2", "C2"},
        ),
        (
            Overlap(a=Column(column="A"), b=Row(row=1), n=2),
            {"A1", "B1", "C1", "D1", "A2", "A3", "A4", "A5"},
        ),
        (
            AllIn(a=Row(row=1), b=Corners(), n=None),
            {"A1", "B1", "C1", "D1", "A5", "D5"},
        ),
        (Connected(group=Column(column="B"), n=None), {"B1", "B2", "B3", "B4", "B5"}),
        (
            Directly(group=Department(name="HR"), direction="left", n=1),
            {"C1", "B3", "C5", "B1", "A3", "B5"},
        ),
        (OnlyOne(family="rows", n=1), set(DESKS)),
        (Most(group=Row(row=3)), set(DESKS)),
    ],
)
def test_a_clue_covers_its_desks(clue: Clue, covered: set[Desk]) -> None:
    assert desks(clue.bits(SAMPLE_BOARD)) == covered


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
    with pytest.raises(ContradictionError):
        forced(SAMPLE_BOARD, [Count(group=Row(row=1), n=0)], {"A1": True})


@pytest.mark.parametrize(
    "data",
    [
        {"kind": "count", "group": {"kind": "corners"}, "n": -1},
        {"kind": "total", "n": -1},
        {"kind": "no_more_than", "family": "rows", "n": -1},
        {"kind": "no_more_than", "family": "desks", "n": 1},
        {"kind": "count", "group": {"kind": "corners"}, "n": 1, "op": "at_most"},
        {"kind": "parity", "group": {"kind": "corners"}, "parity": "prime"},
        {"kind": "most", "group": {"kind": "corners"}},
        {"kind": "sick_vs_well", "group": {"kind": "corners"}, "more": "both"},
        {"kind": "one_of", "desk": "A1", "group": {"kind": "corners"}, "n": 1},
        {"kind": "is", "desk": "E9"},
        {"kind": "only_one", "family": "desks", "n": 1},
        {"kind": "only_one_neighbours", "group": {"kind": "corners"}, "n": -1},
        {"kind": "overlap", "a": {"kind": "corners"}, "b": {"kind": "edges"}, "n": 1},
        {"kind": "all_in", "a": {"kind": "corners"}, "b": {"kind": "edges"}, "n": 3},
        {"kind": "connected", "group": {"kind": "corners"}, "n": None},
        {"kind": "connected", "group": {"kind": "row", "row": 1}, "n": 3},
        {
            "kind": "directly",
            "group": {"kind": "corners"},
            "direction": "diagonal",
            "n": 1,
        },
        {
            "kind": "directly",
            "group": {"kind": "corners"},
            "direction": "left",
            "n": -1,
        },
        {"kind": "riddle"},
    ],
)
def test_invalid_clues(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(Clue).validate_python(data)
