from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()


class Health(BaseModel):
    status: Literal["ok"] = "ok"


@app.get("/api/health")
def health() -> Health:
    return Health()


# ponytail: fixed repo-relative path; make it configurable if the deploy (#34) needs.
WEB_DIST = Path(__file__).parents[2] / "web" / "dist"

# Mounted last so /api routes win; check_dir=False lets the API run unbuilt web/.
app.mount("/", StaticFiles(directory=WEB_DIST, html=True, check_dir=False))
