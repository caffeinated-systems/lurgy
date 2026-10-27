"""Per-player request limits, so scripts can't hammer the API, above all the hints.

Each limit counts requests per IP in fixed one-minute windows. They're sized for an
office of players behind one IP, not one player.
"""

import time
from http import HTTPStatus
from math import ceil
from threading import Lock
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request

if TYPE_CHECKING:
    from collections.abc import Callable

WINDOW = 60  # seconds

# ponytail: in memory and per process, so each Cloud instance counts on its own.
# Move the counts to a shared store (Redis) if Cloud scales out and that matters.
counts: dict[tuple[str, str], int] = {}
_window = 0
_lock = Lock()  # Route handlers run in FastAPI's threadpool.


def clock() -> float:
    return time.time()


def client_ip(request: Request) -> str:
    """The player's IP: Cloudflare sets the header, and is the only way in on Cloud."""
    forwarded = request.headers.get("CF-Connecting-IP")
    return forwarded or (request.client.host if request.client else "")


def limit(name: str, per_minute: int) -> Callable[[Request], None]:
    """A route dependency allowing each IP `per_minute` requests, then 429."""

    def check(request: Request) -> None:
        global _window  # noqa: PLW0603 - the one piece of state the counts hang on
        now = clock()
        window = int(now // WINDOW)
        key = (name, client_ip(request))
        with _lock:
            if window != _window:
                counts.clear()
                _window = window
            counts[key] = count = counts.get(key, 0) + 1
        if count > per_minute:
            wait = ceil((window + 1) * WINDOW - now)
            raise HTTPException(
                HTTPStatus.TOO_MANY_REQUESTS,
                "Too many requests.",
                headers={"Retry-After": str(wait)},
            )

    return check


def reset() -> None:
    with _lock:
        counts.clear()
