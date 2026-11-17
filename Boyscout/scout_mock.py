"""Демонстрационный источник данных Scout. Не содержит реального парсинга."""

from datetime import datetime, timezone
import json
from pathlib import Path


DEMO = {
    "python developer": {
        "skills": ["Python", "SQL", "Git", "HTTP", "REST API"],
        "requirements": ["Знать базовый синтаксис Python", "Понимать HTTP-запросы", "Уметь пользоваться Git"],
        "responsibilities": ["Разрабатывать простые API", "Исправлять ошибки", "Писать тесты"],
        "questions": ["Чем список отличается от кортежа?", "Что означает HTTP 404?", "Для чего нужен git commit?"],
    },
    "бухгалтер": {
        "skills": ["Бухгалтерский учёт", "Excel", "Первичная документация"],
        "requirements": ["Понимать основы бухгалтерского учёта", "Уметь работать с таблицами"],
        "responsibilities": ["Обрабатывать первичные документы", "Проводить сверки"],
        "questions": ["Что такое дебет и кредит?", "Как проверить корректность первичного документа?"],
    },
}


def get_mock_scout_data(profession: str, level: str = "Junior") -> dict:
    profession = profession.strip()
    if not profession:
        raise ValueError("Название профессии не может быть пустым")

    example = DEMO.get(profession.casefold())
    warnings = ["Все записи демонстрационные, не получены с hh.ru или форумов."]
    if example is None:
        example = {"skills": [], "requirements": [], "responsibilities": [], "questions": []}
        warnings.append("Для этой профессии нет предметных демонстрационных сведений.")

    collected_at = datetime.now(timezone.utc).isoformat()
    vacancy = {
        "id": "mock-vacancy-001", "name": profession, "company": "Demo Company",
        "salary": None, "experience": "Не указано", "skills": example["skills"],
        "requirements": example["requirements"], "responsibilities": example["responsibilities"],
        "description": "Искусственный пример для проверки интеграции.",
        "url": None, "source": "mock", "is_mock": True,
    }
    discussion = {
        "id": "mock-forum-001", "title": f"Учебные вопросы: {profession}",
        "text": "Демонстрационное обсуждение; не цитата реального форума.",
        "questions": example["questions"], "topics": example["skills"],
        "url": None, "source": "mock", "is_mock": True,
    }
    return {
        "profession": profession, "level": level, "status": "success", "data_mode": "mock",
        "collected_at": collected_at, "vacancies": [vacancy],
        "forum_discussions": [discussion], "warnings": warnings, "errors": [],
    }


def save_mock_data(data: dict) -> Path:
    folder = Path(__file__).resolve().parent / "data"
    folder.mkdir(exist_ok=True)
    path = folder / "scout_result.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    profession = input("Введите профессию: ")
    level = input("Уровень [Junior]: ").strip() or "Junior"
    result = get_mock_scout_data(profession, level)
    print("Демонстрационный результат:", save_mock_data(result))
