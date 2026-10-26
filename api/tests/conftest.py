from typing import TYPE_CHECKING

import pytest

from app.main import app, days, open_week, today_anywhere
from app.week import load_days
from tests.factories import FIXTURES, MONDAY

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def fixture_week() -> Iterator[None]:
    app.dependency_overrides[days] = lambda: load_days(FIXTURES)
    app.dependency_overrides[today_anywhere] = lambda: MONDAY
    app.dependency_overrides[open_week] = lambda: MONDAY
    yield
    app.dependency_overrides.clear()
