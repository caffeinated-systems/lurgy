"""Build days: a hidden solution, and a true clue for each coworker as they're found."""

import argparse
import random
import secrets
import subprocess
from datetime import date, timedelta
from itertools import combinations
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import numpy as np

from app.board import (
    COLUMNS,
    DESKS,
    ROWS,
    Between,
    Board,
    Column,
    Corners,
    Coworker,
    Department,
    Desk,
    Direction,
    Edges,
    Group,
    Neighbours,
    Row,
    cell,
)
from app.cast import iso_monday, load_cast, load_story, quiet_week, story_path
from app.clues import (
    BOARDS,
    EVERYONE,
    WIDE,
    Clue,
    Count,
    Equal,
    Is,
    More,
    Most,
    NoMoreThan,
    OneOf,
    Parity,
    SickVsWell,
    State,
    Total,
    settled,
)
from app.grade import Grade, Step, grade, next_step
from app.week import Day, Difficulty, Generator, Reveal, Week
from app.wording import explanation, wording

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from app.cast import Cast, Member, Story
    from app.clues import Boards, Mask

# Sick coworkers in a solution: never a near-empty or near-full office.
FEWEST_SICK, MOST_SICK = 6, 12
# Clues weighed for each coworker revealed, drawn from every true one.
CANDIDATES = 12
# ponytail: a fixed cap; Easy is the rarest tier, so raise it if Easy runs out.
ATTEMPTS = 2_000
# Coworkers who say a general line in place of a clue on each quiet day.
QUIET_LINES = 2
# Clues that get a joke after them on each day: one or two.
JOKES = (1, 2)
FAMILIES: tuple[Literal["rows", "columns", "departments"], ...] = (
    "rows", "columns", "departments",
)  # fmt: skip
# How often each clue family is drawn for a candidate.
# ponytail: guessed weights; retune after reading a few generated weeks.
WEIGHTS = {"counts": 4, "parity": 1, "comparisons": 1, "one coworker": 1}
STATES: tuple[State, ...] = ("sick", "well")

type Catalogue = dict[str, list[Clue]]


class GenerationError(Exception):
    """No day at the asked difficulty within the attempts allowed."""


def generate_day(  # noqa: PLR0913
    board: Board,
    day: date,
    difficulty: Difficulty,
    rng: random.Random,
    attempts: int = ATTEMPTS,
    *,
    flavour: Mapping[Desk, str] | None = None,
    jokes: Mapping[Desk, Sequence[str]] | None = None,
) -> Day:
    """A day at this difficulty, replayed from scratch before it's returned.

    Coworkers with flavour say it in place of a clue; never the starting one, who
    has to give the office manager something to go on. Jokes are each coworker's
    pool, for one or two clues.
    """
    flavour = flavour or {}
    for _ in range(attempts):
        if (built := _attempt(board, day, difficulty, rng, flavour)) is None:
            continue
        puzzle, order, graded = built
        if graded.difficulty != difficulty:
            continue
        # Guards against generator bugs: a fresh replay, and the grader agreeing.
        if (
            not puzzle.accepts(board, order) or grade(board, puzzle) != graded
        ):  # pragma: no cover
            msg = "a generated day failed its replay"
            raise AssertionError(msg)
        return puzzle.model_copy(
            update={
                "difficulty": difficulty,
                "reveals": _joke(puzzle.reveals, jokes or {}, rng),
            }
        )
    msg = f"no {difficulty} day for {day} in {attempts} attempts"
    raise GenerationError(msg)


def _attempt(
    board: Board,
    day: date,
    difficulty: Difficulty,
    rng: random.Random,
    flavour: Mapping[Desk, str],
) -> tuple[Day, list[tuple[Desk, State]], Grade] | None:
    """One try: reveal coworkers in order until everyone is declared, or stuck."""
    sick = frozenset(rng.sample(DESKS, rng.randint(FEWEST_SICK, MOST_SICK)))
    solution = sum(1 << DESKS.index(d) for d in sick)
    catalogue = _true_clues(board, solution, rng)
    if difficulty == "Easy":  # a whole-board clue is Hard whenever it's needed
        catalogue = {
            f: [c for c in clues if not isinstance(c, WIDE)]
            for f, clues in catalogue.items()
        }

    start = rng.choice([d for d in DESKS if d not in flavour])
    declared: dict[Desk, bool] = {start: start in sick}
    known = _keep(BOARDS, start, solution)  # fits the declarations alone
    alive = known  # fits the clues too
    order: list[tuple[Desk, State]] = []
    clues: dict[Desk, Clue] = {}
    steps: list[Step] = []
    new = [start]
    said: list[Clue] = []
    # Rounds as the grader plays them: everyone just declared speaks, then the
    # fewest clues that force anyone decide who's declared next.
    while True:
        for desk in (d for d in new if d not in flavour):
            clues[desk] = clue = _choose(
                board,
                _candidates(catalogue, rng),
                known=known,
                alive=alive,
                declared=declared,
                rng=rng,
                easy=difficulty == "Easy",
            )
            said.append(clue)
            for family in catalogue.values():  # no one says it twice
                if clue in family:
                    family.remove(clue)
            alive = alive[clue.mask(board, alive)]
        if len(declared) == len(DESKS):
            break
        try:
            step, forced = next_step(
                said, [c.mask(board, known) for c in said], known, declared
            )
        except ValueError:
            return None  # stuck: start again
        steps.append(step)
        new = sorted(forced)
        for d in new:
            declared[d] = d in sick
            order.append((d, "sick" if d in sick else "well"))
            known = _keep(known, d, solution)
    reveals = tuple(
        Reveal(text=flavour[d])
        if d in flavour
        else Reveal(
            clue=clues[d],
            text=wording(board, d, clues[d]),
            explanation=explanation(board, d, clues[d]),
        )
        for d in DESKS
    )
    return (
        Day(date=day, start=start, sick=sick, reveals=reveals),
        order,
        Grade(tuple(steps)),
    )


def _choose(  # noqa: PLR0913
    board: Board,
    candidates: list[Clue],
    *,
    known: Boards,
    alive: Boards,
    declared: dict[Desk, bool],
    rng: random.Random,
    easy: bool,
) -> Clue:
    """A clue that forces someone new.

    Easy wants it to force on its own. Harder days want clues that don't: single-
    clue progress has to stall for a step to need two. Once someone is settled
    but not yet declared, the next round can't get stuck, so any such clue will do.
    """

    def forces(clue: Clue, boards: Boards) -> bool:
        # Only ever asked when no one on these boards is settled yet, so anyone
        # settled after the clue is new.
        return bool(settled(boards[clue.mask(board, boards)], declared))

    # Declarations alone never settle anyone undeclared.
    alone = [c for c in candidates if forces(c, known)]
    if easy:
        return rng.choice(alone or candidates)
    held = [c for c in candidates if c not in alone]
    if settled(alive, declared):
        return rng.choice(held or candidates)
    together = [c for c in held if forces(c, alive)]
    return rng.choice(together or alone or candidates)


def _keep(boards: Boards, desk: Desk, solution: int) -> Boards:
    """The boards where this desk is in its state in the solution."""
    bit = 1 << DESKS.index(desk)
    same: Mask = (boards & np.uint32(bit)) == solution & bit
    return boards[same]


def _candidates(catalogue: Catalogue, rng: random.Random) -> list[Clue]:
    """Clues to weigh: each from a family drawn by WEIGHTS, repeats dropped."""
    families = [f for f, clues in catalogue.items() if clues]
    drawn = rng.choices(families, [WEIGHTS[f] for f in families], k=CANDIDATES)
    return list(dict.fromkeys(rng.choice(catalogue[f]) for f in drawn))


def _true_clues(board: Board, solution: int, rng: random.Random) -> Catalogue:
    """Every clue true of the solution, by family."""
    return {
        "counts": list(_counts(board, solution, rng)),
        "parity": list(_parities(board, solution)),
        "comparisons": list(_comparisons(board, solution)),
        "one coworker": list(_one_coworker(board, solution)),
    }


def _counts(board: Board, solution: int, rng: random.Random) -> Iterator[Clue]:
    """Every count clue true of the solution; "at least" ones at a random strength."""
    for group in _groups(board):
        bits = board.bits(group)
        for state in STATES:
            n = _how_many(bits, solution, state)
            yield Count(group=group, n=n, state=state)
            # "At least" short of everyone: at least two of two reads as both.
            if n:
                most = min(n, bits.bit_count() - 1)
                yield Count(
                    group=group, op="at_least", n=rng.randint(1, most), state=state
                )
    for state in STATES:
        n = _how_many(EVERYONE, solution, state)
        yield Total(n=n, state=state)
        yield Total(op="at_least", n=rng.randint(1, n), state=state)
        # The board with everyone in this state, which passes only a tautology.
        extreme = np.array([EVERYONE if state == "sick" else 0], dtype=np.uint32)
        for family in FAMILIES:
            # The tightest true bound: the fewest n that the solution passes.
            clue = next(
                clue
                for n in range(len(DESKS))
                if (clue := NoMoreThan(family=family, n=n, state=state)).mask(
                    board, np.array([solution], dtype=np.uint32)
                )[0]
            )
            if not clue.mask(board, extreme)[0]:
                yield clue


def _parities(board: Board, solution: int) -> Iterator[Clue]:
    for group in _groups(board):
        for state in STATES:
            odd = _how_many(board.bits(group), solution, state) % 2
            yield Parity(group=group, parity="odd" if odd else "even", state=state)


def _comparisons(board: Board, solution: int) -> Iterator[Clue]:
    """Equal / more between like groups, sick against well, and the most."""
    one = np.array([solution], dtype=np.uint32)
    for state in STATES:
        for a, b in _pairs(board):
            na = _how_many(board.bits(a), solution, state)
            nb = _how_many(board.bits(b), solution, state)
            if na == nb:
                yield Equal(a=a, b=b, state=state)
            else:
                yield (
                    More(a=a, b=b, state=state)
                    if na > nb
                    else More(a=b, b=a, state=state)
                )
        for group in (
            *(Row(row=r) for r in range(1, ROWS + 1)),
            *(Column(column=c) for c in COLUMNS),
            *(Department(name=name) for name in board.departments),
        ):
            if (most := Most(group=group, state=state)).mask(board, one)[0]:
                yield most
    for group in _groups(board):
        sick = _how_many(board.bits(group), solution, "sick")
        well = board.bits(group).bit_count() - sick
        more: State | None = None if sick == well else "sick" if sick > well else "well"
        yield SickVsWell(group=group, more=more)


def _one_coworker(board: Board, solution: int) -> Iterator[Clue]:
    """Each coworker's state, and each one of two or more in a group."""
    for i, desk in enumerate(DESKS):
        state: State = "sick" if solution >> i & 1 else "well"
        yield Is(desk=desk, state=state)
        for group in _groups(board):
            if board.bits(group) >> i & 1:
                n = _how_many(board.bits(group), solution, state)
                if n >= 2:  # noqa: PLR2004 (one of one would just say they're sick)
                    yield OneOf(desk=desk, group=group, n=n, state=state)
                    yield OneOf(desk=desk, group=group, n=None, state=state)


def _pairs(board: Board) -> Iterator[tuple[Group, Group]]:
    """Groups worth comparing: two of a kind, or opposite sides of one coworker."""
    # ponytail: like-for-like only; mixed pairs (my row vs to my right) if days
    # feel samey.
    groups = _groups(board)
    for kind in ("row", "column", "department", "neighbours"):
        yield from combinations([g for g in groups if g.kind == kind], 2)
    for desk in DESKS:
        for x, y in (("above", "below"), ("left", "right")):
            a = Direction(of=desk, direction=x)
            b = Direction(of=desk, direction=y)
            if board.bits(a) and board.bits(b):
                yield a, b


def _how_many(bits: int, solution: int, state: State) -> int:
    sick = (bits & solution).bit_count()
    return sick if state == "sick" else bits.bit_count() - sick


def _groups(board: Board) -> list[Group]:
    """Every group of two or more desks."""
    directions: tuple[Literal["above", "below", "left", "right"], ...] = (
        "above", "below", "left", "right",
    )  # fmt: skip
    groups: list[Group] = [
        Corners(),
        Edges(),
        *(Row(row=r) for r in range(1, ROWS + 1)),
        *(Column(column=c) for c in COLUMNS),
        *(Department(name=name) for name in board.departments),
        *(Neighbours(of=d) for d in DESKS),
        *(Direction(of=d, direction=x) for d in DESKS for x in directions),
        *(
            Between(a=a, b=b)
            for a, b in combinations(DESKS, 2)
            if cell(a)[0] == cell(b)[0] or cell(a)[1] == cell(b)[1]
        ),
    ]
    # ponytail: one-desk groups are the "about one coworker" family, left for #29.
    return [g for g in groups if board.bits(g).bit_count() > 1]


def _joke(
    reveals: tuple[Reveal, ...], jokes: Mapping[Desk, Sequence[str]], rng: random.Random
) -> tuple[Reveal, ...]:
    """The reveals, with a joke after one or two clues from their speakers' pools."""
    funny = [d for d, r in zip(DESKS, reveals, strict=True) if r.clue and jokes.get(d)]
    chosen = rng.sample(funny, min(rng.choice(JOKES), len(funny)))
    return tuple(
        r.model_copy(update={"joke": rng.choice(jokes[d])}) if d in chosen else r
        for d, r in zip(DESKS, reveals, strict=True)
    )


# Monday to Friday.
SCHEDULE: tuple[Difficulty, ...] = ("Easy", "Medium", "Medium", "Hard", "Hard")


def seat(who: Sequence[Member]) -> Board:
    """The booking system seats everyone alphabetically, row by row."""
    return Board(
        coworkers=tuple(
            Coworker(name=m.name, department=m.department)
            for m in sorted(who, key=lambda m: m.name.casefold())
        )
    )


def generate_week(
    cast: Cast, monday: date, seed: int, commit: str, story: Story | None = None
) -> Week:
    """A Week's five days, each from its own generator seeded by the Week's seed.

    A story says who's in and who speaks; a quiet week picks both.
    """
    # ponytail: random, not secrets: the seed is the secret, and it must replay.
    rngs = [random.Random(f"{seed}:{i}") for i in range(len(SCHEDULE))]  # noqa: S311
    who = story.who if story else quiet_week(cast, random.Random(f"{seed}:who"))  # noqa: S311
    board = seat(who)
    desk = {c.name: d for d, c in zip(DESKS, board.coworkers, strict=True)}
    days = []
    for i, difficulty in enumerate(SCHEDULE):
        rng = rngs[i]
        if story:
            said = story.days[i]
        else:
            chatty = [m for m in who if m.lines]
            said = {
                m.name: rng.choice(m.lines)
                for m in rng.sample(chatty, min(QUIET_LINES, len(chatty)))
            }
        days.append(
            generate_day(
                board,
                monday + timedelta(days=i),
                difficulty,
                rng,
                flavour={desk[name]: line for name, line in said.items()},
                jokes={desk[m.name]: m.jokes for m in who},
            )
        )
    return Week(
        board=board, days=tuple(days), generator=Generator(commit=commit, seed=seed)
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.generate",
        description="Build a Week file. Prints only where it went and how hard.",
    )
    parser.add_argument("week", type=iso_monday, help="the ISO week, e.g. 2026-W45")
    parser.add_argument("-o", "--out", type=Path, required=True, help="the file")
    parser.add_argument(
        "--stories", type=Path, default=Path("../stories"), help="cast and stories"
    )
    args = parser.parse_args(argv)

    cast = load_cast(args.stories / "cast.md")
    path = story_path(args.stories, args.week)
    story = load_story(path, cast) if path.exists() else None
    # A dirty tree, untracked files included, can't rebuild the Week from its commit.
    commit = _git("rev-parse", "HEAD") + (
        "-dirty" if _git("status", "--porcelain") else ""
    )
    week = generate_week(cast, args.week, secrets.randbits(128), commit, story)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(week.model_dump_json(indent=2) + "\n")
    tiers = ", ".join(str(d.difficulty) for d in week.days)
    quiet = "" if story else ", a quiet week"
    print(f"wrote {args.out} ({tiers}{quiet})")  # noqa: T201 (the CLI's one line)


def _git(*args: str) -> str:
    return subprocess.run(  # noqa: S603 (fixed arguments, never user input)
        ["git", *args],  # noqa: S607 (git from PATH, as in CI)
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


if __name__ == "__main__":  # pragma: no cover
    main()
