
import json
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException

from .schemas import ComposeRequest
from .composer import compose_map
from .validator import validate_map
from .versioning import (
    invalidate_stale_evidence,
    compare_with_previous_map,
)
from .quality_review import quality_review


app = FastAPI(
    title="ModeusAristo Synthesizer",
    version="1.2.1",
)

MAP_PATH = Path(__file__).parent / "data" / "map.json"

BACKEND_URL = "http://127.0.0.1:8000"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "synthesizer",
    }


async def get_backend_data(profession: str) -> dict:
    """
    Получает данные о профессии из Backend API.

    Endpoint:
    GET /api/professions/{profession}
    """

    encoded_profession = quote(profession, safe="")

    url = (
        f"{BACKEND_URL}/api/professions/"
        f"{encoded_profession}"
    )

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Профессия '{profession}' не найдена в Backend",
                )

            response.raise_for_status()

            try:
                data = response.json()
            except ValueError as error:
                raise HTTPException(
                    status_code=502,
                    detail="Backend вернул некорректный JSON",
                ) from error

            if not isinstance(data, dict):
                raise HTTPException(
                    status_code=502,
                    detail="Backend вернул некорректный формат данных",
                )

            return data

    except HTTPException:
        raise

    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Backend вернул ошибку: "
                f"{error.response.status_code}"
            ),
        ) from error

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Backend недоступен. "
                "Проверьте, запущен ли его сервер."
            ),
        ) from error


def validate_backend_data(data: dict):
    """
    Проверяет структуру ответа нового Backend API.
    """

    profession = data.get("profession")
    vacancies = data.get("vacancies")
    discussions = data.get("forum_discussions")
    knowledge_base = data.get("knowledge_base")

    if not isinstance(profession, dict):
        raise HTTPException(
            status_code=502,
            detail="Backend: поле profession должно быть объектом",
        )

    if not isinstance(profession.get("name"), str):
        raise HTTPException(
            status_code=502,
            detail="Backend: отсутствует название профессии",
        )

    if not isinstance(vacancies, list):
        raise HTTPException(
            status_code=502,
            detail="Backend: поле vacancies должно быть списком",
        )

    if not isinstance(discussions, list):
        raise HTTPException(
            status_code=502,
            detail="Backend: поле forum_discussions должно быть списком",
        )

    if knowledge_base is not None and not isinstance(
        knowledge_base, dict
    ):
        raise HTTPException(
            status_code=502,
            detail="Backend: поле knowledge_base должно быть объектом или null",
        )


def normalize_test_data(data: dict, profession: str) -> dict:
    """
    Поддерживает старый формат тестовых данных.

    Используется только тогда, когда scout передан
    непосредственно в запросе /compose.
    """

    normalized = dict(data)

    normalized.setdefault(
        "profession",
        {"name": profession},
    )

    normalized.setdefault("vacancies", [])
    normalized.setdefault("forum_discussions", [])
    normalized.setdefault("knowledge_base", None)

    return normalized


def load_previous_map():
    """
    Загружает предыдущую версию карты.
    """

    if not MAP_PATH.exists() or MAP_PATH.stat().st_size == 0:
        return None

    try:
        return json.loads(
            MAP_PATH.read_text(encoding="utf-8")
        )

    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=500,
            detail="Файл map.json содержит некорректный JSON",
        ) from error


def save_map(result: dict):
    """
    Сохраняет сформированную карту.
    """

    MAP_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    MAP_PATH.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


@app.post("/compose")
async def compose(request: ComposeRequest):

    # 1. Преобразуем сообщения интервью в словари.
    transcript = [
        message.model_dump()
        for message in request.transcript
    ]

    # 2. Получаем данные о профессии.
    scout = request.scout

    if scout is None:
        # Настоящий запрос к Backend.
        scout = await get_backend_data(request.profession)

        # Строгая проверка нового контракта.
        validate_backend_data(scout)

    else:
        # Поддержка старых тестовых данных.
        if not isinstance(scout, dict):
            raise HTTPException(
                status_code=502,
                detail="Получены некорректные данные о профессии",
            )

        scout = normalize_test_data(
            scout,
            request.profession,
        )

        validate_backend_data(scout)

    # 3. Загружаем предыдущую карту.
    previous_map = load_previous_map()

    # 4. Формируем карту профессии.
    result = compose_map(
        request.profession,
        scout,
        transcript,
    )

    # 5. Проверяем актуальность доказательств.
    result = invalidate_stale_evidence(
        result,
        transcript,
    )

    # 6. Сравниваем новую карту с предыдущей.
    result = compare_with_previous_map(
        result,
        previous_map,
        transcript,
    )

    # 7. Добавляем информацию об исходных данных.
    result["scout_warnings"] = scout.get(
        "warnings",
        [],
    )

    result["scout_data_mode"] = scout.get(
        "data_mode",
        "unknown",
    )

    # 8. Проверяем структуру карты.
    errors = validate_map(result)

    result["validation_errors"] = errors

    # 9. Выполняем Quality Review.
    result["quality_review"] = quality_review(result)

    # 10. Если есть ошибки, возвращаем их.
    if errors:
        raise HTTPException(
            status_code=422,
            detail=errors,
        )

    # 11. Сохраняем карту.
    save_map(result)

    return result


@app.get("/export")
def export_map():

    if not MAP_PATH.exists() or MAP_PATH.stat().st_size == 0:
        raise HTTPException(
            status_code=404,
            detail="Карта ещё не создана",
        )

    try:
        return json.loads(
            MAP_PATH.read_text(encoding="utf-8")
        )

    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=500,
            detail="Файл карты содержит некорректный JSON",
        ) from error
