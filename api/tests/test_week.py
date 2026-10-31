from typing import TYPE_CHECKING

import numpy as np
import pytest
from pydantic import ValidationError

from app.board import DESKS, Board, Desk, Row
from app.clues import Count
from app.week import Call, Day, Reveal, load_days
from tests.factories import FIXTURES, MONDAY, SAMPLE_BOARD, board_index

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray


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


def test_an_empty_puzzles_dir_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no Week files"):
        load_days(tmp_path)


def test_a_right_and_a_wrong_unforced_guess_take_the_same_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    board, day = load_days(FIXTURES)[MONDAY]
    scans: list[int] = []
    count_nonzero = np.count_nonzero

    def spy(a: NDArray[np.bool_]) -> int:
        scans.append(a.size)
        return int(count_nonzero(a))

    monkeypatch.setattr(np, "count_nonzero", spy)
    works = []
    for state in ("sick", "well"):  # D5 is sick, but nothing forces it yet
        scans.clear()
        assert not day.accepts(board, [("D5", state)])
        works.append(list(scans))

    assert works[0] == works[1]
    assert works[0]


def test_a_day_writes_its_sick_coworkers_in_desk_order() -> None:
    # A set's order follows PYTHONHASHSEED; a rebuilt Week file must match exactly.
    sick = frozenset({"D5", "B4", "A1", "C2", "D1", "A3", "C5"})
    day = Day(
        date=MONDAY,
        start="A1",
        sick=sick,
        reveals=(Reveal(text="…"),) * len(DESKS),
    )

    assert day.model_dump(mode="json")["sick"] == [
        "A1",
        "D1",
        "C2",
        "A3",
        "B4",
        "C5",
        "D5",
    ]


def test_the_fibber_must_be_sick() -> None:
    _, day = load_days(FIXTURES)[MONDAY]

    with pytest.raises(ValidationError, match="fibber"):
        Day.model_validate({**day.model_dump(), "fibber": "B1"})  # well


def test_the_fibber_must_give_a_clue() -> None:
    _, day = load_days(FIXTURES)[MONDAY]
    reveals = list(day.reveals)
    reveals[DESKS.index("A1")] = Reveal(text="Just a cold, honest.")  # sick

    with pytest.raises(ValidationError, match="fibber"):
        Day.model_validate({**day.model_dump(), "reveals": reveals, "fibber": "A1"})


def test_calling_bs_is_only_accepted_on_overtime() -> None:
    board, day = load_days(FIXTURES)[MONDAY]

    assert not day.accepts(board, [("A3", "sick"), ("A1", "fibber")])


def _overtime() -> tuple[Board, Day]:
    """The Monday sample with A3, first found by B3's clue, as the fibber.

    A3 is sick yet says row 3 has no one sick: a lie caught as soon as it's said.
    """
    board, day = load_days(FIXTURES)[MONDAY]
    reveals = list(day.reveals)
    reveals[DESKS.index("A3")] = Reveal(
        clue=Count(group=Row(row=3), n=0), text="Nobody's ill in row 3."
    )
    return board, day.model_copy(update={"reveals": tuple(reveals), "fibber": "A3"})


def test_bs_is_called_on_the_fibber_once_their_clue_cant_be_true() -> None:
    board, day = _overtime()

    assert day.overtime
    assert day.accepts(board, [("A3", "sick"), ("A3", "fibber")])


@pytest.mark.parametrize(
    "steps",
    [
        [("A3", "fibber")],  # hasn't said anything yet
        [("A3", "sick"), ("B3", "fibber")],  # well, so telling the truth
        [("A3", "sick"), ("A3", "fibber"), ("A3", "fibber")],  # called already
    ],
)
def test_bs_is_rejected_unless_forced_on_the_fibber(
    steps: list[tuple[Desk, Call]],
) -> None:
    board, day = _overtime()

    assert not day.accepts(board, steps)


def test_bs_on_the_fibber_is_rejected_while_their_clue_could_be_true() -> None:
    board, day = _overtime()
    reveals = list(day.reveals)
    reveals[DESKS.index("A3")] = Reveal(
        clue=Count(group=Row(row=3), n=2), text="Two of us in row 3 are ill."
    )  # one is: A3 alone, but nothing shows that yet
    day = day.model_copy(update={"reveals": tuple(reveals)})

    assert not day.accepts(board, [("A3", "sick"), ("A3", "fibber")])
