# FastAPI JSON API with a React single-page app

The game is a stateless FastAPI JSON API (`api/`) serving a Vite + React + TypeScript single-page app (`web/`) from one repo and one deploy. Django was the obvious alternative, but its strengths (ORM, auth, sessions, admin, templates) go unused here: guest play keeps progress in the browser and sends it with each declaration, puzzles come from the offline generator, and the board is React. FastAPI's typed signatures give us request validation and an OpenAPI schema for free, and the frontend's API types are generated from that schema so a contract change fails CI on both sides.

## Consequences

- Route handlers are plain `def`, not `async def`: the solver is CPU-bound numpy and would block the event loop.
- Nothing is chosen yet for a database, auth or background jobs; each is picked when a feature needs it. Accounts and history would add both a database and an auth library, on top of the stateless declaration check rather than replacing it.
