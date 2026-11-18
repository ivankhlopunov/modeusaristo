from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from pathlib import Path
import json


app = FastAPI(title="ModeusAristo Scout")


# Папка, в которой лежат собранные вакансии
DATA_DIR = Path(__file__).resolve().parent / "data"


# Поддерживаемые профессии
PROFESSIONS = {
    "python developer": "Python Developer",
    "python разработчик": "Python Developer",
    "python-разработчик": "Python Developer",
    "программист python": "Python Developer",

    "java developer": "Java Developer",
    "java разработчик": "Java Developer",
    "java-разработчик": "Java Developer",
    "программист java": "Java Developer",

    "data analyst": "Data Analyst",
    "аналитик данных": "Data Analyst",
    "sql аналитик": "Data Analyst",
}


class ScoutRequest(BaseModel):
    profession: str = Field(min_length=1, max_length=150)
    level: str = "Junior"


@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "scout",
        "mode": "cached"
    }


def load_vacancies():
    """
    Загружает вакансии из последнего
    сохранённого JSON-файла.
    """

    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Папка с данными не найдена: {DATA_DIR}"
        )

    # Ищем файлы нашего парсера
    files = list(DATA_DIR.glob("trudvsem_*.json"))

    if not files:
        raise FileNotFoundError(
            "Не найден JSON с вакансиями. "
            "Сначала запусти trudvsem_parser.py"
        )

    # Берём последний изменённый файл
    latest_file = max(
        files,
        key=lambda file: file.stat().st_mtime
    )

    print(f"Загружаем данные из {latest_file.name}")

    with open(
        latest_file,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    vacancies = data.get("vacancies", [])

    if not isinstance(vacancies, list):
        raise ValueError(
            "Поле vacancies должно содержать список"
        )

    return vacancies, data.get("collected_at")


@app.post("/scout/search")
def scout_search(request: ScoutRequest):

    profession = request.profession.strip()

    normalized_name = profession.lower()

    canonical_profession = PROFESSIONS.get(
        normalized_name
    )

    if canonical_profession is None:

        raise HTTPException(
            status_code=400,
            detail=f"Профессия «{profession}» пока не поддерживается"
        )

    # Получаем сохранённые вакансии
    try:

        all_vacancies, collected_at = load_vacancies()

    except (
        FileNotFoundError,
        ValueError,
        OSError,
        json.JSONDecodeError
    ) as error:

        raise HTTPException(
            status_code=503,
            detail=str(error)
        ) from error

    # Оставляем только выбранную профессию
    vacancies = [
        vacancy
        for vacancy in all_vacancies
        if vacancy.get("profession") == canonical_profession
    ]

    # Ограничиваем количество результатов
    vacancies = vacancies[:10]

    print(
        f"Профессия: {canonical_profession}, "
        f"найдено вакансий: {len(vacancies)}"
    )

    return {
        "profession": canonical_profession,
        "level": request.level,
        "status": "success",
        "data_mode": "cached",
        "vacancies": vacancies,
        "forum_discussions": [],
        "warnings": [
            "Используются ранее собранные данные «Работы России».",
            f"Дата сбора: {collected_at or 'не указана'}.",
            "Фильтрация по уровню Junior/Middle/Senior пока не подключена.",
            "Парсинг форумов пока не подключён."
        ],
        "errors": []
    }