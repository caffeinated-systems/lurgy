import random
import secrets
from dataclasses import replace
from datetime import UTC, date, datetime
from functools import cache
from typing import TYPE_CHECKING, get_args

import pytest

from app import generate
from app.board import DESKS, Board, Desk, Row
from app.cast import DAYS, fits, load_cast, load_overtime, load_story
from app.clues import (
    BOARDS,
    WIDE,
    Clue,
    Connected,
    Count,
    Directly,
    Overlap,
    Parity,
    next_desk,
)
from app.generate import (
    FEWEST_SICK,
    FORMS,
    MOST_SICK,
    QUIET_LINES,
    SCHEDULE,
    GenerationError,
    _candidates,
    _choose,
    _connections,
    _directions,
    _form,
    _how_many,
    _overlaps,
    _speak,
    _true_clues,
    generate_day,
    generate_week,
    main,
)
from app.grade import grade, hint, next_step
from app.week import Call, Reveal, Week, load_days
from tests.factories import MONDAY, SAMPLE_BOARD, STORIES, board_index, desks

if TYPE_CHECKING:
    from pathlib import Path

    from app.clues import Boards
    from app.week import Difficulty

CAST = load_cast(STORIES / "cast.md")
STORY = load_story(STORIES / "2026-W45.md", CAST)
OVERTIME = load_overtime(STORIES / "overtime.md")


@pytest.fixture
def weekdays(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monday to Friday only: Overtime takes most of a Week's build time."""
    monkeypatch.setattr(generate, "SCHEDULE", SCHEDULE[: len(DAYS)])


@cache
def story_week() -> Week:
    return generate_week(CAST, date(2026, 11, 2), 1, "0" * 40, STORY, overtime=OVERTIME)


@pytest.mark.parametrize("difficulty", ["Easy", "Medium", "Hard"])
def test_a_day_grades_at_the_difficulty_asked(difficulty: Difficulty) -> None:
    day = generate_day(SAMPLE_BOARD, MONDAY, difficulty, random.Random(2026))

    assert grade(SAMPLE_BOARD, day).difficulty == difficulty
    if difficulty == "Easy":  # a whole-board clue would make it Hard
        assert not any(isinstance(r.clue, WIDE) for r in day.reveals)


def test_every_coworker_says_a_true_clue_in_words() -> None:
    day = generate_day(SAMPLE_BOARD, MONDAY, "Medium", random.Random(7))

    solution = board_index(set(day.sick))
    assert FEWEST_SICK <= len(day.sick) <= MOST_SICK
    for reveal in day.reveals:
        assert reveal.clue is not None
        assert reveal.clue.mask(SAMPLE_BOARD)[solution], reveal.clue
        assert reveal.text.endswith(".")
        assert reveal.explanation
    said = [r.clue for r in day.reveals]
    assert len(set(said)) == len(said), "a clue said twice"


def test_the_same_seed_builds_the_same_day() -> None:
    first = generate_day(SAMPLE_BOARD, MONDAY, "Easy", random.Random(1))

    assert generate_day(SAMPLE_BOARD, MONDAY, "Easy", random.Random(1)) == first


def test_running_out_of_attempts_fails() -> None:
    with pytest.raises(GenerationError, match="no Hard day"):
        generate_day(SAMPLE_BOARD, MONDAY, "Hard", random.Random(1), attempts=0)


def test_the_cli_writes_a_week_that_loads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(secrets, "randbits", lambda _: 2026)
    out = tmp_path / "2026-W45.json"

    main(["2026-W45", "-o", str(out), "--stories", str(STORIES)])

    days = load_days(tmp_path)
    assert sorted(days) == [date(2026, 11, d) for d in range(2, 9)]
    assert [day.difficulty for _, day in days.values()] == list(SCHEDULE)
    week = Week.model_validate_json(out.read_bytes())
    assert week.generator is not None
    assert week.generator.seed == 2026  # noqa: PLR2004
    # Only where it went and how hard: no clue, solution or seed.
    assert capsys.readouterr().out == (
        f"wrote {out} (Easy, Medium, Medium, Hard, Hard, Medium, Hard)\n"
    )


@pytest.mark.usefixtures("weekdays")
def test_the_cli_leaves_a_built_week_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "2026-W45.json"
    out.write_text("built\n")

    main(["2026-W45", "-o", str(out), "--stories", str(STORIES)])

    assert out.read_text() == "built\n"
    assert capsys.readouterr().out == "2026-W45 is already built\n"


@pytest.mark.usefixtures("weekdays")
def test_the_cli_rebuilds_a_week_until_it_starts_anywhere(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "2026-W45.json"
    out.write_text("built\n")
    args = ["2026-W45", "-o", str(out), "--stories", str(STORIES), "--rebuild"]
    # Monday 2 November starts at 10:00 UTC on the Sunday, in UTC+14.
    monkeypatch.setattr(
        generate, "utc_now", lambda: datetime(2026, 11, 1, 9, 59, tzinfo=UTC)
    )

    main(args)

    assert Week.model_validate_json(out.read_bytes()).days
    monkeypatch.setattr(
        generate, "utc_now", lambda: datetime(2026, 11, 1, 10, tzinfo=UTC)
    )
    out.write_text("built\n")
    with pytest.raises(SystemExit) as refused:
        main(args)
    assert refused.value.code == 1
    assert capsys.readouterr().err == "2026-W45 has started, so it can't be rebuilt\n"
    assert out.read_text() == "built\n"


@pytest.mark.usefixtures("weekdays")
def test_the_cli_builds_a_quiet_week_without_a_story(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "2026-W46.json"

    main(["2026-W46", "-o", str(out), "--stories", str(STORIES)])

    assert capsys.readouterr().out.endswith(", a quiet week)\n")
    week = Week.model_validate_json(out.read_bytes())
    assert fits(CAST[c.name] for c in week.board.coworkers)
    for day in week.days:
        flavour = [r.text for r in day.reveals if r.clue is None]
        # Idle coworkers add jokes and lines to the two quiet lines.
        assert len([x for x in flavour if x.endswith("'s line.")]) >= QUIET_LINES
        assert all(x.endswith(("'s line.", "'s joke.")) for x in flavour)


def test_the_same_seed_builds_the_same_week() -> None:
    commit = "0" * 40

    first = story_week()

    assert (
        generate_week(CAST, date(2026, 11, 2), 1, commit, STORY, overtime=OVERTIME)
        == first
    )
    _seats_the_story_and_gives_speakers_their_lines(first)


def _seats_the_story_and_gives_speakers_their_lines(week: Week) -> None:
    names = [c.name for c in week.board.coworkers]
    assert names == sorted(m.name for m in STORY.who)
    for day, said in zip(week.days[: len(DAYS)], STORY.days, strict=True):
        flavour = {
            names[DESKS.index(d)]: day.reveal(d).text
            for d in DESKS
            if day.reveal(d).clue is None
        }
        assert flavour.items() >= said.items()
        for name, text in flavour.items() - said.items():  # idle: a joke or line
            assert text in {f"{name}'s joke.", f"{name}'s line."}
        assert names[DESKS.index(day.start)] not in said
        jokes = [(d, r.joke) for d, r in zip(DESKS, day.reveals, strict=True) if r.joke]
        assert 1 <= len(jokes) <= 2  # noqa: PLR2004
        for desk, joke in jokes:
            assert day.reveal(desk).clue is not None
            assert joke == f"{names[DESKS.index(desk)]}'s joke."


def test_every_kind_of_clue_is_generated_and_true() -> None:
    solution = board_index({"A1", "B3", "C3", "D2", "A5", "B5", "C4"})

    catalogue = _true_clues(SAMPLE_BOARD, solution, random.Random(3))

    assert set(catalogue) == {x for xs in FORMS.values() for x in xs}
    clues = [c for family in catalogue.values() for c in family]
    kinds = get_args(get_args(Clue.__value__)[0])
    assert {c.kind for c in clues} == {k.model_fields["kind"].default for k in kinds}
    for clue in clues:
        assert clue.mask(SAMPLE_BOARD)[solution], clue


def test_every_form_gets_drawn() -> None:
    solution = board_index({"D1", "D2", "D3", "A5", "B5"})  # column D has the most
    catalogue = _true_clues(SAMPLE_BOARD, solution, random.Random(3))
    rng = random.Random(4)

    drawn = {_form(c) for _ in range(100) for c in _candidates(catalogue, rng)}

    assert drawn == set(catalogue)


def test_a_clue_that_tells_nothing_new_is_never_chosen() -> None:
    known = BOARDS[(BOARDS & 1) == 1]  # Aisha (A1) is declared sick
    said = Count(group=Row(row=1), op="at_least", n=0)  # true of every board
    news = Parity(group=Row(row=2), parity="odd")

    for seed in range(20):
        chosen = _choose(
            SAMPLE_BOARD,
            [said, news],
            {},
            known=known,
            alive=known,
            declared={"A1": True},
            rng=random.Random(seed),
            easy=True,
        )
        assert chosen == news


def test_a_clue_that_tells_nothing_new_is_swapped_for_one_that_does() -> None:
    known = BOARDS[(BOARDS & 1) == 1]  # Aisha (A1) is declared sick
    alive = known[Parity(group=Row(row=2), parity="odd").mask(SAMPLE_BOARD, known)]
    stale = Parity(group=Row(row=2), parity="odd")  # already said
    news = Parity(group=Row(row=3), parity="odd")

    def choose(catalogue: dict[str, list[Clue]]) -> Clue | None:
        return _choose(
            SAMPLE_BOARD,
            [stale],
            catalogue,
            known=known,
            alive=alive,
            declared={"A1": True},
            rng=random.Random(1),
            easy=False,
        )

    assert choose({"parity": [stale, news]}) == news
    assert choose({"parity": [stale]}) is None


def test_every_clue_tells_something_new_when_it_is_said() -> None:
    week = story_week()

    for day in week.days[: len(DAYS)]:  # Overtime has its own tests
        declared, said, new = {day.start}, list[Clue](), [day.start]
        while True:
            for desk in new:
                if clue := day.reveal(desk).clue:
                    alive = _fits(week.board, declared, day.sick, said)
                    assert not clue.mask(week.board, alive).all(), (day.date, desk)
                    said.append(clue)
            if len(declared) == len(DESKS):
                break
            known = _fits(week.board, declared, day.sick, [])
            masks = [c.mask(week.board, known) for c in said]
            _, forced, _ = next_step(said, masks, known, declared)
            new = sorted(forced)
            declared |= forced
    # The fixture cast has a joke and a line each, so someone is always idle.
    idle = [r.text for d in week.days for r in d.reveals if r.clue is None]
    assert any(text.endswith("'s joke.") for text in idle)


def _fits(
    board: Board, declared: set[Desk], sick: frozenset[Desk], said: list[Clue]
) -> Boards:
    """The boards the declarations and the clues said so far allow."""
    bits = sum(1 << DESKS.index(d) for d in declared)
    sick_bits = sum(1 << DESKS.index(d) for d in declared & sick)
    boards: Boards = BOARDS[(BOARDS & bits) == sick_bits]
    for clue in said:
        boards = boards[clue.mask(board, boards)]
    return boards


@pytest.mark.usefixtures("weekdays")
def test_nobody_repeats_themselves_in_a_week() -> None:
    # Someone speaks once a day, so five things each means no repeat is ever needed.
    cast = {
        name: replace(
            m,
            jokes=tuple(f"{name}'s joke {i}." for i in range(2)),
            lines=tuple(f"{name}'s line {i}." for i in range(3)),
        )
        for name, m in CAST.items()
    }

    week = generate_week(cast, date(2026, 11, 9), 1, "0" * 40, overtime=OVERTIME)

    names = [c.name for c in week.board.coworkers]
    said: dict[str, list[str]] = {name: [] for name in names}
    for day in week.days:
        for d, r in zip(DESKS, day.reveals, strict=True):
            said[names[DESKS.index(d)]] += [r.text] * (r.clue is None) + [r.joke or ""]
    for name, texts in said.items():
        spoken = [t for t in texts if t]
        assert len(spoken) == len(set(spoken)), name


def test_nobody_repeats_themselves_until_they_run_out() -> None:
    reveal = Reveal(text="...")
    told: set[str] = set()
    jokes: dict[Desk, tuple[str, ...]] = {"A1": ("a", "b")}
    lines: dict[Desk, tuple[str, ...]] = {"A1": ("l",)}

    def say(seed: int) -> str:
        reveals = (reveal,) * len(DESKS)
        rng = random.Random(seed)
        return _speak(reveals, {"A1"}, jokes=jokes, lines=lines, told=told, rng=rng)[
            0
        ].text

    said = [say(i) for i in range(4)]

    assert sorted(said[:2]) == ["a", "b"]
    assert said[2] == "l"
    assert said[3] in {"a", "b"}


def test_overlaps_never_give_a_coworker_away_or_hide_a_count() -> None:
    solution = board_index({"A1", "B3", "C3", "D2", "A5", "B5", "C4"})

    for clue in _overlaps(SAMPLE_BOARD, solution):
        a, b = SAMPLE_BOARD.bits(clue.a), SAMPLE_BOARD.bits(clue.b)  # type: ignore[union-attr]
        if isinstance(clue, Overlap):
            # "two of the" is short of all of them, and b isn't inside a
            total = _how_many(a, solution, clue.state)
            assert clue.n < total, clue
            assert b & ~a, clue
        else:
            # never "the only sick person in row 2 is in column B"
            assert (a & b).bit_count() > 1, clue


def test_connected_and_directional_clues_keep_to_their_rules() -> None:
    solution = board_index({"A1", "B1", "B3", "C3", "D2", "A5", "B5", "C4"})

    for clue in _connections(SAMPLE_BOARD, solution):
        assert isinstance(clue, Connected)
        bits = SAMPLE_BOARD.bits(clue.group)
        n = _how_many(bits, solution, clue.state)
        assert bits.bit_count() >= 3, clue  # noqa: PLR2004 (a line of three or more)
        assert n >= 2, clue  # noqa: PLR2004 (two or more to connect)
        assert clue.n == (2 if n == 2 else None), clue  # noqa: PLR2004
    for clue in _directions(SAMPLE_BOARD, solution):
        assert isinstance(clue, Directly)
        there = [
            nxt
            for d in desks(SAMPLE_BOARD.bits(clue.group))
            if (nxt := next_desk(d, clue.direction))
        ]
        assert len(there) >= 2, clue  # noqa: PLR2004 (one desk there would name them)


def test_the_weekend_is_overtime_with_a_fibber_who_lies() -> None:
    week = story_week()
    names = [c.name for c in week.board.coworkers]

    saturday, sunday = week.days[len(DAYS) :]
    assert (saturday.date, sunday.date) == (date(2026, 11, 7), date(2026, 11, 8))
    assert (saturday.difficulty, sunday.difficulty) == ("Medium", "Hard")
    for day in (saturday, sunday):
        assert day.fibber in day.sick
        solution = board_index(set(day.sick))
        for desk in DESKS:
            if clue := day.reveal(desk).clue:
                # Everyone tells the truth but the fibber.
                assert clue.mask(week.board)[solution] == (desk != day.fibber), desk
        # The story has ended: everyone says overtime lines and jokes.
        said = [r.text for r in day.reveals if r.clue is None]
        said += [r.joke for r in day.reveals if r.joke]
        assert set(said) <= {*OVERTIME.lines, *OVERTIME.jokes}
        assert not any(t.startswith(tuple(names)) for t in said)


def test_hints_walk_an_overtime_day_to_calling_bs() -> None:
    week = story_week()
    day = week.days[-1]
    steps: list[tuple[Desk, Call]] = []
    while len(steps) < len(DESKS):  # everyone but the starting coworker, and BS
        _, coworker = hint(week.board, day, steps)
        declared = coworker in {d for d, _ in steps} | {day.start}
        steps.append((coworker, "fibber" if declared else day.state(coworker)))

    assert (day.fibber, "fibber") in steps
    assert day.accepts(week.board, steps)
