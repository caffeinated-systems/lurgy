from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Health(BaseModel):
    status: Literal["ok"] = "ok"


@app.get("/api/health")
def health() -> Health:
    return Health()
