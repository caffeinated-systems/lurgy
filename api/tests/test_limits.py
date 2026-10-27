from http import HTTPStatus
from typing import TYPE_CHECKING

from app import limits
from tests.test_declarations import PERFECT, client

if TYPE_CHECKING:
    import pytest


def hints(n: int, ip: str = "203.0.113.1") -> list[int]:
    return [
        client.post(
            "/api/hints",
            json={"date": "2026-10-19", "declared": []},
            headers={"CF-Connecting-IP": ip},
        ).status_code
        for _ in range(n)
    ]


def test_a_burst_of_hints_past_the_limit_is_told_to_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(limits, "clock", lambda: 600.0 + 15)

    assert hints(30) == [HTTPStatus.OK] * 30
    response = client.post(
        "/api/hints",
        json={"date": "2026-10-19", "declared": []},
        headers={"CF-Connecting-IP": "203.0.113.1"},
    )

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert response.headers["Retry-After"] == "45"


def test_each_player_has_their_own_budget_and_it_comes_back_next_minute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(limits, "clock", lambda: 600.0)
    hints(31)

    assert hints(1, ip="198.51.100.7") == [HTTPStatus.OK]
    monkeypatch.setattr(limits, "clock", lambda: 660.0)
    assert hints(1) == [HTTPStatus.OK]


def test_a_whole_game_of_declarations_and_loads_stays_under_the_limits() -> None:
    for i, declaration in enumerate(PERFECT):
        assert client.get("/api/days/2026-10-19").status_code == HTTPStatus.OK
        response = client.post(
            "/api/declarations",
            json={
                "date": "2026-10-19",
                "declared": PERFECT[:i],
                "declaration": declaration,
            },
        )
        assert response.json()["accepted"]


def test_days_and_declarations_have_looser_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(limits, "clock", lambda: 600.0)
    days = [client.get("/api/days/2026-10-19").status_code for _ in range(301)]
    declaration = {"date": "2026-10-19", "declared": [], "declaration": PERFECT[0]}
    declarations = [
        client.post("/api/declarations", json=declaration).status_code
        for _ in range(121)
    ]

    assert days == [HTTPStatus.OK] * 300 + [HTTPStatus.TOO_MANY_REQUESTS]
    assert declarations == [HTTPStatus.OK] * 120 + [HTTPStatus.TOO_MANY_REQUESTS]
