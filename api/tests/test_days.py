from datetime import date, datetime, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from app.main import EARLIEST, app, days, today_anywhere
from app.week import load_days
from tests.factories import FIXTURES, MONDAY

if TYPE_CHECKING:
    import pytest

client = TestClient(app)


def test_a_day_shows_the_board_and_the_starting_clue() -> None:
    response = client.get("/api/days/2026-10-19")

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["date"] == "2026-10-19"
    assert body["coworkers"][0] == {
        "desk": "A1",
        "name": "Aisha",
        "department": "Facilities",
    }
    assert [c["desk"] for c in body["coworkers"]][-1] == "D5"
    assert body["start"] == {
        "desk": "B3",
        "state": "well",
        "kind": "clue",
        "text": "My row has more sick people than the sick people to my right. "
        "I've logged it. Formally.",
        "joke": None,
    }


def test_a_day_never_shows_the_solution_or_other_clues() -> None:
    response = client.get("/api/days/2026-10-19")

    body = response.json()
    assert body.keys() == {"date", "coworkers", "start", "difficulty"}
    assert all(c.keys() == {"desk", "name", "department"} for c in body["coworkers"])
    _, day = load_days(FIXTURES)[MONDAY]
    hidden = [r.text for r in day.reveals if r is not day.reveal("B3")]
    assert not any(text in response.text for text in hidden)


def test_an_unknown_day_is_not_found() -> None:
    response = client.get("/api/days/2026-10-20")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_a_day_that_has_not_started_anywhere_is_not_found() -> None:
    app.dependency_overrides[today_anywhere] = lambda: date(2026, 10, 18)

    response = client.get("/api/days/2026-10-19")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_today_anywhere_is_utc_plus_14() -> None:
    assert EARLIEST.utcoffset(None) == timedelta(hours=14)
    assert today_anywhere() == datetime.now(EARLIEST).date()


def test_days_come_from_puzzles_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUZZLES_DIR", str(FIXTURES))
    days.cache_clear()

    with TestClient(app):  # runs the startup hook, which loads them
        assert days.cache_info().currsize == 1
    assert MONDAY in days()


def test_a_day_says_how_hard_it_is() -> None:
    board, puzzle = load_days(FIXTURES)[MONDAY]
    graded = {MONDAY: (board, puzzle.model_copy(update={"difficulty": "Medium"}))}
    app.dependency_overrides[days] = lambda: graded

    assert client.get("/api/days/2026-10-19").json()["difficulty"] == "Medium"


def test_a_day_built_before_grading_has_no_difficulty() -> None:
    assert client.get("/api/days/2026-10-19").json()["difficulty"] is None
