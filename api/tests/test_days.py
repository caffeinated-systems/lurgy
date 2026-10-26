from datetime import date, datetime, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from app.main import EARLIEST, LATEST, app, days, open_week, today_anywhere
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


def test_open_week_is_the_monday_at_utc_minus_12() -> None:
    assert LATEST.utcoffset(None) == timedelta(hours=-12)
    today = datetime.now(LATEST).date()
    assert open_week().weekday() == 0
    assert 0 <= (today - open_week()).days < 7  # noqa: PLR2004


def test_a_day_ahead_at_utc_plus_14_still_serves_its_week() -> None:
    # Tuesday has started in Kiribati; Monday is still today at UTC-12.
    app.dependency_overrides[today_anywhere] = lambda: date(2026, 10, 20)

    assert client.get("/api/days/2026-10-19").status_code == HTTPStatus.OK


def test_the_week_just_ended_stays_open_all_weekend() -> None:
    app.dependency_overrides[today_anywhere] = lambda: date(2026, 10, 26)

    # Still Sunday at UTC-12, so Monday's Week is open somewhere.
    assert client.get("/api/days/2026-10-19").status_code == HTTPStatus.OK


def test_a_week_closes_once_monday_starts_at_utc_minus_12() -> None:
    app.dependency_overrides[today_anywhere] = lambda: date(2026, 10, 27)
    app.dependency_overrides[open_week] = lambda: date(2026, 10, 26)

    assert client.get("/api/days/2026-10-19").status_code == HTTPStatus.NOT_FOUND


def test_declarations_and_hints_close_with_the_week() -> None:
    app.dependency_overrides[open_week] = lambda: date(2026, 10, 26)
    declaration = {"desk": "A3", "state": "sick"}

    declared = client.post(
        "/api/declarations",
        json={"date": "2026-10-19", "declared": [], "declaration": declaration},
    )
    hinted = client.post("/api/hints", json={"date": "2026-10-19", "declared": []})

    assert declared.status_code == HTTPStatus.NOT_FOUND
    assert hinted.status_code == HTTPStatus.NOT_FOUND
