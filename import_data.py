import json

from database.db_manager import init_db, import_boyscout_payload


# Открываем файл с данными BoyScout AI
with open("data/sqlite_payload.json", encoding="utf-8") as file:
    payload = json.load(file)


# Инициализируем основную базу данных
init_db()


# Импортируем данные в основную базу
result = import_boyscout_payload(payload)


# Выводим результат импорта
print("Результат импорта:")
print(result)
