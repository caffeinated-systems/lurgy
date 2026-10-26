from typing import TYPE_CHECKING, Annotated, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from app.board import COLUMNS, DESKS, ROWS, Board, Column, Department, Desk, Group, Row

if TYPE_CHECKING:
    from collections.abc import Container, Iterable, Mapping

# Every possible board: bit i set means the coworker at desk i is sick.
BOARDS = np.arange(2 ** len(DESKS), dtype=np.uint32)
EVERYONE = 2 ** len(DESKS) - 1

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


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True)


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
    family: Literal["rows", "columns", "departments"]
    n: Annotated[int, Field(ge=0)]
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        groups: list[Group]
        match self.family:
            case "rows":
                groups = [Row(row=r) for r in range(1, ROWS + 1)]
            case "columns":
                groups = [Column(column=c) for c in COLUMNS]
            case "departments":  # pragma: no branch (the match is exhaustive)
                groups = [Department(name=d) for d in board.departments]
        mask = np.ones(boards.shape, dtype=np.bool_)
        for group in groups:
            mask &= _count(board.bits(group), self.state, boards) <= self.n
        return mask


class More(_Model):
    """More sick (or well) in group a than in group b."""

    kind: Literal["more"] = "more"
    a: Group
    b: Group
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        a = _count(board.bits(self.a), self.state, boards)
        return a > _count(board.bits(self.b), self.state, boards)


type Clue = Annotated[Count | Total | NoMoreThan | More, Field(discriminator="kind")]

# Clues about the whole office: a step that needs one makes the day Hard.
WIDE = (Total, NoMoreThan)


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
