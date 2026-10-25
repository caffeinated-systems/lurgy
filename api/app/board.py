from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

type ColumnName = Literal["A", "B", "C", "D"]
type Desk = Literal[
    "A1", "B1", "C1", "D1",
    "A2", "B2", "C2", "D2",
    "A3", "B3", "C3", "D3",
    "A4", "B4", "C4", "D4",
    "A5", "B5", "C5", "D5",
]  # fmt: skip

COLUMNS: tuple[ColumnName, ...] = ("A", "B", "C", "D")
ROWS = 5
# Row by row, so desk i is bit i of a board.
DESKS: tuple[Desk, ...] = (
    "A1", "B1", "C1", "D1",
    "A2", "B2", "C2", "D2",
    "A3", "B3", "C3", "D3",
    "A4", "B4", "C4", "D4",
    "A5", "B5", "C5", "D5",
)  # fmt: skip

type Cell = tuple[int, int]  # (column, row), both from 0


def cell(desk: Desk) -> Cell:
    i = DESKS.index(desk)
    return i % len(COLUMNS), i // len(COLUMNS)


def _bit(c: Cell) -> int:
    return 1 << (c[1] * len(COLUMNS) + c[0])


ALL_CELLS = [(c, r) for r in range(ROWS) for c in range(len(COLUMNS))]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True)


class Row(_Model):
    kind: Literal["row"] = "row"
    row: Annotated[int, Field(ge=1, le=ROWS)]


class Column(_Model):
    kind: Literal["column"] = "column"
    column: ColumnName


class Neighbours(_Model):
    kind: Literal["neighbours"] = "neighbours"
    of: Desk


class Between(_Model):
    """The desks strictly between two desks in the same row or column."""

    kind: Literal["between"] = "between"
    a: Desk
    b: Desk

    @model_validator(mode="after")
    def _same_line(self) -> Between:
        (ac, ar), (bc, br) = cell(self.a), cell(self.b)
        if self.a == self.b or (ac != bc and ar != br):
            msg = "between needs two desks in the same row or column"
            raise ValueError(msg)
        return self


class Direction(_Model):
    """Every desk above, below, left or right of a desk, up to the edge."""

    kind: Literal["direction"] = "direction"
    of: Desk
    direction: Literal["above", "below", "left", "right"]


class Corners(_Model):
    kind: Literal["corners"] = "corners"


class Edges(_Model):
    kind: Literal["edges"] = "edges"


class Department(_Model):
    kind: Literal["department"] = "department"
    name: str


type Group = Annotated[
    Row | Column | Neighbours | Between | Direction | Corners | Edges | Department,
    Field(discriminator="kind"),
]


class Coworker(_Model):
    name: str
    department: str


class Board(_Model):
    """Who sits where: coworkers in desk order, A1 to D5."""

    coworkers: Annotated[
        tuple[Coworker, ...], Field(min_length=len(DESKS), max_length=len(DESKS))
    ]

    @property
    def departments(self) -> list[str]:
        return sorted({c.department for c in self.coworkers})

    def bits(self, group: Group) -> int:
        """The desks in a group, as a bitmask."""
        return sum(_bit(c) for c in self._cells(group))

    def _cells(self, group: Group) -> list[Cell]:  # noqa: PLR0911
        match group:
            case Row(row=row):
                return [(c, r) for c, r in ALL_CELLS if r == row - 1]
            case Column(column=column):
                return [(c, r) for c, r in ALL_CELLS if c == COLUMNS.index(column)]
            case Neighbours(of=of):
                oc, orow = cell(of)
                return [
                    (c, r) for c, r in ALL_CELLS if max(abs(c - oc), abs(r - orow)) == 1
                ]
            case Between(a=a, b=b):
                (ac, ar), (bc, br) = sorted([cell(a), cell(b)])
                return [
                    (c, r)
                    for c, r in ALL_CELLS
                    if ac <= c <= bc
                    and ar <= r <= br
                    and (c, r) not in {(ac, ar), (bc, br)}
                ]
            case Direction(of=of, direction=direction):
                oc, orow = cell(of)
                return [
                    (c, r)
                    for c, r in ALL_CELLS
                    if {
                        "above": c == oc and r < orow,
                        "below": c == oc and r > orow,
                        "left": r == orow and c < oc,
                        "right": r == orow and c > oc,
                    }[direction]
                ]
            case Corners():
                return [
                    (c, r)
                    for c, r in ALL_CELLS
                    if c in {0, len(COLUMNS) - 1} and r in {0, ROWS - 1}
                ]
            case Edges():
                return [
                    (c, r)
                    for c, r in ALL_CELLS
                    if c in {0, len(COLUMNS) - 1} or r in {0, ROWS - 1}
                ]
            case Department(name=name):  # pragma: no branch (the match is exhaustive)
                cells = [
                    ALL_CELLS[i]
                    for i, coworker in enumerate(self.coworkers)
                    if coworker.department == name
                ]
                if not cells:
                    msg = f"no coworker in {name}"
                    raise ValueError(msg)
                return cells
