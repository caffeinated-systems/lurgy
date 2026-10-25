from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ponytail: version mirrors pyproject.toml (the project isn't installed, so
# importlib.metadata can't read it); title is a placeholder until #16 names the game.
app = FastAPI(
    title="Office bug API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)


class Health(BaseModel):
    status: Literal["ok"] = Field(
        default="ok", description="Always `ok` while the API is up.", examples=["ok"]
    )


@app.get("/api/health")
def health() -> Health:
    """Report that the API is up."""
    return Health()


# ponytail: fixed repo-relative path; make it configurable if the deploy (#34) needs.
WEB_DIST = Path(__file__).parents[2] / "web" / "dist"

# Mounted last so /api routes win; check_dir=False lets the API run unbuilt web/.
app.mount("/", StaticFiles(directory=WEB_DIST, html=True, check_dir=False))
