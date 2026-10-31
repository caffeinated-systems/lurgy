from datetime import date
from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from app.main import app, today_anywhere
from app.week import load_days
from tests.factories import FIXTURES, MONDAY
from tests.test_monday_sample import REVEALS, SICK

if TYPE_CHECKING:
    from app.board import Desk

client = TestClient(app)

# The office manager who never slips: every coworker after Jas, in reveal order.
PERFECT = [
    {"desk": desk, "state": "sick" if desk in SICK else "well"}
    for desk, _ in REVEALS[1:]
]


def declare(declared: list[dict[str, str]], desk: Desk, state: str) -> bytes:
    response = client.post(
        "/api/declarations",
        json={
            "date": "2026-10-19",
            "declared": declared,
            "declaration": {"desk": desk, "state": state},
        },
    )
    assert response.status_code == HTTPStatus.OK
    return response.content


REJECTED = b'{"accepted":false}'


def test_a_forced_correct_declaration_reveals_the_next_clue() -> None:
    response = client.post(
        "/api/declarations",
        json={
            "date": "2026-10-19",
            "declared": [],
            "declaration": {"desk": "A3", "state": "sick"},
        },
    )

    assert response.json() == {
        "accepted": True,
        "reveal": {
            "desk": "A3",
            "state": "sick",
            "kind": "clue",
            "text": "Nobody between me and Quentin is sick. "
            "Have you tried turning me off and on again?",
            "joke": None,
        },
    }


def test_the_perfect_run_plays_to_the_end() -> None:
    _, day = load_days(FIXTURES)[MONDAY]

    for i, (desk, _) in enumerate(REVEALS[1:]):
        body = client.post(
            "/api/declarations",
            json={
                "date": "2026-10-19",
                "declared": PERFECT[:i],
                "declaration": PERFECT[i],
            },
        ).json()
        assert body["accepted"], desk
        assert body["reveal"]["text"] == day.reveal(desk).text

    assert body["reveal"]["kind"] == "flavour"  # Nadia, last


def test_a_wrong_declaration_is_rejected() -> None:
    assert declare([], "A3", "well") == REJECTED


def test_a_correct_but_unforced_declaration_is_rejected() -> None:
    assert declare([], "D5", "sick") == REJECTED


def test_an_unforced_step_in_the_declarations_so_far_is_rejected() -> None:
    # D5 is sick, but nothing forced it: smuggling it in must not help.
    assert declare([{"desk": "D5", "state": "sick"}], "A3", "sick") == REJECTED


def test_a_wrong_step_in_the_declarations_so_far_is_rejected() -> None:
    # A3 sick is forced from the start alone, so only the wrong D5 can reject it.
    assert declare([], "A3", "sick") != REJECTED
    assert declare([{"desk": "D5", "state": "well"}], "A3", "sick") == REJECTED


def test_a_repeated_declaration_is_rejected() -> None:
    a3 = {"desk": "A3", "state": "sick"}

    assert declare([a3, a3], "A4", "well") == REJECTED
    assert declare([a3], "A3", "sick") == REJECTED


def test_redeclaring_the_starting_coworker_is_rejected() -> None:
    assert declare([], "B3", "well") == REJECTED
    assert declare([{"desk": "B3", "state": "well"}], "A3", "sick") == REJECTED


def test_a_declaration_for_an_unknown_day_is_not_found() -> None:
    response = client.post(
        "/api/declarations",
        json={
            "date": "2026-10-20",
            "declared": [],
            "declaration": {"desk": "A3", "state": "sick"},
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_a_declaration_for_a_day_not_started_anywhere_is_not_found() -> None:
    app.dependency_overrides[today_anywhere] = lambda: date(2026, 10, 18)

    response = client.post(
        "/api/declarations",
        json={
            "date": "2026-10-19",
            "declared": [],
            "declaration": {"desk": "A3", "state": "sick"},
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_more_declarations_than_desks_are_invalid() -> None:
    a3 = {"desk": "A3", "state": "sick"}
    response = client.post(
        "/api/declarations",
        # Everyone but the starting coworker and BS is 19, plus this one.
        json={"date": "2026-10-19", "declared": [a3] * 20, "declaration": a3},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_a_desk_off_the_board_is_invalid() -> None:
    response = client.post(
        "/api/declarations",
        json={
            "date": "2026-10-19",
            "declared": [],
            "declaration": {"desk": "E9", "state": "sick"},
        },
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
