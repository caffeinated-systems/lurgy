import random
import secrets
from datetime import date
from typing import TYPE_CHECKING

import pytest

from app.cast import STUB_BOARD
from app.generate import (
    FEWEST_SICK,
    MOST_SICK,
    SCHEDULE,
    GenerationError,
    generate_day,
    generate_week,
    main,
)
from app.grade import grade
from app.week import Week, load_days
from tests.factories import MONDAY, board_index

if TYPE_CHECKING:
    from pathlib import Path

    from app.week import Difficulty


@pytest.mark.parametrize("difficulty", ["Easy", "Medium", "Hard"])
def test_a_day_grades_at_the_difficulty_asked(difficulty: Difficulty) -> None:
    day = generate_day(STUB_BOARD, MONDAY, difficulty, random.Random(2026))

    assert grade(STUB_BOARD, day).difficulty == difficulty


def test_every_coworker_says_a_true_clue_in_words() -> None:
    day = generate_day(STUB_BOARD, MONDAY, "Medium", random.Random(7))

    solution = board_index(set(day.sick))
    assert FEWEST_SICK <= len(day.sick) <= MOST_SICK
    for reveal in day.reveals:
        assert reveal.clue is not None
        assert reveal.clue.mask(STUB_BOARD)[solution], reveal.clue
        assert reveal.text.endswith(".")
        assert reveal.explanation
    said = [r.clue for r in day.reveals]
    assert len(set(said)) == len(said), "a clue said twice"


def test_the_same_seed_builds_the_same_day() -> None:
    first = generate_day(STUB_BOARD, MONDAY, "Easy", random.Random(1))

    assert generate_day(STUB_BOARD, MONDAY, "Easy", random.Random(1)) == first


def test_running_out_of_attempts_fails() -> None:
    with pytest.raises(GenerationError, match="no Hard day"):
        generate_day(STUB_BOARD, MONDAY, "Hard", random.Random(1), attempts=0)


def test_the_cli_writes_a_week_that_loads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(secrets, "randbits", lambda _: 2026)
    out = tmp_path / "2026-W45.json"

    main(["2026-W45", "-o", str(out)])

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


def test_the_same_seed_builds_the_same_week() -> None:
    commit = "0" * 40

    first = generate_week(STUB_BOARD, date(2026, 11, 2), 1, commit)

    assert generate_week(STUB_BOARD, date(2026, 11, 2), 1, commit) == first


def test_the_cli_wants_an_iso_week(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(["2026-11-02", "-o", str(tmp_path / "w.json")])
