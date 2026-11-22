
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    BackgroundTasks
)
from pydantic import BaseModel, Field

from database.db_manager import (
    init_db,
    get_available_professions,
    get_vacancies,
    get_discussions,
    get_knowledge_base
)

from backend.n8n_client import N8NClient

from Boyscout.smartest_update import (
    research_for_site,
    refresh_status
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ModeusAristo API",
    description="API для работы с данными о профессиях и AI-агентах",
    version="1.0.0",
    lifespan=lifespan
)

n8n_client = N8NClient()


# Модели запросов

class PersonaRequest(BaseModel):
    profession: str


class QuestionRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)


class ExpertRequest(BaseModel):
    question: str
    persona: dict
    facts: list[dict]
    history: list[dict] = Field(default_factory=list)


class ScoutSearchRequest(BaseModel):
    profession: str
    level: Literal["Junior", "Middle", "Senior"]


# Проверка ответа n8n

def get_agent_data(result, key):
    data = result.get("data", {})

    if key not in data:
        raise HTTPException(
            status_code=502,
            detail=f"В ответе n8n отсутствует поле {key}"
        )

    return data[key]


# Преобразование статусов Smart Update

def normalize_status(status):
    statuses = {
        "not_started": "idle",
        "processing": "running",
        "scheduled": "running",
        "fresh": "completed"
    }

    return statuses.get(status, status)


# Основные методы API

@app.get("/")
def home():
    return {
        "message": "ModeusAristo API работает"
    }


@app.get("/api/professions")
def professions():
    return get_available_professions()


# Получение полной карточки профессии

@app.get("/api/professions/{profession}")
def get_profession(profession: str):
    available = get_available_professions()

    if profession not in available:
        raise HTTPException(
            status_code=404,
            detail="Профессия не найдена"
        )

    knowledge = get_knowledge_base(profession)
    vacancies_data = get_vacancies(profession, limit=10)
    discussions_data = get_discussions(profession, limit=20)

    return {
        "profession": {
            "name": profession
        },
        "vacancies": vacancies_data or [],
        "forum_discussions": discussions_data or [],
        "knowledge_base": knowledge
    }


# Smart Update: поиск профессии

@app.post("/scout/search")
def scout_search(
    request: ScoutSearchRequest,
    background_tasks: BackgroundTasks
):
    result = research_for_site(
        request.profession,
        background_tasks
    )

    result["level"] = request.level

    result["status"] = (
        "loading"
        if result["data_mode"] == "loading"
        else "ready"
    )

    result["refresh_status"] = normalize_status(
        result["refresh_status"]
    )

    return result


# Smart Update: получение статуса

@app.get("/scout/status/{profession}")
def scout_status(profession: str):
    result = refresh_status(profession)

    result["status"] = normalize_status(
        result["status"]
    )

    return result


# Получение вакансий

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


# Получение обсуждений

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


# Получение базы знаний

@app.get("/api/professions/{profession}/knowledge-base")
def knowledge_base(profession: str):
    result = get_knowledge_base(profession)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="База знаний не найдена"
        )

    return result


# Persona Builder

@app.post("/api/ai/persona")
def build_persona(request: PersonaRequest):
    available = get_available_professions()

    if request.profession not in available:
        raise HTTPException(
            status_code=404,
            detail="Профессия не найдена"
        )

    try:
        facts = n8n_client.get_facts(request.profession)
        result = n8n_client.build_persona(facts)

        return {
            "facts": facts,
            "persona": get_agent_data(result, "persona"),
            "mode": result.get("mode")
        }

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error)
        )


# Interviewer

@app.post("/api/ai/question")
def get_question(request: QuestionRequest):
    try:
        result = n8n_client.get_question(
            request.message,
            request.history
        )

        return {
            "question": get_agent_data(result, "question"),
            "mode": result.get("mode")
        }

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error)
        )


# Expert

@app.post("/api/ai/answer")
def ask_expert(request: ExpertRequest):
    try:
        result = n8n_client.ask_expert(
            request.question,
            request.persona,
            request.facts,
            request.history
        )

        return {
            "answer": get_agent_data(result, "answer"),
            "mode": result.get("mode")
        }

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error)
        )
