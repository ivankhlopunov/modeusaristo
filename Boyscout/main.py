"""HTTP-интерфейс Scout, одинаковый для заглушки и будущего парсера."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from scout_mock import get_mock_scout_data


app = FastAPI(title="ModeusAristo Scout", version="0.2.0")


class ScoutRequest(BaseModel):
    profession: str = Field(min_length=1, max_length=150)
    level: str = "Junior"


@app.get("/health")
def health():
    return {"status": "ok", "service": "scout", "mode": "mock"}


@app.post("/scout/search")
def scout_search(request: ScoutRequest):
    try:
        return get_mock_scout_data(request.profession, request.level)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
