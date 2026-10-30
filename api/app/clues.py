from typing import TYPE_CHECKING, Annotated, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from app.board import (
    COLUMNS,
    DESKS,
    ROWS,
    Between,
    Board,
    Column,
    Department,
    Desk,
    Direction,
    Group,
    Neighbours,
    Row,
    cell,
)

if TYPE_CHECKING:
    from collections.abc import Container, Iterable, Mapping, Sequence

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


def family_groups(board: Board, family: Family) -> list[Row | Column | Department]:
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
        for group in family_groups(board, self.family):
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
        for group in family_groups(board, family):
            if group != self.group:
                mask &= mine > _count(board.bits(group), self.state, boards)
        return mask


def _is(desk: Desk, state: State, boards: Boards) -> Mask:
    sick: Mask = (boards >> DESKS.index(desk) & 1).astype(np.bool_)
    return sick if state == "sick" else ~sick


class OneOf(_Model):
    """A coworker is one of n sick (or well) in their group, or (None) of 2+."""

    kind: Literal["one_of"] = "one_of"
    desk: Desk
    group: Group
    n: Annotated[int, Field(ge=2)] | None
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        counts = _count(board.bits(self.group), self.state, boards)
        them = counts >= 2 if self.n is None else np.equal(counts, self.n)  # noqa: PLR2004 (one of the: two or more)
        return _is(self.desk, self.state, boards) & them

    def bits(self, board: Board) -> int:
        return board.bits(self.group)


class OnlyOne(_Model):
    """Exactly one row / column / department has exactly n sick (or well)."""

    kind: Literal["only_one"] = "only_one"
    family: Family
    n: Annotated[int, Field(ge=0)]
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        hits = np.zeros(boards.shape, dtype=np.uint8)
        for group in family_groups(board, self.family):
            hits += np.equal(_count(board.bits(group), self.state, boards), self.n)
        return np.equal(hits, 1)


class OnlyOneNeighbours(_Model):
    """Exactly one person in a group has exactly n sick (or well) neighbours."""

    kind: Literal["only_one_neighbours"] = "only_one_neighbours"
    group: Group
    n: Annotated[int, Field(ge=0)]
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        hits = np.zeros(boards.shape, dtype=np.uint8)
        for desk in _desks(board.bits(self.group)):
            near = board.bits(Neighbours(of=desk))
            hits += np.equal(_count(near, self.state, boards), self.n)
        return np.equal(hits, 1)

    def bits(self, board: Board) -> int:
        bits = board.bits(self.group)
        for desk in _desks(bits):
            bits |= board.bits(Neighbours(of=desk))
        return bits


class Overlap(_Model):
    """Exactly n of the sick (or well) in group a are in group b too."""

    kind: Literal["overlap"] = "overlap"
    a: Group
    b: Group
    n: Annotated[int, Field(ge=2)]  # "one of the" would mean two or more in a
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        both = board.bits(self.a) & board.bits(self.b)
        return np.equal(_count(both, self.state, boards), self.n)

    def bits(self, board: Board) -> int:
        return board.bits(self.a) | board.bits(self.b)


class AllIn(_Model):
    """Every sick (or well) person in group a is in group b: the only one (n=1),
    both (n=2), or all (None, at least one)."""

    kind: Literal["all_in"] = "all_in"
    a: Group
    b: Group
    n: Literal[1, 2] | None
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        a = board.bits(self.a)
        outside = np.equal(_count(a & ~board.bits(self.b), self.state, boards), 0)
        counts = _count(a, self.state, boards)
        enough = counts >= 1 if self.n is None else np.equal(counts, self.n)
        return outside & enough

    def bits(self, board: Board) -> int:
        return board.bits(self.a) | board.bits(self.b)


class Connected(_Model):
    """Everyone sick (or well) in a line sits in one unbroken run: both of them
    (n=2), or all of them, at least one (None)."""

    kind: Literal["connected"] = "connected"
    group: Annotated[Row | Column | Between | Direction, Field(discriminator="kind")]
    n: Literal[2] | None
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        runs = np.zeros(boards.shape, dtype=np.uint8)
        before = np.zeros(boards.shape, dtype=np.bool_)
        for desk in _desks(board.bits(self.group)):  # desk order runs along a line
            here = _is(desk, self.state, boards)
            runs += here & ~before
            before = here
        one: Mask = np.equal(runs, 1)
        if self.n is None:
            return one
        return one & np.equal(_count(board.bits(self.group), self.state, boards), 2)

    def bits(self, board: Board) -> int:
        return board.bits(self.group)


type Way = Literal["above", "below", "left", "right"]
_STEP: dict[Way, tuple[int, int]] = {
    "above": (0, -1), "below": (0, 1), "left": (-1, 0), "right": (1, 0),
}  # fmt: skip


def next_desk(desk: Desk, direction: Way) -> Desk | None:
    """The desk directly above, below, left or right of this one; None at the edge."""
    (c, r), (dc, dr) = cell(desk), _STEP[direction]
    if 0 <= c + dc < len(COLUMNS) and 0 <= r + dr < ROWS:
        return DESKS[(r + dr) * len(COLUMNS) + c + dc]
    return None


class Directly(_Model):
    """Everyone (None) / exactly n in a group has a sick (or well) coworker at the
    next desk in one direction; someone at the edge has no one there."""

    kind: Literal["directly"] = "directly"
    group: Group
    direction: Way
    n: Annotated[int, Field(ge=0)] | None
    state: State = "sick"

    def mask(self, board: Board, boards: Boards = BOARDS) -> Mask:
        members = _desks(board.bits(self.group))
        hits = np.zeros(boards.shape, dtype=np.uint8)
        for desk in members:
            if there := next_desk(desk, self.direction):
                hits += _is(there, self.state, boards)
        return np.equal(hits, len(members) if self.n is None else self.n)

    def bits(self, board: Board) -> int:
        bits = board.bits(self.group)
        for desk in _desks(bits):
            if there := next_desk(desk, self.direction):
                bits |= 1 << DESKS.index(there)
        return bits


def _desks(bits: int) -> list[Desk]:
    return [d for i, d in enumerate(DESKS) if bits >> i & 1]


type Clue = Annotated[
    Count
    | Total
    | NoMoreThan
    | Parity
    | More
    | Equal
    | SickVsWell
    | Most
    | OneOf
    | OnlyOne
    | OnlyOneNeighbours
    | Overlap
    | AllIn
    | Connected
    | Directly,
    Field(discriminator="kind"),
]

# Clues about the whole office: a step that needs one makes the day Hard.
WIDE = (Total, NoMoreThan, Most, OnlyOne)


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


def fits(
    masks: Sequence[Mask], liars: Sequence[bool], *, elsewhere: Mask | bool = True
) -> Mask:
    """The boards where the fibber is lying, wherever they are.

    Each mask is a clue said, at least one; a liar is a sick speaker, who could be
    the fibber. Exactly one of their clues is false, or none is and the fibber is
    elsewhere: someone whose clue isn't among these. Everyone else's is true.
    On a day with no fibber, nobody is a liar and every clue is true.
    """
    honest = np.ones_like(masks[0])
    lies = np.zeros(masks[0].shape, dtype=np.uint8)
    for mask, liar in zip(masks, liars, strict=True):
        if liar:
            lies += ~mask
        else:
            honest &= mask
    fit: Mask = honest & ((lies == 1) | ((lies == 0) & elsewhere))
    return fit


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
