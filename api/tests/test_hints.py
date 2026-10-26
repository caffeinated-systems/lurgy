import random
from http import HTTPStatus
from itertools import combinations
from typing import TYPE_CHECKING, Any

import numpy as np

from app.board import DESKS
from app.clues import BOARDS, EVERYONE, WIDE, Count, settled
from app.generate import generate_day
from app.grade import MOST, hint
from app.main import ExplainedClue, app
from app.week import load_days
from tests.factories import FIXTURES, MONDAY, SAMPLE_BOARD
from tests.test_declarations import PERFECT, REJECTED, client, declare

if TYPE_CHECKING:
    from app.board import Desk
    from app.clues import Boards, Mask, State

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


def _forces(
    subset: tuple[Desk, ...],
    masks: dict[Desk, Mask],
    alive: Boards,
    declared: set[Desk],
) -> list[Desk]:
    """Who these clues settle, in desk order."""
    kept = np.logical_and.reduce([masks[d] for d in subset])
    return sorted(settled(alive[kept], declared), key=DESKS.index)


def test_hints_alone_walk_a_hard_day_with_the_fewest_clues_each_time() -> None:
    day = generate_day(SAMPLE_BOARD, MONDAY, "Hard", random.Random(2027))
    steps: list[tuple[Desk, State]] = []
    sizes = []
    wides = []
    while len(steps) < len(DESKS) - 1:
        clues, coworker = hint(SAMPLE_BOARD, day, steps)

        declared = {day.start, *(d for d, _ in steps)}
        alive = BOARDS[
            np.logical_and.reduce(
                [
                    (BOARDS >> DESKS.index(d) & 1).astype(bool) == (d in day.sick)
                    for d in declared
                ]
            )
        ]
        speakers = [d for d in DESKS if d in declared and day.reveal(d).clue]
        masks = {d: day.reveal(d).clue.mask(SAMPLE_BOARD, alive) for d in speakers}  # type: ignore[union-attr]

        wide = any(isinstance(day.reveal(d).clue, WIDE) for d in clues)
        fewer = range(1, min(len(clues), MOST + 1) if len(clues) > MOST else len(clues))
        assert not any(
            _forces(s, masks, alive, declared)
            for k in fewer
            for s in combinations(speakers, k)
        )
        if wide:  # no local-only subset of the same size would do
            local = [d for d in speakers if not isinstance(day.reveal(d).clue, WIDE)]
            assert not any(
                _forces(s, masks, alive, declared)
                for s in combinations(local, len(clues))
            )
        assert coworker == _forces(tuple(clues), masks, alive, declared)[0]
        sizes.append(len(clues))
        wides.append(wide)
        steps.append((coworker, day.state(coworker)))

    assert max(sizes) > 1, "the walk never needed more than one clue"
    assert any(wides), "the walk never needed a whole-board clue"
    assert day.accepts(SAMPLE_BOARD, steps)


def test_more_declarations_than_desks_is_invalid() -> None:
    assert ask(PERFECT + PERFECT[:1])[0] == HTTPStatus.UNPROCESSABLE_ENTITY


def test_a_hint_spells_out_each_of_its_clues() -> None:
    hint = ask(PERFECT[:3])[1]

    assert [e["desk"] for e in hint["explanations"]] == hint["clues"]


def test_an_explained_clue_names_its_desks() -> None:
    day = generate_day(SAMPLE_BOARD, MONDAY, "Hard", random.Random(2027))
    for desk, reveal in zip(DESKS, day.reveals, strict=True):
        match reveal.clue:
            case None:
                continue
            case Count(group=group):
                bits = SAMPLE_BOARD.bits(group)
            case _:
                bits = EVERYONE
        explained = ExplainedClue.at(SAMPLE_BOARD, day, desk)

        assert explained.explanation == reveal.explanation
        assert explained.explanation
        assert explained.desks == [d for i, d in enumerate(DESKS) if bits >> i & 1]


def test_a_comparing_clue_covers_both_of_its_groups() -> None:
    # Jas (B3): "My row has more sick people than the sick people to my right."
    assert ExplainedClue.at(BOARD, DAY, "B3").desks == ["A3", "B3", "C3", "D3"]
