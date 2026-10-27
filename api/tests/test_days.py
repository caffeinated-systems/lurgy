from datetime import UTC, date, datetime
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from app.main import app, days, open_week, today_anywhere, utc_now
from app.week import load_days
from tests.factories import FIXTURES, MONDAY

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


def at(instant: str) -> datetime:
    return datetime.fromisoformat(instant)


def test_now_is_utc() -> None:
    assert utc_now().tzinfo is UTC


@pytest.mark.parametrize(
    ("now", "today"),
    [
        (at("2026-10-25T09:59:59Z"), date(2026, 10, 25)),
        (at("2026-10-25T10:00:00Z"), date(2026, 10, 26)),
    ],
)
def test_today_anywhere_starts_at_utc_plus_14(now: datetime, today: date) -> None:
    assert today_anywhere(now) == today


@pytest.mark.parametrize(
    ("now", "monday"),
    [
        (at("2026-10-26T11:59:59Z"), date(2026, 10, 19)),
        (at("2026-10-26T12:00:00Z"), date(2026, 10, 26)),
        (at("2027-01-03T23:00:00Z"), date(2026, 12, 28)),
    ],
)
def test_open_week_turns_at_utc_minus_12(now: datetime, monday: date) -> None:
    assert open_week(now) == monday


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


@pytest.mark.parametrize(
    ("now", "status"),
    [
        (at("2026-10-18T09:59:59Z"), HTTPStatus.NOT_FOUND),  # Sunday everywhere
        (at("2026-10-18T10:00:00Z"), HTTPStatus.OK),  # Monday at UTC+14
        (at("2026-10-24T12:00:00Z"), HTTPStatus.OK),  # the weekend
        (at("2026-10-26T11:59:59Z"), HTTPStatus.OK),  # still Sunday at UTC-12
        (at("2026-10-26T12:00:00Z"), HTTPStatus.NOT_FOUND),  # Monday everywhere
    ],
)
def test_a_week_opens_at_utc_plus_14_and_closes_at_utc_minus_12(
    now: datetime, status: HTTPStatus
) -> None:
    app.dependency_overrides[utc_now] = lambda: now

    assert client.get("/api/days/2026-10-19").status_code == status


def test_declarations_and_hints_close_with_the_week() -> None:
    app.dependency_overrides[utc_now] = lambda: at("2026-10-26T12:00:00Z")
    declaration = {"desk": "A3", "state": "sick"}

    declared = client.post(
        "/api/declarations",
        json={"date": "2026-10-19", "declared": [], "declaration": declaration},
    )
    hinted = client.post("/api/hints", json={"date": "2026-10-19", "declared": []})

    assert declared.status_code == HTTPStatus.NOT_FOUND
    assert hinted.status_code == HTTPStatus.NOT_FOUND
