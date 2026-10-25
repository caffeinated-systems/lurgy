import pytest
from pydantic import TypeAdapter, ValidationError

from app.board import (
    Between,
    Board,
    Column,
    Corners,
    Coworker,
    Department,
    Direction,
    Edges,
    Group,
    Neighbours,
    Row,
)
from tests.factories import SAMPLE_BOARD, desks


@pytest.mark.parametrize(
    ("group", "expected"),
    [
        (Row(row=3), {"A3", "B3", "C3", "D3"}),
        (Column(column="B"), {"B1", "B2", "B3", "B4", "B5"}),
        (Neighbours(of="A1"), {"B1", "A2", "B2"}),
        (
            Neighbours(of="B3"),
            {"A2", "B2", "C2", "A3", "C3", "A4", "B4", "C4"},
        ),
        (Between(a="A3", b="A5"), {"A4"}),
        (Between(a="C3", b="C1"), {"C2"}),
        (Between(a="A2", b="D2"), {"B2", "C2"}),
        (Between(a="B1", b="C1"), set()),
        (Direction(of="A4", direction="below"), {"A5"}),
        (Direction(of="D2", direction="above"), {"D1"}),
        (Direction(of="B3", direction="right"), {"C3", "D3"}),
        (Direction(of="C3", direction="left"), {"A3", "B3"}),
        (Corners(), {"A1", "D1", "A5", "D5"}),
        (
            Edges(),
            {"A1", "B1", "C1", "D1", "A2", "D2", "A3", "D3", "A4", "D4"}
            | {"A5", "B5", "C5", "D5"},
        ),
        (Department(name="Finance"), {"D2", "A4", "A5"}),
    ],
)
def test_group_desks(group: Group, expected: set[str]) -> None:
    assert desks(SAMPLE_BOARD.bits(group)) == expected


def test_unknown_department() -> None:
    with pytest.raises(ValueError, match="no coworker in Legal"):
        SAMPLE_BOARD.bits(Department(name="Legal"))


@pytest.mark.parametrize(("a", "b"), [("A1", "A1"), ("A1", "B2")])
def test_between_needs_one_line(a: str, b: str) -> None:
    with pytest.raises(ValidationError, match="same row or column"):
        Between.model_validate({"a": a, "b": b})


def test_groups_round_trip_as_json() -> None:
    adapter: TypeAdapter[Group] = TypeAdapter(Group)

    group = adapter.validate_json(
        '{"kind": "direction", "of": "B3", "direction": "right"}'
    )

    assert group == Direction(of="B3", direction="right")


def test_board_has_twenty_coworkers() -> None:
    with pytest.raises(ValidationError):
        Board(coworkers=(Coworker(name="Aisha", department="IT"),))


def test_departments() -> None:
    assert SAMPLE_BOARD.departments == [
        "Facilities", "Finance", "HR", "IT", "Marketing", "Sales",
    ]  # fmt: skip


@pytest.mark.parametrize(
    "data",
    [
        {"kind": "row", "row": 0},
        {"kind": "row", "row": 6},
        {"kind": "column", "column": "E"},
        {"kind": "neighbours", "of": "E1"},
        {"kind": "neighbours", "of": "A6"},
        {"kind": "direction", "of": "A1", "direction": "diagonal"},
    ],
)
def test_invalid_groups(data: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(Group).validate_python(data)


def test_names_are_unique() -> None:
    twins = (Coworker(name="Kev", department="IT"),) * 20

    with pytest.raises(ValidationError, match="different name"):
        Board(coworkers=twins)


@pytest.mark.parametrize(("name", "department"), [("", "IT"), ("Kev", "")])
def test_names_and_departments_are_not_empty(name: str, department: str) -> None:
    with pytest.raises(ValidationError):
        Coworker(name=name, department=department)
