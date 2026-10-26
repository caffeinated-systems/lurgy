"""Build days: a hidden solution, and a true clue for each coworker as they're found."""

import argparse
import random
import secrets
import subprocess
from datetime import date, datetime, timedelta
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
    Department,
    Desk,
    Direction,
    Edges,
    Group,
    Neighbours,
    Row,
    cell,
)
from app.cast import STUB_BOARD
from app.clues import BOARDS, Clue, Count, NoMoreThan, State, Total, settled
from app.grade import Grade, Step, next_step
from app.week import Day, Difficulty, Generator, Reveal, Week
from app.wording import explanation, wording

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from app.clues import Boards, Mask

# Sick coworkers in a solution: never a near-empty or near-full office.
FEWEST_SICK, MOST_SICK = 6, 12
# Clues weighed for each coworker revealed, drawn from every true one.
CANDIDATES = 12
# ponytail: a fixed cap; Easy is the rarest tier, so raise it if Easy runs out.
ATTEMPTS = 2_000
FAMILIES: tuple[Literal["rows", "columns", "departments"], ...] = (
    "rows", "columns", "departments",
)  # fmt: skip


class GenerationError(Exception):
    """No day at the asked difficulty within the attempts allowed."""


def generate_day(
    board: Board,
    day: date,
    difficulty: Difficulty,
    rng: random.Random,
    attempts: int = ATTEMPTS,
) -> Day:
    """A day at this difficulty, replayed from scratch before it's returned."""
    for _ in range(attempts):
        if (built := _attempt(board, day, difficulty, rng)) is None:
            continue
        puzzle, order, graded = built
        if not puzzle.accepts(board, order):  # pragma: no cover (a generator bug)
            msg = "a generated day failed its replay"
            raise AssertionError(msg)
        if graded.difficulty == difficulty:
            return puzzle.model_copy(update={"difficulty": difficulty})
    msg = f"no {difficulty} day for {day} in {attempts} attempts"
    raise GenerationError(msg)


def _attempt(
    board: Board, day: date, difficulty: Difficulty, rng: random.Random
) -> tuple[Day, list[tuple[Desk, State]], Grade] | None:
    """One try: reveal coworkers in order until everyone is declared, or stuck."""
    sick = frozenset(rng.sample(DESKS, rng.randint(FEWEST_SICK, MOST_SICK)))
    solution = sum(1 << DESKS.index(d) for d in sick)
    catalogue = list(_true_clues(board, solution, rng))
    if difficulty == "Easy":  # a whole-board clue is Hard whenever it's needed
        catalogue = [c for c in catalogue if isinstance(c, Count)]

    start = rng.choice(DESKS)
    declared: dict[Desk, bool] = {start: start in sick}
    known = _keep(BOARDS, start, solution)  # fits the declarations alone
    alive = known  # fits the clues too
    order: list[tuple[Desk, State]] = []
    clues: dict[Desk, Clue] = {}
    steps: list[Step] = []
    new = [start]
    # Rounds as the grader plays them: everyone just declared speaks, then the
    # fewest clues that force anyone decide who's declared next.
    while True:
        for desk in new:
            clues[desk] = clue = _choose(
                board,
                rng.sample(catalogue, CANDIDATES),
                known=known,
                alive=alive,
                declared=declared,
                rng=rng,
                easy=difficulty == "Easy",
            )
            alive = alive[clue.mask(board, alive)]
        if len(declared) == len(DESKS):
            break
        said = list(clues.values())
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
        Reveal(
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

    Easy wants it to force on its own; harder days want it to need earlier clues,
    since every clue forcing alone grades Easy.
    """

    def forces(clue: Clue, boards: Boards) -> bool:
        return bool(settled(boards[clue.mask(board, boards)], declared))

    alone = [c for c in candidates if forces(c, known)]
    if easy:
        return rng.choice(alone or candidates)
    together = [c for c in candidates if c not in alone and forces(c, alive)]
    return rng.choice(together or alone or candidates)


def _keep(boards: Boards, desk: Desk, solution: int) -> Boards:
    """The boards where this desk is in its state in the solution."""
    bit = 1 << DESKS.index(desk)
    same: Mask = (boards & np.uint32(bit)) == solution & bit
    return boards[same]


def _true_clues(board: Board, solution: int, rng: random.Random) -> Iterator[Clue]:
    """Every count clue true of the solution; "at least" ones at a random strength."""
    states: tuple[State, ...] = ("sick", "well")
    for group in _groups(board):
        bits = board.bits(group)
        for state in states:
            n = _how_many(bits, solution, state)
            yield Count(group=group, n=n, state=state)
            # "At least" short of everyone: at least two of two reads as both.
            if n:
                most = min(n, bits.bit_count() - 1)
                yield Count(
                    group=group, op="at_least", n=rng.randint(1, most), state=state
                )
    for state in states:
        n = _how_many(2 ** len(DESKS) - 1, solution, state)
        yield Total(n=n, state=state)
        yield Total(op="at_least", n=rng.randint(1, n), state=state)
        for family in FAMILIES:
            # The tightest true bound: the fewest n that the solution passes.
            yield next(
                clue
                for n in range(len(DESKS))
                if (clue := NoMoreThan(family=family, n=n, state=state)).mask(
                    board, np.array([solution], dtype=np.uint32)
                )[0]
            )


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


# Monday to Friday.
SCHEDULE: tuple[Difficulty, ...] = ("Easy", "Medium", "Medium", "Hard", "Hard")


def generate_week(board: Board, monday: date, seed: int, commit: str) -> Week:
    """A Week's five days, each from its own generator seeded by the Week's seed."""
    days = [monday + timedelta(days=i) for i in range(len(SCHEDULE))]
    return Week(
        board=board,
        days=tuple(
            # ponytail: random, not secrets: the seed is the secret, and it must replay.
            generate_day(board, day, difficulty, random.Random(f"{seed}:{day}"))  # noqa: S311
            for day, difficulty in zip(days, SCHEDULE, strict=True)
        ),
        generator=Generator(commit=commit, seed=seed),
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.generate",
        description="Build a Week file. Prints only where it went and how hard.",
    )
    parser.add_argument("week", type=_monday, help="the ISO week, e.g. 2026-W45")
    parser.add_argument("-o", "--out", type=Path, required=True, help="the file")
    args = parser.parse_args(argv)

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607 (git from PATH, as in CI)
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    week = generate_week(STUB_BOARD, args.week, secrets.randbits(128), commit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(week.model_dump_json(indent=2) + "\n")
    tiers = ", ".join(str(d.difficulty) for d in week.days)
    print(f"wrote {args.out} ({tiers})")  # noqa: T201 (the CLI's one line)


def _monday(week: str) -> date:
    """The Monday of an ISO week such as 2026-W45."""
    return datetime.strptime(f"{week}-1", "%G-W%V-%u").date()  # noqa: DTZ007 (a date)


if __name__ == "__main__":  # pragma: no cover
    main()
