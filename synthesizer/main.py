
import json
from pathlib import Path

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
    version="1.1.0",
)

MAP_PATH = Path(__file__).parent / "data" / "map.json"
SCOUT_URL = "http://127.0.0.1:8000"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "synthesizer",
    }


async def get_scout_data(
    profession: str,
    level: str,
) -> dict:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{SCOUT_URL}/scout/search",
                json={
                    "profession": profession,
                    "level": level,
                },
            )

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Scout вернул ошибку: "
                f"{error.response.status_code}"
            ),
        ) from error

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "Scout недоступен. "
                "Проверьте, запущен ли его сервер."
            ),
        ) from error


@app.post("/compose")
async def compose(request: ComposeRequest):
    # Преобразуем сообщения Pydantic в обычные словари.
    transcript = [
        message.model_dump()
        for message in request.transcript
    ]

    # Безопасно обрабатываем пустое интервью.
    if transcript:
        print("TRANSCRIPT:", repr(transcript[0]["text"]))
    else:
        print("TRANSCRIPT: пустое интервью")

    scout = request.scout

    # Если данные Scout не переданы, запрашиваем их.
    if scout is None:
        scout = await get_scout_data(
            request.profession,
            request.level,
        )

    if not isinstance(scout, dict):
        raise HTTPException(
            status_code=502,
            detail="Scout вернул некорректный формат данных",
        )

    if scout.get("status") != "success":
        raise HTTPException(
            status_code=502,
            detail="Scout не смог получить данные",
        )

    # Загружаем предыдущую версию карты.
    previous_map = None

    if MAP_PATH.exists() and MAP_PATH.stat().st_size > 0:
        try:
            previous_map = json.loads(
                MAP_PATH.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=500,
                detail="Файл map.json содержит некорректный JSON",
            ) from error

    # Строим новую карту.
    result = compose_map(
        request.profession,
        scout,
        transcript,
    )

    # Проверяем актуальность доказательств.
    result = invalidate_stale_evidence(
        result,
        transcript,
    )

    # Сравниваем карту с предыдущей версией.
    result = compare_with_previous_map(
        result,
        previous_map,
        transcript,
    )

    # Добавляем информацию о Scout.
    result["scout_warnings"] = scout.get("warnings", [])
    result["scout_data_mode"] = scout.get(
        "data_mode",
        "unknown",
    )

    # Проверяем структуру карты.
    # Текущая validate_map принимает один аргумент.
    errors = validate_map(result)

    result["validation_errors"] = errors
    result["quality_review"] = quality_review(result)

    if errors:
        raise HTTPException(
            status_code=422,
            detail=errors,
        )

    # Сохраняем карту.
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
