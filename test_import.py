import json
from pathlib import Path

from database.db_manager import (
    init_db,
    import_boyscout_payload,
    get_available_professions,
    get_vacancies,
    get_discussions,
    get_knowledge_base
)

# Загружаем настоящий JSON
payload_path = Path("data/sqlite_payload.json")

with payload_path.open("r", encoding="utf-8") as file:
    payload = json.load(file)

# Создаём чистую тестовую базу
init_db(test_mode=True)

# Импортируем данные
result = import_boyscout_payload(payload, test_mode=True)

print("Результат импорта:")
print(result)

# Проверяем данные по каждой профессии
for profession in get_available_professions(test_mode=True):
    vacancies = get_vacancies(
        profession, limit=1000, test_mode=True
    )
    discussions = get_discussions(
        profession, limit=1000, test_mode=True
    )
    knowledge = get_knowledge_base(
        profession, test_mode=True
    )

    print("\nПрофессия:", profession)
    print("Вакансий:", len(vacancies))
    print("Обсуждений:", len(discussions))
    print("База знаний найдена:", knowledge is not None)

    if knowledge:
        print("Caveats:", knowledge["caveats"])

# Проверяем повторный импорт
second_result = import_boyscout_payload(
    payload, test_mode=True
)

print("\nРезультат повторного импорта:")
print(second_result)