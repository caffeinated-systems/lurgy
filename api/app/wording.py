"""What a clue says, and its plain explanation, in the speaker's voice."""

from app.board import (
    COLUMNS,
    DESKS,
    ROWS,
    Between,
    Board,
    Column,
    Corners,
    Department,
    Desk,
    Direction,
    Edges,
    Group,
    Neighbours,
    Row,
    cell,
)
from app.clues import (
    Clue,
    Count,
    Equal,
    Is,
    More,
    Most,
    NoMoreThan,
    OneOf,
    Op,
    Parity,
    SickVsWell,
    State,
    Total,
)

NUMBERS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty",
)  # fmt: skip

_SIDES = {"left": "to the left of", "right": "to the right of"}
_MY_SIDES = {"left": "to my left", "right": "to my right"}
_OTHER: dict[State, State] = {"sick": "well", "well": "sick"}


def wording(board: Board, speaker: Desk, clue: Clue) -> str:  # noqa: C901, PLR0911 (a case per kind)
    """The clue as the speaker says it: "Two of my neighbours are sick."."""
    match clue:
        case Count(group=group, op=op, n=n, state=state):
            return _sentence(op, n, state, _where(board, speaker, group))
        case Total(op=op, n=n, state=state):
            return _sentence(op, n, state, "in the office")
        case NoMoreThan(family=family, n=n, state=state):
            one = family.removesuffix("s")
            if n == 0:
                return f"No {one} has any {state} people."
            return f"No {one} has more than {_people(n, state)}."
        case Parity(group=group, parity=parity, state=state):
            return (
                f"An {parity} number of people {_where(board, speaker, group)}"
                f" are {state}."
            )
        case Equal(a=a, b=b, state=state):
            return (
                f"There are as many {state} people {_where(board, speaker, a)}"
                f" as {state} people {_where(board, speaker, b)}."
            )
        case More(a=a, b=b, state=state):
            return (
                f"There are more {state} people {_where(board, speaker, a)}"
                f" than {state} people {_where(board, speaker, b)}."
            )
        case SickVsWell(group=group, more=more):
            where = _where(board, speaker, group)
            if more is None:
                return f"Half the people {where} are sick."
            return f"More people {where} are {more} than {_OTHER[more]}."
        case Most(group=group, state=state):
            return f"{_noun(board, speaker, group)[0]} has the most {state} people."
        case Is(desk=desk, state=state):
            return f"{_subject(board, speaker, desk)} {state}."
        case OneOf(desk=desk, group=group, n=n, state=state):  # pragma: no branch
            count = "the" if n is None else NUMBERS[n]
            return (
                f"{_subject(board, speaker, desk)} one of {count} {state} people"
                f" {_where(board, speaker, group)}."
            )


def explanation(board: Board, speaker: Desk, clue: Clue) -> str:  # noqa: C901, PLR0911 (a case per kind)
    """The clue spelled out desk by desk, with nothing left implied."""
    match clue:
        case Count(group=group, op=op, n=n, state=state):
            return f"{_members(board, speaker, group)}: {_of_them(op, n, state)}."
        case Total(op=op, n=n, state=state):
            everyone = NUMBERS[len(DESKS)]
            return (
                f"There are {everyone} people in the office: {_of_them(op, n, state)}."
            )
        case NoMoreThan(family=family, n=n, state=state):
            groups = {
                "rows": f"Rows 1 to {ROWS}",
                "columns": f"Columns {COLUMNS[0]} to {COLUMNS[-1]}",
                "departments": _list(board.departments),
            }[family]
            if n == 0:
                return f"{groups} each have no {state} people."
            return f"{groups} each have at most {_people(n, state)}."
        case Parity(group=group, parity=parity, state=state):
            size = board.bits(group).bit_count()
            could = _list(
                [NUMBERS[k] for k in range(parity == "odd", size + 1, 2)], "or"
            )
            return (
                f"{_members(board, speaker, group)}:"
                f" an {parity} number of them ({could}) are {state}."
            )
        case Equal(a=a, b=b, state=state):
            return (
                f"{_members(board, speaker, a)}. {_members(board, speaker, b)}."
                f" As many of the first are {state} as of the second,"
                " and that can be none."
            )
        case More(a=a, b=b, state=state):
            return (
                f"{_members(board, speaker, a)}. {_members(board, speaker, b)}."
                f" More of the first are {state} than of the second,"
                " which can have none."
            )
        case SickVsWell(group=group, more=more):
            members = _members(board, speaker, group)
            if more is None:
                half = NUMBERS[board.bits(group).bit_count() // 2]
                return f"{members}: half of them ({half}) are sick, and half are well."
            return f"{members}: more of them are {more} than {_OTHER[more]}."
        case Most(group=group, state=state):
            noun = _noun(board, speaker, group)[0]
            return f"{noun} has more {state} people than any other {group.kind}."
        case Is(desk=desk, state=state):
            who = (
                "me: I am"
                if desk == speaker
                else f"{_who(board, speaker, desk)}, who is"
            )
            return f"This is only about {who} {state}."
        case OneOf(desk=desk, group=group, n=n, state=state):  # pragma: no branch
            return (
                f"{_members(board, speaker, group)}:"
                f" {_subject(board, speaker, desk)} {state}, and {_others(n)}."
            )


def _sentence(op: Op, n: int, state: State, where: str) -> str:
    if op == "exactly" and n == 0:
        return f"No one {where} is {state}."
    people = "person" if n == 1 else "people"
    verb = "is" if n == 1 else "are"
    at_least = "at least " if op == "at_least" else ""
    return _capital(f"{at_least}{NUMBERS[n]} {people} {where} {verb} {state}.")


def _people(n: int, state: State) -> str:
    return f"{NUMBERS[n]} {state} {'person' if n == 1 else 'people'}"


def _of_them(op: Op, n: int, state: State) -> str:
    if op == "exactly" and n == 0:
        return f"none of them is {state}"
    verb = "is" if n == 1 else "are"
    return f"{op.replace('_', ' ')} {NUMBERS[n]} of them {verb} {state}"


def _who(board: Board, speaker: Desk, desk: Desk) -> str:
    return "me" if desk == speaker else board.coworkers[DESKS.index(desk)].name


def _others(n: int | None) -> str:
    """Everyone else in a "one of" clue's state: "so are exactly two others"."""
    if n is None:
        return "so is at least one other"
    if n == 2:  # noqa: PLR2004 (this coworker and one other)
        return "so is exactly one other"
    return f"so are exactly {NUMBERS[n - 1]} others"


def _subject(board: Board, speaker: Desk, desk: Desk) -> str:
    """Someone and their "is": "Kev is", or "I am" for the speaker."""
    return "I am" if desk == speaker else f"{_who(board, speaker, desk)} is"


def _whose(board: Board, speaker: Desk, desk: Desk) -> str:
    return "my" if desk == speaker else f"{_who(board, speaker, desk)}'s"


def _where(board: Board, speaker: Desk, group: Group) -> str:  # noqa: PLR0911
    """Where the people a clue counts are: "in my row", "between Erin and Kev"."""
    column, row = cell(speaker)
    match group:
        case Row(row=r):
            return "in my row" if r == row + 1 else f"in row {r}"
        case Column(column=c):
            return "in my column" if c == COLUMNS[column] else f"in column {c}"
        case Neighbours(of=of):
            return f"among {_whose(board, speaker, of)} neighbours"
        case Between(a=a, b=b):
            return f"between {_who(board, speaker, a)} and {_who(board, speaker, b)}"
        case Direction(of=of, direction=d) if of == speaker:
            return _MY_SIDES.get(d, f"{d} me")
        case Direction(of=of, direction=d):
            return f"{_SIDES.get(d, d)} {_who(board, speaker, of)}"
        case Corners():
            return "in the corners"
        case Edges():
            return "on the edges"
        case Department(name=name):  # pragma: no branch (the match is exhaustive)
            mine = board.coworkers[DESKS.index(speaker)].department == name
            return "in my department" if mine else f"in {name}"


def _noun(board: Board, speaker: Desk, group: Group) -> tuple[str, bool]:
    """A group as the subject of a sentence, and whether it takes "are"."""
    where = _where(board, speaker, group)
    match group:
        case Row(row=r):
            return ("My row" if where == "in my row" else f"Row {r}"), False
        case Column(column=c):
            return ("My column" if where == "in my column" else f"Column {c}"), False
        case Neighbours(of=of):
            return _capital(f"{_whose(board, speaker, of)} neighbours"), True
        case Department(name=name):
            return ("My department" if where == "in my department" else name), False
        case Corners() | Edges():
            return f"The {where.split()[-1]}", True
        case Between() | Direction():  # pragma: no branch (the match is exhaustive)
            return f"The people {where}", True


def _members(board: Board, speaker: Desk, group: Group) -> str:
    """A group and who is in it: "My row is Imogen, Kev, Linda and me"."""
    noun, plural = _noun(board, speaker, group)
    names = _names(board, speaker, board.bits(group))
    return f"{noun} {'are' if plural else 'is'} {names}"


def _names(board: Board, speaker: Desk, bits: int) -> str:
    """Everyone in the desks, in desk order, but the speaker last: "…, Kev and me"."""
    desks = [d for i, d in enumerate(DESKS) if bits >> i & 1]
    desks.sort(key=lambda d: d == speaker)
    return _list([_who(board, speaker, d) for d in desks])


def _list(items: list[str], last: str = "and") -> str:
    return (
        items[0] if len(items) == 1 else f"{', '.join(items[:-1])} {last} {items[-1]}"
    )


def _capital(text: str) -> str:
    return text[0].upper() + text[1:]
