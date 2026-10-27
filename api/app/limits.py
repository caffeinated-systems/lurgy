"""Per-player request limits, so scripts can't hammer the API, above all the hints.

Each limit counts requests per IP in fixed one-minute windows. They're sized for an
office of players behind one IP, not one player.
"""

import time
from http import HTTPStatus
from ipaddress import IPv6Address, ip_address, ip_network
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
    """Who to count: the player's IPv4 address, or their IPv6 /64.

    One machine usually holds a whole IPv6 /64, so counting single addresses would
    let a script rotate through them. The header is only trustworthy because on
    Cloud, Cloudflare sets it and is the only way in; behind anything else, anyone
    could send it for a fresh budget.
    """
    raw = request.headers.get("CF-Connecting-IP") or (
        request.client.host if request.client else ""
    )
    try:
        address = ip_address(raw)
    except ValueError:
        return raw
    if isinstance(address, IPv6Address):
        return str(ip_network(f"{address}/64", strict=False))
    return raw


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
