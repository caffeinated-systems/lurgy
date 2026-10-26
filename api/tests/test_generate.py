import random
import secrets
from datetime import date
from typing import TYPE_CHECKING, get_args

import pytest

from app.board import DESKS, Row
from app.cast import fits, load_cast, load_story
from app.clues import BOARDS, WIDE, Clue, Is, Parity
from app.generate import (
    FEWEST_SICK,
    FORMS,
    MOST_SICK,
    QUIET_LINES,
    SCHEDULE,
    GenerationError,
    _candidates,
    _choose,
    _form,
    _true_clues,
    generate_day,
    generate_week,
    main,
)
from app.grade import grade
from app.week import Week, load_days
from tests.factories import MONDAY, SAMPLE_BOARD, STORIES, board_index

if TYPE_CHECKING:
    from pathlib import Path

    from app.week import Difficulty

CAST = load_cast(STORIES / "cast.md")
STORY = load_story(STORIES / "2026-W45.md", CAST)


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
    assert sorted(days) == [date(2026, 11, d) for d in range(2, 7)]
    assert [day.difficulty for _, day in days.values()] == list(SCHEDULE)
    week = Week.model_validate_json(out.read_bytes())
    assert week.generator is not None
    assert week.generator.seed == 2026  # noqa: PLR2004
    # Only where it went and how hard: no clue, solution or seed.
    assert capsys.readouterr().out == (
        f"wrote {out} (Easy, Medium, Medium, Hard, Hard)\n"
    )


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
        assert len(flavour) == QUIET_LINES
        assert all(line.endswith("'s line.") for line in flavour)


def test_the_same_seed_builds_the_same_week() -> None:
    commit = "0" * 40

    first = generate_week(CAST, date(2026, 11, 2), 1, commit, STORY)

    assert generate_week(CAST, date(2026, 11, 2), 1, commit, STORY) == first
    _seats_the_story_and_gives_speakers_their_lines(first)


def _seats_the_story_and_gives_speakers_their_lines(week: Week) -> None:
    names = [c.name for c in week.board.coworkers]
    assert names == sorted(m.name for m in STORY.who)
    for day, said in zip(week.days, STORY.days, strict=True):
        flavour = {
            names[DESKS.index(d)]: day.reveal(d).text
            for d in DESKS
            if day.reveal(d).clue is None
        }
        assert flavour == said
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
    said = Is(desk="A1")
    news = Parity(group=Row(row=2), parity="odd")

    for seed in range(20):
        chosen = _choose(
            SAMPLE_BOARD,
            [said, news],
            known=known,
            alive=known,
            declared={"A1": True},
            rng=random.Random(seed),
            easy=True,
        )
        assert chosen == news
