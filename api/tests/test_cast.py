from datetime import date
from typing import TYPE_CHECKING

import pytest

from app.cast import StoryError, load_cast, load_story, main
from tests.factories import STORIES

if TYPE_CHECKING:
    from pathlib import Path

CAST = load_cast(STORIES / "cast.md")
STORY = (STORIES / "2026-W45.md").read_text()


def test_the_cast_reads_names_departments_and_pools() -> None:
    aisha = CAST["Aisha"]

    assert len(CAST) == 22  # noqa: PLR2004
    assert (aisha.department, aisha.lines, aisha.jokes) == (
        "Facilities",
        ("Aisha's line.",),
        ("Aisha's joke.",),
    )


def test_a_story_reads_who_is_in_and_who_speaks() -> None:
    story = load_story(STORIES / "2026-W45.md", CAST)

    assert [m.name for m in story.who][:3] == ["Aisha", "Barry", "Carol"]
    assert len(story.who) == 20  # noqa: PLR2004
    assert story.days == (
        {"Aisha": "Morning, all.", "Barry": "Is that my mug?"},
        {},
        {"Carol": "Fire drill at ten."},
        {},
        {"Dev": "Cake in the kitchen."},
    )


@pytest.mark.parametrize(
    ("cast", "error"),
    [
        (
            "## Aisha\nDepartment: HR\n## aisha\nDepartment: HR",
            ":3: aisha is in the cast twice",
        ),
        ("## Aisha\n\nShe's lovely.", ":1: Aisha has no department"),
        ("## Aisha\nDepartment: HR\n### Voice", ":3: unknown section 'Voice'"),
        ("## Aisha\nDepartment: HR\n### Jokes\n- ", ":4: empty bullet"),
    ],
)
def test_a_broken_cast_names_the_line(tmp_path: Path, cast: str, error: str) -> None:
    (path := tmp_path / "cast.md").write_text(cast)

    with pytest.raises(StoryError, match=error):
        load_cast(path)


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        ("## Away", "## Office party", ":7: unknown or repeated section 'Office"),
        ("## Tuesday", "## Monday", ":15: unknown or repeated section 'Monday'"),
        ("Aisha, Barry", "Aisha, Zed", ":4: Zed isn't in the cast"),
        ("Aisha, Barry", "Aisha, Aisha", ":4: Aisha is in twice"),
        (", Tariq", "", ":3: 19 are in, not 20"),
        ("Steve", "Vic", ":3: needs 5 to 7 departments"),
        ("- Uma: on a course", "- Aisha: on a course", ":8: Aisha isn't away"),
        ("- Barry: Is", "- Uma: Is", ":13: Uma isn't in this Week"),
        ("- Barry: Is that my mug?", "- Barry:", ":13: Barry says nothing"),
        ("- Barry:", "- Aisha:", ":13: Aisha speaks twice"),
        ("## Tuesday", "- Carol: Hi.\n- Dev: Hi.\n## Tuesday", ":16: more than 3"),
        ("## Thursday\n", "", ":1: no Thursday"),
    ],
)
def test_a_broken_story_names_the_line(
    tmp_path: Path, old: str, new: str, error: str
) -> None:
    assert old in STORY
    (path := tmp_path / "2026-W45.md").write_text(STORY.replace(old, new, 1))

    with pytest.raises(StoryError, match=error):
        load_story(path, CAST)


def _stories(tmp_path: Path, **weeks: str) -> Path:
    (tmp_path / "cast.md").write_text((STORIES / "cast.md").read_text())
    for week, text in weeks.items():
        (tmp_path / f"{week}.md").write_text(text)
    return tmp_path


def test_check_passes_and_warns_of_quiet_weeks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stories = _stories(tmp_path, **{"2026-W45": STORY})

    # Wednesday of W44: W45 is written, W46 isn't.
    main(["check", "--stories", str(stories)], today=date(2026, 10, 28))

    assert capsys.readouterr().out == (
        "::warning::no story for 2026-W46: it will be a quiet week\n"
        "checked 22 cast members\n"
    )


@pytest.mark.parametrize(
    ("weeks", "error"),
    [
        ({"2026-W45": STORY.replace("Aisha, Barry", "Aisha, Zed")}, "Zed isn't"),
        ({"2026-W99": STORY}, "2026-W99.md:1: not named for an ISO week"),
    ],
)
def test_check_fails_on_a_broken_story(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    weeks: dict[str, str],
    error: str,
) -> None:
    stories = _stories(tmp_path, **weeks)

    with pytest.raises(SystemExit) as exit_:
        main(["check", "--stories", str(stories)], today=date(2026, 10, 28))

    assert exit_.value.code == 1
    assert error in capsys.readouterr().err
