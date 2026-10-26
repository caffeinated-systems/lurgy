from typing import TYPE_CHECKING, Annotated, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from app.board import COLUMNS, DESKS, ROWS, Board, Column, Department, Desk, Group, Row

if TYPE_CHECKING:
    from collections.abc import Container, Iterable, Mapping

# Every possible board: bit i set means the coworker at desk i is sick.
BOARDS = np.arange(2 ** len(DESKS), dtype=np.uint32)
EVERYONE: int = 2 ** len(DESKS) - 1

type Mask = NDArray[np.bool_]
type Counts = NDArray[np.uint8]
type State = Literal["sick", "well"]
type Op = Literal["exactly", "at_least"]


type Boards = NDArray[np.uint32]


def _count(bits: int, state: State, boards: Boards) -> Counts:
    """How many coworkers in these desks are in this state, on each board."""
    sick = np.bitwise_count(boards & np.uint32(bits))
    return sick if state == "sick" else bits.bit_count() - sick


def _compare(counts: Counts, op: Op, n: int) -> Mask:
    return counts == n if op == "exactly" else counts >= n


type Family = Literal["rows", "columns", "departments"]
_FAMILY_OF: dict[str, Family] = {
    "row": "rows", "column": "columns", "department": "departments",
}  # fmt: skip


def _family(board: Board, family: Family) -> list[Group]:
    match family:
        case "rows":
            return [Row(row=r) for r in range(1, ROWS + 1)]
        case "columns":
            return [Column(column=c) for c in COLUMNS]
        case "departments":  # pragma: no branch (the match is exhaustive)
            return [Department(name=d) for d in board.departments]


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True)

    def bits(self, board: Board) -> int:  # noqa: ARG002 (same signature as every clue)
        """The desks the clue talks about: the whole office, unless it names groups."""
        return EVERYONE


class Count(_Model):
    """Exactly / at least n sick (or well) in a group."""

    kind: Literal["count"] = "count"
    group: Group
    op: Op = "exactly"
    n: Annotated[int, Field(ge=0)]
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        counts = _count(board.bits(self.group), self.state, boards)
        return _compare(counts, self.op, self.n)

    def bits(self, board: Board) -> int:
        return board.bits(self.group)


class Total(_Model):
    """Exactly / at least n sick (or well) in the whole office."""

    kind: Literal["total"] = "total"
    op: Op = "exactly"
    n: Annotated[int, Field(ge=0)]
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:  # noqa: ARG002 (same signature as every clue)
        return _compare(_count(EVERYONE, self.state, boards), self.op, self.n)


class NoMoreThan(_Model):
    """No row / column / department has more than n sick (or well)."""

    kind: Literal["no_more_than"] = "no_more_than"
    family: Family
    n: Annotated[int, Field(ge=0)]
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        mask = np.ones(boards.shape, dtype=np.bool_)
        for group in _family(board, self.family):
            mask &= _count(board.bits(group), self.state, boards) <= self.n
        return mask


class Parity(_Model):
    """An odd / even number sick (or well) in a group; even includes zero."""

    kind: Literal["parity"] = "parity"
    group: Group
    parity: Literal["odd", "even"]
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        odd: Mask = _count(board.bits(self.group), self.state, boards) % 2 == 1
        return odd if self.parity == "odd" else ~odd

    def bits(self, board: Board) -> int:
        return board.bits(self.group)


class More(_Model):
    """More sick (or well) in group a than in group b, which can have none."""

    kind: Literal["more"] = "more"
    a: Group
    b: Group
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        a = _count(board.bits(self.a), self.state, boards)
        return a > _count(board.bits(self.b), self.state, boards)

    def bits(self, board: Board) -> int:
        return board.bits(self.a) | board.bits(self.b)


class Equal(_Model):
    """As many sick (or well) in group a as in group b, none included."""

    kind: Literal["equal"] = "equal"
    a: Group
    b: Group
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        a = _count(board.bits(self.a), self.state, boards)
        return np.equal(a, _count(board.bits(self.b), self.state, boards))

    def bits(self, board: Board) -> int:
        return board.bits(self.a) | board.bits(self.b)


class SickVsWell(_Model):
    """More sick than well in a group, more well than sick, or (None) as many."""

    kind: Literal["sick_vs_well"] = "sick_vs_well"
    group: Group
    more: State | None

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        bits = board.bits(self.group)
        sick = _count(bits, "sick", boards).astype(np.int8)
        well = bits.bit_count() - sick
        match self.more:
            case "sick":
                return sick > well
            case "well":
                return well > sick
            case None:  # pragma: no branch (the match is exhaustive)
                return np.equal(sick, well)

    def bits(self, board: Board) -> int:
        return board.bits(self.group)


class Most(_Model):
    """A row / column / department has more sick (or well) than every other one."""

    kind: Literal["most"] = "most"
    group: Annotated[Row | Column | Department, Field(discriminator="kind")]
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        family = _FAMILY_OF[self.group.kind]
        mine = _count(board.bits(self.group), self.state, boards)
        mask = np.ones(boards.shape, dtype=np.bool_)
        for group in _family(board, family):
            if group != self.group:
                mask &= mine > _count(board.bits(group), self.state, boards)
        return mask


type Clue = Annotated[
    Count | Total | NoMoreThan | Parity | More | Equal | SickVsWell | Most,
    Field(discriminator="kind"),
]

# Clues about the whole office: a step that needs one makes the day Hard.
WIDE = (Total, NoMoreThan, Most)


class ContradictionError(Exception):
    """The clues and declarations contradict each other."""

    def __init__(self) -> None:
        super().__init__("no board fits the clues and declarations")


def forced(
    board: Board, clues: Iterable[Clue], declared: Mapping[Desk, bool]
) -> dict[Desk, bool]:
    """Undeclared coworkers whose state is the same on every board that fits."""
    alive = np.ones(BOARDS.shape, dtype=np.bool_)
    for clue in clues:
        alive &= clue.mask(board)
    known = sum(1 << DESKS.index(d) for d in declared)
    sick = sum(1 << DESKS.index(d) for d, s in declared.items() if s)
    alive &= (BOARDS & np.uint32(known)) == sick

    return settled(BOARDS[alive], declared)


def settled(boards: Boards, declared: Container[Desk]) -> dict[Desk, bool]:
    """Undeclared coworkers in the same state on all of these boards."""
    if boards.size == 0:
        raise ContradictionError
    always = int(np.bitwise_and.reduce(boards))
    ever = int(np.bitwise_or.reduce(boards))
    return {
        desk: bool(always >> i & 1)
        for i, desk in enumerate(DESKS)
        if desk not in declared and (always >> i & 1 or not ever >> i & 1)
    }
