from app.board import Board, Coworker

# ponytail: the voice prototype's Monday sample seats every Week until the cast and
# story files drive who's in (#30). Names run A to T across the floor.
DEPARTMENTS = (
    "Facilities", "Facilities", "HR", "Marketing",
    "IT", "Facilities", "Marketing", "Finance",
    "IT", "HR", "IT", "Sales",
    "Finance", "Sales", "Sales", "Marketing",
    "Finance", "Sales", "HR", "IT",
)  # fmt: skip
NAMES = (
    "Aisha", "Barry", "Carol", "Dev",
    "Erin", "Fergus", "Gemma", "Hamid",
    "Imogen", "Jas", "Kev", "Linda",
    "Mo", "Nadia", "Ollie", "Priya",
    "Quentin", "Rosa", "Steve", "Tariq",
)  # fmt: skip

STUB_BOARD = Board(
    coworkers=tuple(
        Coworker(name=n, department=d) for n, d in zip(NAMES, DEPARTMENTS, strict=True)
    )
)
