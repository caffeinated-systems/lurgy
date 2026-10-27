"""The app on the fixture Monday, for the browser tests in web/e2e."""

from app.main import app, open_week, today_anywhere
from tests.factories import MONDAY

app.dependency_overrides[today_anywhere] = lambda: MONDAY
app.dependency_overrides[open_week] = lambda: MONDAY
