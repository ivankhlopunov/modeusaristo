from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import requests

from parcer_Arbeitnow import search_vacancies


app = FastAPI(title="ModeusAristo Scout")


class ScoutRequest(BaseModel):
    profession: str = Field(min_length=1, max_length=150)
    level: str = "Junior"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "scout",
        "mode": "live"
    }


@app.post("/scout/search")
def scout_search(request: ScoutRequest):

    profession = request.profession.strip()

    if not profession:
        raise HTTPException(
            status_code=422,
            detail="Название профессии не может быть пустым"
        )

    try:
        vacancies = search_vacancies(
            profession=profession,
            limit=10,
            max_pages=3
        )

    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"Не удалось получить вакансии: {error}"
        ) from error

    return {
        "profession": profession,
        "level": request.level,
        "status": "success",
        "data_mode": "live",
        "vacancies": vacancies,
        "forum_discussions": [],
        "warnings": [
            "Используется API Arbeitnow.",
            "Поиск ограничен тремя страницами вакансий.",
            "Парсинг форумов пока не подключён."
        ],
        "errors": []
    }