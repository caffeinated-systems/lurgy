from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from app.board import DESKS
from app.week import Day, load_days
from tests.factories import FIXTURES, MONDAY, SAMPLE_BOARD, board_index

if TYPE_CHECKING:
    from pathlib import Path


def test_the_fixture_loads_the_monday_sample() -> None:
    days = load_days(FIXTURES)

    board, day = days[MONDAY]
    assert board == SAMPLE_BOARD
    assert day.start == "B3"
    assert len(day.reveals) == len(DESKS)
    assert day.reveal("B4").clue is None  # Nadia: flavour


def test_every_clue_in_the_fixture_is_true() -> None:
    board, day = load_days(FIXTURES)[MONDAY]
    solution = board_index(set(day.sick))

    clues = [r.clue for r in day.reveals if r.clue]
    assert len(clues) == len(DESKS) - 1  # Nadia's is flavour
    for clue in clues:
        assert clue.mask(board)[solution], clue


def test_a_day_needs_a_reveal_for_every_desk() -> None:
    with pytest.raises(ValidationError):
        Day(date=MONDAY, start="A1", sick=frozenset(), reveals=())


def test_two_files_cannot_hold_the_same_day(tmp_path: Path) -> None:
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text((FIXTURES / "2026-W43.json").read_text())

    with pytest.raises(ValueError, match="2026-10-19"):
        load_days(tmp_path)
