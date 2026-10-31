from datetime import UTC, date, datetime
from http import HTTPStatus
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.board import DESKS
from app.main import app, days
from app.week import utc_now
from tests.factories import SAMPLE_BOARD
from tests.test_grade import overtime

client = TestClient(app)
SATURDAY = date(2026, 10, 24)


@pytest.fixture(autouse=True)
def saturday() -> None:
    """The synthetic Overtime day, where D5 is the fibber, as the Saturday."""
    puzzle = overtime().model_copy(update={"date": SATURDAY})
    app.dependency_overrides[days] = lambda: {SATURDAY: (SAMPLE_BOARD, puzzle)}
    app.dependency_overrides[utc_now] = lambda: datetime(2026, 10, 24, 12, tzinfo=UTC)


def post(path: str, declared: list[dict[str, str]], **body: object) -> dict[str, Any]:
    response = client.post(
        path, json={"date": str(SATURDAY), "declared": declared, **body}
    )
    assert response.status_code == HTTPStatus.OK, response.text
    answer: dict[str, Any] = response.json()
    return answer


def test_an_overtime_day_says_so() -> None:
    assert client.get(f"/api/days/{SATURDAY}").json()["overtime"] is True


def test_hints_and_declarations_play_overtime_to_calling_bs() -> None:
    declared: list[dict[str, str]] = []
    while len(declared) < len(DESKS):  # everyone but A1, and BS
        desk = post("/api/hints", declared)["coworker"]
        found = desk in {d["desk"] for d in declared}
        state = "fibber" if found else "sick" if desk == "D5" else "well"
        answer = post(
            "/api/declarations", declared, declaration={"desk": desk, "state": state}
        )
        assert answer["accepted"], (desk, state)
        declared.append({"desk": desk, "state": state})

    assert declared[-1] == {"desk": "D5", "state": "fibber"}
    solved = client.post(
        "/api/hints", json={"date": str(SATURDAY), "declared": declared}
    )
    assert solved.status_code == HTTPStatus.CONFLICT


def test_calling_bs_too_early_is_rejected_like_any_declaration() -> None:
    answer = post(
        "/api/declarations", [], declaration={"desk": "D5", "state": "fibber"}
    )

    assert answer == {"accepted": False}
