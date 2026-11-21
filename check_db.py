import sqlite3

db = sqlite3.connect("database/modeusaristo.db")

tables = db.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()

print("Таблицы:")
for table in tables:
    print(table[0])

professions = db.execute(
    "SELECT * FROM professions"
).fetchall()

print("\nПрофессии:")
for profession in professions:
    print(profession)

db.close()
