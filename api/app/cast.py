"""The cast and each Week's story, read from the Markdown files writers edit.

Only headings, `Department:` lines and bullets are read; the prose around them is
for writers. Errors name the file and line, since story files are public.
"""

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from app.board import DESKS, Board, Coworker

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
# Every speaker costs the generator a clue.
MOST_SPEAKERS = 3
DEPARTMENTS = range(5, 8)  # departments on a board
PER_DEPARTMENT = range(2, 5)  # coworkers in each


class StoryError(ValueError):
    """A cast or story file that doesn't follow the format."""

    def __init__(self, path: Path, line: int, message: str) -> None:
        super().__init__(f"{path}:{line}: {message}")


@dataclass(frozen=True)
class Member:
    name: str
    department: str
    lines: tuple[str, ...] = ()  # said in place of a clue in a quiet week
    jokes: tuple[str, ...] = ()  # said after a clue


@dataclass(frozen=True)
class Story:
    """What a Week's story file gives the generator: who's in, and who says what."""

    who: tuple[Member, ...]
    # Each day's speakers and their lines, Monday to Friday.
    days: tuple[dict[str, str], ...]


type Cast = dict[str, Member]


def fits(members: Iterable[Member]) -> bool:
    """Whether these coworkers make a board: 5 to 7 departments of 2 to 4."""
    sizes: dict[str, int] = {}
    for m in members:
        sizes[m.department] = sizes.get(m.department, 0) + 1
    return len(sizes) in DEPARTMENTS and all(
        n in PER_DEPARTMENT for n in sizes.values()
    )


type _Line = tuple[int, str]  # a line number, and the line stripped
type _Section = tuple[str, int, list[_Line]]  # its heading, where, and what's under it


def _lines(path: Path) -> list[_Line]:
    return [
        (n, line.strip()) for n, line in enumerate(path.read_text().splitlines(), 1)
    ]


def _sections(lines: list[_Line], marker: str) -> list[_Section]:
    """What's under each heading that starts with the marker."""
    sections: list[_Section] = []
    for number, line in lines:
        if line.startswith(marker):
            sections.append((line.removeprefix(marker).strip(), number, []))
        elif sections:
            sections[-1][2].append((number, line))
    return sections


def _bullets(path: Path, lines: list[_Line]) -> list[_Line]:
    """The bullets' text; any other line is prose for writers."""
    bullets: list[_Line] = []
    for number, line in lines:
        if line.startswith("-"):
            if not (text := line.removeprefix("-").strip()):
                raise StoryError(path, number, "empty bullet")
            bullets.append((number, text))
    return bullets


def load_cast(path: Path) -> Cast:
    """Everyone in `cast.md`, by name, in file order."""
    cast: Cast = {}
    for name, number, body in _sections(_lines(path), "## "):
        if any(n.casefold() == name.casefold() for n in cast):
            raise StoryError(path, number, f"{name} is in the cast twice")
        department = next(
            (
                line.removeprefix("Department:").strip()
                for _, line in body
                if line.startswith("Department:")
            ),
            "",
        )
        if not department:
            raise StoryError(path, number, f"{name} has no department")
        pools: dict[str, list[str]] = {"Lines": [], "Jokes": []}
        for heading, at, lines in _sections(body, "### "):
            if heading not in pools:
                raise StoryError(path, at, f"unknown section {heading!r}")
            pools[heading] += [text for _, text in _bullets(path, lines)]
        cast[name] = Member(
            name, department, tuple(pools["Lines"]), tuple(pools["Jokes"])
        )
    return cast


def load_story(path: Path, cast: Cast) -> Story:
    """A Week's story file, checked against the cast."""
    sections: dict[str, tuple[int, list[_Line]]] = {}
    for heading, number, body in _sections(_lines(path), "## "):
        if heading not in {"In", "Away", *DAYS} or heading in sections:
            raise StoryError(path, number, f"unknown or repeated section {heading!r}")
        sections[heading] = number, body
    if missing := [h for h in ("In", *DAYS) if h not in sections]:
        raise StoryError(path, 1, f"no {', '.join(missing)}")
    who = _who(path, cast, *sections["In"])
    for number, text in _bullets(path, sections.get("Away", (0, []))[1]):
        name = text.partition(":")[0].strip()
        if name not in cast or cast[name] in who:
            raise StoryError(path, number, f"{name} isn't away")
    return Story(
        who=who, days=tuple(_speakers(path, who, sections[d][1]) for d in DAYS)
    )


def _who(path: Path, cast: Cast, at: int, lines: list[_Line]) -> tuple[Member, ...]:
    who: list[Member] = []
    for number, line in lines:
        for name in filter(None, (n.strip() for n in line.split(","))):
            if name not in cast:
                raise StoryError(path, number, f"{name} isn't in the cast")
            if cast[name] in who:
                raise StoryError(path, number, f"{name} is in twice")
            who.append(cast[name])
    if len(who) != len(DESKS):
        raise StoryError(path, at, f"{len(who)} are in, not {len(DESKS)}")
    if not fits(who):
        raise StoryError(path, at, "needs 5 to 7 departments of 2 to 4 people")
    return tuple(who)


def _speakers(
    path: Path, who: tuple[Member, ...], lines: list[_Line]
) -> dict[str, str]:
    """A day's speakers and what each says."""
    said: dict[str, str] = {}
    for number, text in _bullets(path, lines):
        speaker, _, line = (part.strip() for part in text.partition(":"))
        if speaker not in {m.name for m in who}:
            raise StoryError(path, number, f"{speaker} isn't in this Week")
        if not line:
            raise StoryError(path, number, f"{speaker} says nothing")
        if speaker in said:
            raise StoryError(path, number, f"{speaker} speaks twice")
        if len(said) == MOST_SPEAKERS:
            raise StoryError(path, number, f"more than {MOST_SPEAKERS} speakers")
        said[speaker] = line
    return said


def story_path(stories: Path, monday: date) -> Path:
    year, week, _ = monday.isocalendar()
    return stories / f"{year}-W{week:02d}.md"


def iso_monday(week: str) -> date:
    """The Monday of an ISO week such as 2026-W45."""
    return datetime.strptime(f"{week}-1", "%G-W%V-%u").date()  # noqa: DTZ007 (a date)


def main(argv: Sequence[str] | None = None, today: date | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.cast",
        description="Check the cast and every story, and warn if stories run short.",
    )
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--stories", type=Path, default=Path("../stories"))
    args = parser.parse_args(argv)

    try:
        cast = load_cast(args.stories / "cast.md")
        for path in sorted(args.stories.glob("*-W*.md")):
            try:
                iso_monday(path.stem)
            except ValueError:
                raise StoryError(path, 1, "not named for an ISO week") from None
            load_story(path, cast)
    except StoryError as e:
        parser.exit(1, f"{e}\n")
    today = today or date.today()  # noqa: DTZ011 (a calendar day is close enough)
    this_monday = today - timedelta(days=today.weekday())
    for ahead in (1, 2):
        if not (
            path := story_path(args.stories, this_monday + timedelta(weeks=ahead))
        ).exists():
            # A GitHub Actions annotation: a quiet week is allowed, so never a failure.
            print(f"::warning::no story for {path.stem}: it will be a quiet week")  # noqa: T201
    print(f"checked {len(cast)} cast members")  # noqa: T201


# ponytail: the voice prototype's Monday sample seats every Week until the cast and
# story files drive who's in (#30). Names run A to T across the floor.
_STUB_DEPARTMENTS = (
    "Facilities", "Facilities", "HR", "Marketing",
    "IT", "Facilities", "Marketing", "Finance",
    "IT", "HR", "IT", "Sales",
    "Finance", "Sales", "Sales", "Marketing",
    "Finance", "Sales", "HR", "IT",
)  # fmt: skip
_STUB_NAMES = (
    "Aisha", "Barry", "Carol", "Dev",
    "Erin", "Fergus", "Gemma", "Hamid",
    "Imogen", "Jas", "Kev", "Linda",
    "Mo", "Nadia", "Ollie", "Priya",
    "Quentin", "Rosa", "Steve", "Tariq",
)  # fmt: skip

STUB_BOARD = Board(
    coworkers=tuple(
        Coworker(name=n, department=d)
        for n, d in zip(_STUB_NAMES, _STUB_DEPARTMENTS, strict=True)
    )
)


if __name__ == "__main__":  # pragma: no cover
    main()
