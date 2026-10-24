# Built puzzles live in a private repo

This repo is public, so committing built puzzles here would publish every solution. Each Week's puzzles are built ahead of time by a scheduled GitHub Action and pushed as one JSON file to a separate private puzzles repo, which the server pulls when it starts; after each build, a redeploy picks up the new Week. A private repo keeps the files versioned and diffable with no database or object storage, and works wherever the app is hosted. Encrypting the files into this repo was the alternative; it moves the secret to a key and makes debugging harder.

## Consequences

- **The seed is as secret as the solution.** The generator and its commit are public, so the seed recorded in each file reproduces the Week. It comes from `secrets` (128 bits or more), never from a time or date, and is never logged or written to this repo.
- **The build never leaks through CI.** Action logs in a public repo are public: the build job never prints puzzle content or the seed (including validation errors and test output), uploads no artifacts, and caches nothing but dependencies. The write deploy key lives in a GitHub environment limited to `main` and exposed only to the build job; actions that touch it are pinned by SHA, and no workflow uses `pull_request_target`.
- **A Week never changes once it starts**, at the first Monday midnight anywhere (UTC+14): players' saved progress depends on it. The build skips Weeks already built, so a generator fix reaches only unbuilt Weeks unless one is deliberately rebuilt before it starts. This is enforced by the build, not by the private repo, whose write key could force-push.
- **Old files are never migrated.** The file is validated by Pydantic models the API reuses, so model changes must stay backward compatible with every Week the server may still serve.
- **The browser gets only the board and the starting coworker's clue.** Every other clue or flavour line arrives only with an accepted declaration, and the API serves only a day that is current somewhere on Earth, so nobody plays Friday on Monday.
- **The server needs `git`, `ssh` and a read-only deploy key** at startup.
- This settles where generated puzzles are stored and the one background job, both left open by ADR 0001.
