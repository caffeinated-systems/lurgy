from app.board import DESKS, Board, Coworker, Desk

# The Monday sample from the voice prototype: names run A to T across the floor.
SAMPLE_DEPARTMENTS = (
    "Facilities", "Facilities", "HR", "Marketing",
    "IT", "Facilities", "Marketing", "Finance",
    "IT", "HR", "IT", "Sales",
    "Finance", "Sales", "Sales", "Marketing",
    "Finance", "Sales", "HR", "IT",
)  # fmt: skip
SAMPLE_NAMES = (
    "Aisha", "Barry", "Carol", "Dev",
    "Erin", "Fergus", "Gemma", "Hamid",
    "Imogen", "Jas", "Kev", "Linda",
    "Mo", "Nadia", "Ollie", "Priya",
    "Quentin", "Rosa", "Steve", "Tariq",
)  # fmt: skip

SAMPLE_BOARD = Board(
    coworkers=tuple(
        Coworker(name=n, department=d)
        for n, d in zip(SAMPLE_NAMES, SAMPLE_DEPARTMENTS, strict=True)
    )
)


def desks(bits: int) -> set[Desk]:
    return {d for i, d in enumerate(DESKS) if bits >> i & 1}


def board_index(sick: set[Desk]) -> int:
    """The board (an index into all 2^20) where exactly these desks are sick."""
    return sum(1 << DESKS.index(d) for d in sick)
