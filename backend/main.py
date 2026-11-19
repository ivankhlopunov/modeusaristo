from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from database.db_manager import (
    init_db,
    get_available_professions,
    get_vacancies,
    get_discussions,
    get_knowledge_base
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ModeusAristo API",
    description="API для работы с данными о профессиях",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
def home():
    return {
        "message": "ModeusAristo API работает"
    }


@app.get("/api/professions")
def professions():
    return get_available_professions()


@app.get("/api/professions/{profession}/vacancies")
def vacancies(
    profession: str,
    limit: int = Query(default=10, ge=1, le=1000)
):
    available = get_available_professions()

    if profession not in available:
        raise HTTPException(
            status_code=404,
            detail="Профессия не найдена"
        )

    return get_vacancies(profession, limit=limit)


@app.get("/api/professions/{profession}/discussions")
def discussions(
    profession: str,
    limit: int = Query(default=20, ge=1, le=1000)
):
    available = get_available_professions()

    if profession not in available:
        raise HTTPException(
            status_code=404,
            detail="Профессия не найдена"
        )

    return get_discussions(profession, limit=limit)


@app.get("/api/professions/{profession}/knowledge-base")
def knowledge_base(profession: str):
    result = get_knowledge_base(profession)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="База знаний не найдена"
        )

    return result
