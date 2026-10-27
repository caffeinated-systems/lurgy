"""The app on the fixture Monday, for the browser tests in web/e2e."""

from app.main import app, utc_now
from tests.factories import NOON

app.dependency_overrides[utc_now] = lambda: NOON
