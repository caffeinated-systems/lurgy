from http import HTTPStatus
from typing import Any

import numpy as np

from app.board import DESKS
from app.clues import BOARDS, settled
from app.main import app
from app.week import load_days
from tests.factories import FIXTURES, MONDAY
from tests.test_declarations import PERFECT, REJECTED, client, declare

BOARD, DAY = load_days(FIXTURES)[MONDAY]


def ask(declared: list[dict[str, str]], on: str = "2026-10-19") -> tuple[int, Any]:
    response = client.post("/api/hints", json={"date": on, "declared": declared})
    return response.status_code, response.json()


def test_every_hint_names_clues_that_force_its_coworker() -> None:
    for i in range(len(PERFECT)):
        declared = PERFECT[:i]
        status, hint = ask(declared)

        assert status == HTTPStatus.OK
        named = {DAY.start, *(d["desk"] for d in declared)}
        known = {d for d in DESKS if d in named}
        assert set(hint["clues"]) <= known
        assert hint["coworker"] not in known
        # The hinted clues alone, with the declarations, settle the coworker.
        alive = np.ones(BOARDS.shape, dtype=np.bool_)
        for desk in known:
            sick = (BOARDS >> DESKS.index(desk) & 1).astype(np.bool_)
            alive &= sick == (desk in DAY.sick)
        for desk in hint["clues"]:
            clue = DAY.reveal(desk).clue
            assert clue is not None
            alive &= clue.mask(BOARD)
        assert hint["coworker"] in settled(BOARDS[alive], known)
        # And declaring them is accepted.
        state = "sick" if hint["coworker"] in DAY.sick else "well"
        assert declare(declared, hint["coworker"], state) != REJECTED


def test_the_same_progress_gets_the_same_hint() -> None:
    assert ask(PERFECT[:3]) == ask(PERFECT[:3])


def test_declarations_that_werent_accepted_get_no_hint() -> None:
    wrong = [
        {**PERFECT[0], "state": "well" if PERFECT[0]["state"] == "sick" else "sick"}
    ]

    assert ask(wrong) == (HTTPStatus.BAD_REQUEST, {"detail": "Not enough evidence."})


def test_a_solved_day_has_no_hint() -> None:
    assert ask(PERFECT)[0] == HTTPStatus.CONFLICT


def test_a_day_that_hasnt_started_has_no_hint() -> None:
    assert ask([], on="2099-01-01")[0] == HTTPStatus.NOT_FOUND


def test_hints_are_in_the_schema() -> None:
    assert "/api/hints" in app.openapi()["paths"]
