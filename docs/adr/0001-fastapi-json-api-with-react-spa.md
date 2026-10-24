# FastAPI JSON API with a React single-page app

The game is a stateless FastAPI JSON API (`api/`) plus a Vite + React + TypeScript single-page app (`web/`), in one repo and one deploy, with FastAPI serving the built frontend. Django was the obvious alternative, but its strengths (ORM, auth, sessions, admin, templates) go unused here: guest play keeps progress in the browser, puzzles come from the offline generator, and the board is React. FastAPI natively turns typed signatures and Pydantic models into request validation and an OpenAPI schema; the frontend's API types are generated from that schema and committed, and CI fails if they drift from it.

## Consequences

- The server stays authoritative without holding sessions: the solution never leaves the server, and each declaration arrives with the declarations made so far, which the server re-checks against the stored solution before checking the new one.
- Every rejected request looks the same as "Not enough evidence", whether the new declaration is wrong, not forced, or the declarations sent with it are invalid, so the API can't be probed for the solution.
- Route handlers are plain `def`, which FastAPI runs in its threadpool; the solver is CPU-bound numpy and would block the event loop inside `async def`.
- Nothing is chosen yet for a database, auth or background jobs, including where generated puzzles are stored (since settled by ADR 0002); each is picked when a feature needs it. Accounts and history (out of scope today) would add both a database and an auth library on top of the stateless declaration check rather than replacing it.
