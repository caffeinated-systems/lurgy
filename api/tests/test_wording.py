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
from app.clues import (
    AllIn,
    Clue,
    Count,
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
)
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
        (
            Parity(group=Row(row=3), parity="odd"),
            "An odd number of people in my row are sick.",
        ),
        (
            Parity(group=Neighbours(of="A2"), parity="even", state="well"),
            "An even number of people among Erin's neighbours are well.",
        ),
        (
            Equal(a=Row(row=1), b=Row(row=3)),
            "There are as many sick people in row 1 as sick people in my row.",
        ),
        (
            More(a=Row(row=3), b=Direction(of="B3", direction="right")),
            "There are more sick people in my row than sick people to my right.",
        ),
        (
            More(a=Department(name="IT"), b=Department(name="HR"), state="well"),
            "There are more well people in IT than well people in my department.",
        ),
        (
            SickVsWell(group=Neighbours(of="B3"), more="sick"),
            "More people among my neighbours are sick than well.",
        ),
        (
            SickVsWell(group=Column(column="A"), more="well"),
            "More people in column A are well than sick.",
        ),
        (
            SickVsWell(group=Row(row=1), more=None),
            "Half the people in row 1 are sick.",
        ),
        (Most(group=Column(column="D")), "Column D has the most sick people."),
        (Most(group=Row(row=3), state="well"), "My row has the most well people."),
        (Most(group=Department(name="Sales")), "Sales has the most sick people."),
        (
            OneOf(desk="C3", group=Row(row=3), n=3),
            "Kev is one of three sick people in my row.",
        ),
        (
            OneOf(desk="B3", group=Department(name="HR"), n=None, state="well"),
            "I am one of the well people in my department.",
        ),
        (
            OnlyOne(family="columns", n=1),
            "Only one column has exactly one sick person.",
        ),
        (OnlyOne(family="rows", n=0), "Only one row has no sick people."),
        (
            OnlyOne(family="departments", n=3, state="well"),
            "Only one department has exactly three well people.",
        ),
        (
            OnlyOneNeighbours(group=Row(row=3), n=4),
            "Only one person in my row has exactly four sick neighbours.",
        ),
        (
            OnlyOneNeighbours(group=Corners(), n=1, state="well"),
            "Only one person in the corners has exactly one well neighbour.",
        ),
        (
            OnlyOneNeighbours(group=Column(column="A"), n=0),
            "Only one person in column A has no sick neighbours.",
        ),
        (
            Overlap(a=Row(row=3), b=Neighbours(of="B2"), n=2),
            "Two of the sick people in my row are among Fergus's neighbours.",
        ),
        (
            Overlap(a=Department(name="Sales"), b=Row(row=4), n=2, state="well"),
            "Two of the well people in Sales are in row 4.",
        ),
        (
            AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=1),
            "The only sick person in my row is among Fergus's neighbours.",
        ),
        (
            AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=2),
            "Both sick people in my row are among Fergus's neighbours.",
        ),
        (
            AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=None, state="well"),
            "All the well people in my row are among Fergus's neighbours.",
        ),
        (
            AllIn(a=Row(row=5), b=Corners(), n=1),
            "The only sick person in row 5 is in a corner.",
        ),
    ],
)
def test_wording(clue: Clue, said: str) -> None:
    assert wording(SAMPLE_BOARD, SPEAKER, clue) == said


@pytest.mark.parametrize(
    ("clue", "explained"),
    [
        (
            Count(group=Row(row=3), n=2),
            "My row is Imogen, Kev, Linda and me: exactly two of them are sick.",
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
                "The people between Imogen and Linda are Kev and me:"
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
            "My department is Carol, Steve and me: exactly two of them are sick.",
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
        (
            Parity(group=Row(row=3), parity="odd"),
            (
                "My row is Imogen, Kev, Linda and me:"
                " an odd number of them (one or three) are sick."
            ),
        ),
        (
            Parity(group=Department(name="HR"), parity="even", state="well"),
            (
                "My department is Carol, Steve and me:"
                " an even number of them (zero or two) are well."
            ),
        ),
        (
            Equal(a=Row(row=1), b=Row(row=3)),
            (
                "Row 1 is Aisha, Barry, Carol and Dev. My row is Imogen, Kev, Linda"
                " and me. As many of the first are sick as of the second, and that"
                " can be none."
            ),
        ),
        (
            More(a=Row(row=3), b=Direction(of="B3", direction="right")),
            (
                "My row is Imogen, Kev, Linda and me. The people to my right are Kev"
                " and Linda. More of the first are sick than of the second, which can"
                " have none."
            ),
        ),
        (
            SickVsWell(group=Neighbours(of="A2"), more="sick"),
            (
                "Erin's neighbours are Aisha, Barry, Fergus, Imogen and me:"
                " more of them are sick than well."
            ),
        ),
        (
            SickVsWell(group=Row(row=1), more=None),
            (
                "Row 1 is Aisha, Barry, Carol and Dev:"
                " half of them (two) are sick, and half are well."
            ),
        ),
        (
            Most(group=Column(column="D")),
            "Column D has more sick people than any other column.",
        ),
        (
            Most(group=Row(row=3)),
            "My row has more sick people than any other row.",
        ),
        (
            Most(group=Department(name="Sales"), state="well"),
            "Sales has more well people than any other department.",
        ),
        (
            OneOf(desk="C3", group=Row(row=3), n=3),
            (
                "My row is Imogen, Kev, Linda and me:"
                " Kev is sick, and so are exactly two others."
            ),
        ),
        (
            OneOf(desk="C3", group=Row(row=3), n=2, state="well"),
            (
                "My row is Imogen, Kev, Linda and me:"
                " Kev is well, and so is exactly one other."
            ),
        ),
        (
            OneOf(desk="B3", group=Department(name="HR"), n=None),
            (
                "My department is Carol, Steve and me:"
                " I am sick, and so is at least one other."
            ),
        ),
        (
            OnlyOne(family="columns", n=1),
            (
                "Of columns A to D, exactly one has exactly one sick person;"
                " every other column has more or fewer."
            ),
        ),
        (
            OnlyOne(family="rows", n=0),
            (
                "Of rows 1 to 5, exactly one has no sick people;"
                " every other row has more."
            ),
        ),
        (
            OnlyOne(family="departments", n=3, state="well"),
            (
                "Of Facilities, Finance, HR, IT, Marketing and Sales, exactly one has"
                " exactly three well people; every other department has more or fewer."
            ),
        ),
        (
            OnlyOneNeighbours(group=Row(row=3), n=4),
            (
                "My row is Imogen, Kev, Linda and me: just one of us has exactly"
                " four sick neighbours, counting diagonals."
            ),
        ),
        (
            OnlyOneNeighbours(group=Corners(), n=1),
            (
                "The corners are Aisha, Dev, Quentin and Tariq: just one of them has"
                " exactly one sick neighbour, counting diagonals."
            ),
        ),
        (
            Overlap(a=Row(row=3), b=Neighbours(of="B2"), n=2),
            (
                "My row is Imogen, Kev, Linda and me. Fergus's neighbours are Aisha,"
                " Barry, Carol, Erin, Gemma, Imogen, Kev and me. The people in both"
                " are Imogen, Kev and me: exactly two of them are sick."
            ),
        ),
        (
            AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=1),
            (
                "My row is Imogen, Kev, Linda and me. Fergus's neighbours are Aisha,"
                " Barry, Carol, Erin, Gemma, Imogen, Kev and me. Exactly one of the"
                " first is sick, and they're in the second too, so Linda is not sick."
            ),
        ),
        (
            AllIn(a=Row(row=3), b=Neighbours(of="D2"), n=2),
            (
                "My row is Imogen, Kev, Linda and me. Hamid's neighbours are Carol,"
                " Dev, Gemma, Kev and Linda. Exactly two of the first are sick, both"
                " in the second too, so Imogen and I are not sick."
            ),
        ),
        (
            AllIn(a=Row(row=1), b=Corners(), n=2),
            (
                "Row 1 is Aisha, Barry, Carol and Dev. The corners are Aisha, Dev,"
                " Quentin and Tariq. Exactly two of the first are sick, both in the"
                " second too, so Barry and Carol are not sick."
            ),
        ),
        (
            AllIn(a=Row(row=3), b=Neighbours(of="B2"), n=None, state="well"),
            (
                "My row is Imogen, Kev, Linda and me. Fergus's neighbours are Aisha,"
                " Barry, Carol, Erin, Gemma, Imogen, Kev and me. At least one of the"
                " first is well, and all of them are in the second too, so Linda"
                " is not well."
            ),
        ),
    ],
)
def test_explanation(clue: Clue, explained: str) -> None:
    assert explanation(SAMPLE_BOARD, SPEAKER, clue) == explained
