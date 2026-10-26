import random
from typing import TYPE_CHECKING

import pytest

from app.cast import STUB_BOARD
from app.generate import FEWEST_SICK, MOST_SICK, GenerationError, generate_day
from app.grade import grade
from tests.factories import MONDAY, board_index

if TYPE_CHECKING:
    from app.week import Difficulty


@pytest.mark.parametrize("difficulty", ["Easy", "Medium", "Hard"])
def test_a_day_grades_at_the_difficulty_asked(difficulty: Difficulty) -> None:
    day = generate_day(STUB_BOARD, MONDAY, difficulty, random.Random(2026))

    assert grade(STUB_BOARD, day).difficulty == difficulty


def test_every_coworker_says_a_true_clue_in_words() -> None:
    day = generate_day(STUB_BOARD, MONDAY, "Medium", random.Random(7))

    solution = board_index(set(day.sick))
    assert FEWEST_SICK <= len(day.sick) <= MOST_SICK
    for reveal in day.reveals:
        assert reveal.clue is not None
        assert reveal.clue.mask(STUB_BOARD)[solution], reveal.clue
        assert reveal.text.endswith(".")
        assert reveal.explanation


def test_the_same_seed_builds_the_same_day() -> None:
    first = generate_day(STUB_BOARD, MONDAY, "Easy", random.Random(1))

    assert generate_day(STUB_BOARD, MONDAY, "Easy", random.Random(1)) == first


def test_running_out_of_attempts_fails() -> None:
    with pytest.raises(GenerationError, match="no Hard day"):
        generate_day(STUB_BOARD, MONDAY, "Hard", random.Random(1), attempts=0)
