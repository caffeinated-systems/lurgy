<p align="center">
  <img src="web/public/logo.svg" alt="Office Lurgy" width="262" height="148">
</p>

<p align="center">
  <a href="https://github.com/caffeinated-systems/lurgy/actions/workflows/tests.yml?query=branch%3Amain"><img src="https://github.com/caffeinated-systems/lurgy/actions/workflows/tests.yml/badge.svg?branch=main" alt="Tests"></a>
  <img src="https://img.shields.io/badge/api%20coverage-100%25%20branch-brightgreen" alt="api coverage: 100% branch">
  <img src="https://img.shields.io/badge/web%20coverage-100%25-brightgreen" alt="web coverage: 100%">
  <img src="https://img.shields.io/badge/mypy-strict-blue" alt="mypy: strict">
  <img src="https://img.shields.io/badge/ruff-ALL-blue" alt="ruff: ALL">
  <img src="https://img.shields.io/badge/TypeScript-strict-blue" alt="TypeScript: strict">
</p>

A daily deduction puzzle: a bug is doing the rounds of an open-plan office, and you work out who has caught it using only what the coworkers already found have said.

## How to play

- Twenty coworkers sit at a 4 × 5 grid of desks, seated alphabetically by the hot-desking system. One starts revealed.
- Declare a coworker **sick** or **well**. It's accepted only if it's correct *and* forced: the same in every office that fits what you know so far. No guessing.
- Each coworker you find says something true about who's sick or well in their row, column, neighbours, department and so on. Some just say something daft.
- Get it wrong, or right too early, and it's "Not enough evidence", and the two look the same. Stuck? A hint shows the fewest clues that settle someone, then who.
- A new puzzle every weekday, Easy on Monday to Hard by Friday, with the same office all week and a story running through it.

## How it's made

- **Every puzzle is generated, not written.** An offline generator picks a hidden outbreak and gives each coworker a true clue, and a solver checks each step against all 2²⁰ possible offices. A puzzle ships only if it can be solved without guessing and grades at the day's difficulty.
- **The office has a script.** The cast and each Week's story are edited text files in [`stories/`](stories/). Their lines never hint at who's sick.
- **Solutions never touch this repo.** Built Weeks go to a private repo. The server checks every declaration and never sends a solution or an unrevealed clue to the browser ([ADR 0002](docs/adr/0002-puzzles-in-a-private-repo.md)).
- **Stack:** a stateless FastAPI JSON API in [`api/`](api/) and a React + TypeScript single-page app in [`web/`](web/), deployed together ([ADR 0001](docs/adr/0001-fastapi-json-api-with-react-spa.md)). The words the game uses are in [`GLOSSARY.md`](GLOSSARY.md).

Inspired by Clues by Sam. Also from [Caffeinated Systems](https://caffeinated.systems): [Wordis](https://wordis.caffeinated.systems).
