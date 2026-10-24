# Built puzzles live in a private repo

This repo is public, so committing built puzzles here would publish every solution. Each Week's puzzles are built ahead of time by a scheduled GitHub Action and pushed as one JSON file to a separate private puzzles repo, which the server pulls when it starts. A private repo keeps the files versioned and reviewable with no database or object storage, and works wherever the app is hosted.

## Consequences

- A Week's file never changes once the Week starts on Monday: players' saved progress depends on it, so generator fixes only reach Weeks that haven't started.
- The browser gets only the board and the clues revealed so far, never the solution or an unrevealed clue.
- Each file records the generator's commit and seed, so any puzzle can be rebuilt for debugging.
- The build Action writes with one deploy key and the server reads with another; no personal access tokens.
