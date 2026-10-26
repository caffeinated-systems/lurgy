import pytest

from app.board import (
    Between,
    Column,
    Corners,
    Department,
    Desk,
    Direction,
    Edges,
    Neighbours,
    Row,
)
from app.clues import Clue, Count, NoMoreThan, Total
from app.wording import explanation, wording
from tests.factories import SAMPLE_BOARD

# Jas sits at B3, in HR; Erin at A2.
SPEAKER: Desk = "B3"


@pytest.mark.parametrize(
    ("clue", "said"),
    [
        (Count(group=Row(row=3), n=2), "Two people in my row are sick."),
        (Count(group=Row(row=1), n=1), "One person in row 1 is sick."),
        (Count(group=Row(row=1), n=0), "No one in row 1 is sick."),
        (Count(group=Column(column="B"), n=3), "Three people in my column are sick."),
        (
            Count(group=Column(column="D"), n=2, state="well"),
            "Two people in column D are well.",
        ),
        (
            Count(group=Neighbours(of="B3"), n=4),
            "Four people among my neighbours are sick.",
        ),
        (
            Count(group=Neighbours(of="A2"), op="at_least", n=1, state="well"),
            "At least one person among Erin's neighbours is well.",
        ),
        (
            Count(group=Between(a="A3", b="D3"), n=0),
            "No one between Imogen and Linda is sick.",
        ),
        (
            Count(group=Between(a="B1", b="B3"), n=1),
            "One person between Barry and me is sick.",
        ),
        (
            Count(group=Direction(of="B3", direction="above"), n=2),
            "Two people above me are sick.",
        ),
        (
            Count(group=Direction(of="B3", direction="left"), n=1),
            "One person to my left is sick.",
        ),
        (
            Count(group=Direction(of="A2", direction="right"), n=3),
            "Three people to the right of Erin are sick.",
        ),
        (
            Count(group=Direction(of="A2", direction="below"), n=1),
            "One person below Erin is sick.",
        ),
        (Count(group=Corners(), n=2), "Two people in the corners are sick."),
        (
            Count(group=Edges(), op="at_least", n=5),
            "At least five people on the edges are sick.",
        ),
        (
            Count(group=Department(name="HR"), n=2),
            "Two people in my department are sick.",
        ),
        (Count(group=Department(name="IT"), n=2), "Two people in IT are sick."),
        (Total(n=8), "Eight people in the office are sick."),
        (
            Total(op="at_least", n=12, state="well"),
            "At least twelve people in the office are well.",
        ),
        (NoMoreThan(family="rows", n=2), "No row has more than two sick people."),
        (
            NoMoreThan(family="departments", n=1, state="well"),
            "No department has more than one well person.",
        ),
        (NoMoreThan(family="columns", n=0), "No column has any sick people."),
    ],
)
def test_wording(clue: Clue, said: str) -> None:
    assert wording(SAMPLE_BOARD, SPEAKER, clue) == said


@pytest.mark.parametrize(
    ("clue", "explained"),
    [
        (
            Count(group=Row(row=3), n=2),
            "My row is Imogen, me, Kev and Linda: exactly two of them are sick.",
        ),
        (
            Count(group=Row(row=1), n=1),
            "Row 1 is Aisha, Barry, Carol and Dev: exactly one of them is sick.",
        ),
        (
            Count(group=Column(column="A"), n=0),
            "Column A is Aisha, Erin, Imogen, Mo and Quentin: none of them is sick.",
        ),
        (
            Count(group=Neighbours(of="A2"), op="at_least", n=1, state="well"),
            (
                "Erin's neighbours are Aisha, Barry, Fergus, Imogen and me:"
                " at least one of them is well."
            ),
        ),
        (
            Count(group=Neighbours(of="B3"), n=3),
            (
                "My neighbours are Erin, Fergus, Gemma, Imogen, Kev, Mo, Nadia"
                " and Ollie: exactly three of them are sick."
            ),
        ),
        (
            Count(group=Between(a="A3", b="D3"), n=2),
            (
                "The people between Imogen and Linda are me and Kev:"
                " exactly two of them are sick."
            ),
        ),
        (
            Count(group=Direction(of="B3", direction="below"), n=1),
            "The people below me are Nadia and Rosa: exactly one of them is sick.",
        ),
        (
            Count(group=Corners(), n=2),
            (
                "The corners are Aisha, Dev, Quentin and Tariq:"
                " exactly two of them are sick."
            ),
        ),
        (
            Count(group=Department(name="HR"), n=2),
            "My department is Carol, me and Steve: exactly two of them are sick.",
        ),
        (
            Count(group=Department(name="Sales"), n=2),
            "Sales is Linda, Nadia, Ollie and Rosa: exactly two of them are sick.",
        ),
        (
            Total(n=8),
            "There are twenty people in the office: exactly eight of them are sick.",
        ),
        (
            NoMoreThan(family="rows", n=2),
            "Rows 1 to 5 each have at most two sick people.",
        ),
        (
            NoMoreThan(family="columns", n=1, state="well"),
            "Columns A to D each have at most one well person.",
        ),
        (NoMoreThan(family="rows", n=0), "Rows 1 to 5 each have no sick people."),
        (
            NoMoreThan(family="departments", n=3),
            (
                "Facilities, Finance, HR, IT, Marketing and Sales each have at most"
                " three sick people."
            ),
        ),
    ],
)
def test_explanation(clue: Clue, explained: str) -> None:
    assert explanation(SAMPLE_BOARD, SPEAKER, clue) == explained
