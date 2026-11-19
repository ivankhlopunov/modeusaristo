
import sqlite3
import json
from pathlib import Path


# Путь к файлу базы данных
DB_PATH = Path(__file__).parent / "modeusaristo.db"
TEST_DB_PATH = Path(__file__).parent / "modeusaristo_test.db"


def get_connection(test_mode=False):
    """Создаёт подключение к основной или тестовой базе."""

    if test_mode:
        db_path = TEST_DB_PATH
    else:
        db_path = DB_PATH

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def get_profession_id(connection, profession):
    """Находит профессию или добавляет её."""

    connection.execute(
        "INSERT OR IGNORE INTO professions (name) VALUES (?)",
        (profession,)
    )

    result = connection.execute(
        "SELECT id FROM professions WHERE name = ?",
        (profession,)
    ).fetchone()

    return result["id"]


def json_to_text(value):
    """Преобразует Python-объект в JSON-строку."""

    if value is None:
        return None

    return json.dumps(value, ensure_ascii=False)


def validate_payload(payload):
    """Проверяет структуру входного JSON."""

    if not isinstance(payload, dict):
        raise ValueError("Payload должен быть словарём")

    if payload.get("schema_version") != 1:
        raise ValueError("Неподдерживаемая версия schema_version")

    if not isinstance(payload.get("generated_at"), str):
        raise ValueError("generated_at должен быть строкой")

    required_fields = {
        "vacancies": ["external_id", "profession", "source"],
        "forum_discussions": ["external_id", "profession", "source"],
        "knowledge_bases": ["profession"]
    }

    for key in required_fields:

        if key not in payload or not isinstance(payload[key], list):
            raise ValueError(f"Поле {key} должно содержать список")

        for number, item in enumerate(payload[key], start=1):

            if not isinstance(item, dict):
                raise ValueError(
                    f"Элемент {number} в {key} должен быть словарём"
                )

            for field in required_fields[key]:

                if field not in item or not item[field]:
                    raise ValueError(
                        f"В {key}, элементе {number}, "
                        f"отсутствует обязательное поле {field}"
                    )


def import_boyscout_payload(payload: dict, test_mode=False):
    """
    Импортирует вакансии, обсуждения и базы знаний BoyScout AI.
    Все изменения выполняются в одной транзакции.
    """

    validate_payload(payload)

    connection = get_connection(test_mode=test_mode)

    result = {
        "vacancies_imported": 0,
        "vacancies_skipped": 0,
        "discussions_imported": 0,
        "discussions_skipped": 0,
        "knowledge_bases_imported": 0,
        "knowledge_bases_skipped": 0
    }

    try:
        with connection:

            # Импорт вакансий
            for vacancy in payload["vacancies"]:

                if vacancy.get("is_mock") is True:
                    result["vacancies_skipped"] += 1
                    continue

                profession_id = get_profession_id(
                    connection,
                    vacancy["profession"]
                )

                connection.execute("""
                    INSERT INTO vacancies (
                        external_id, profession_id, source,
                        name, company, region,
                        salary_min, salary_max, currency,
                        experience, requirements, responsibilities,
                        description, skills, url,
                        published_at, collected_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                    ON CONFLICT(source, external_id) DO UPDATE SET
                        profession_id = excluded.profession_id,
                        name = excluded.name,
                        company = excluded.company,
                        region = excluded.region,
                        salary_min = excluded.salary_min,
                        salary_max = excluded.salary_max,
                        currency = excluded.currency,
                        experience = excluded.experience,
                        requirements = excluded.requirements,
                        responsibilities = excluded.responsibilities,
                        description = excluded.description,
                        skills = excluded.skills,
                        url = excluded.url,
                        published_at = excluded.published_at,
                        collected_at = excluded.collected_at
                """, (
                    str(vacancy["external_id"]),
                    profession_id,
                    vacancy["source"],
                    vacancy.get("name"),
                    vacancy.get("company"),
                    vacancy.get("region"),
                    vacancy.get("salary_min"),
                    vacancy.get("salary_max"),
                    vacancy.get("currency"),
                    vacancy.get("experience"),
                    json_to_text(vacancy.get("requirements")),
                    vacancy.get("responsibilities"),
                    vacancy.get("description"),
                    json_to_text(vacancy.get("skills")),
                    vacancy.get("url"),
                    vacancy.get("published_at"),
                    vacancy.get("collected_at")
                ))

                result["vacancies_imported"] += 1

            # Импорт обсуждений
            for discussion in payload["forum_discussions"]:

                if discussion.get("is_mock") is True:
                    result["discussions_skipped"] += 1
                    continue

                profession_id = get_profession_id(
                    connection,
                    discussion["profession"]
                )

                connection.execute("""
                    INSERT INTO forum_discussions (
                        external_id, profession_id, source,
                        title, text, answers, tags,
                        url, published_at, collected_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                    ON CONFLICT(source, external_id) DO UPDATE SET
                        profession_id = excluded.profession_id,
                        title = excluded.title,
                        text = excluded.text,
                        answers = excluded.answers,
                        tags = excluded.tags,
                        url = excluded.url,
                        published_at = excluded.published_at,
                        collected_at = excluded.collected_at
                """, (
                    str(discussion["external_id"]),
                    profession_id,
                    discussion["source"],
                    discussion.get("title"),
                    discussion.get("text"),
                    json_to_text(discussion.get("answers")),
                    json_to_text(discussion.get("tags")),
                    discussion.get("url"),
                    discussion.get("published_at"),
                    discussion.get("collected_at")
                ))

                result["discussions_imported"] += 1

            # Импорт баз знаний
            for knowledge in payload["knowledge_bases"]:

                if knowledge.get("is_mock") is True:
                    result["knowledge_bases_skipped"] += 1
                    continue

                profession_id = get_profession_id(
                    connection,
                    knowledge["profession"]
                )

                connection.execute("""
                    INSERT INTO knowledge_bases (
                        profession_id, vacancies_count,
                        discussions_count, median_salary_midpoint_rub,
                        salary_sample_count, top_skills,
                        responsibility_examples,
                        technical_question_examples,
                        caveats, ai_analysis, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(profession_id) DO UPDATE SET
                        vacancies_count = excluded.vacancies_count,
                        discussions_count = excluded.discussions_count,
                        median_salary_midpoint_rub =
                            excluded.median_salary_midpoint_rub,
                        salary_sample_count = excluded.salary_sample_count,
                        top_skills = excluded.top_skills,
                        responsibility_examples =
                            excluded.responsibility_examples,
                        technical_question_examples =
                            excluded.technical_question_examples,
                        caveats = excluded.caveats,
                        ai_analysis = excluded.ai_analysis,
                        updated_at = excluded.updated_at
                """, (
                    profession_id,
                    knowledge.get("vacancies_count"),
                    knowledge.get("discussions_count"),
                    knowledge.get("median_salary_midpoint_rub"),
                    knowledge.get("salary_sample_count"),
                    json_to_text(knowledge.get("top_skills")),
                    json_to_text(knowledge.get("responsibility_examples")),
                    json_to_text(knowledge.get("technical_question_examples")),
                    json_to_text(knowledge.get("caveats")),
                    json_to_text(knowledge.get("ai_analysis")),
                    knowledge.get("updated_at")
                ))

                result["knowledge_bases_imported"] += 1

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return result


def init_db(test_mode=False):
    """Создаёт необходимые таблицы, если их ещё нет."""

    connection = get_connection(test_mode)

    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS professions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT NOT NULL,
                profession_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                name TEXT,
                company TEXT,
                region TEXT,
                salary_min REAL,
                salary_max REAL,
                currency TEXT,
                experience TEXT,
                requirements TEXT,
                responsibilities TEXT,
                description TEXT,
                skills TEXT,
                url TEXT,
                published_at TEXT,
                collected_at TEXT,

                UNIQUE(source, external_id),

                FOREIGN KEY (profession_id)
                    REFERENCES professions(id)
            );

            CREATE TABLE IF NOT EXISTS forum_discussions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT NOT NULL,
                profession_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                title TEXT,
                text TEXT,
                answers TEXT,
                tags TEXT,
                url TEXT,
                published_at TEXT,
                collected_at TEXT,

                UNIQUE(source, external_id),

                FOREIGN KEY (profession_id)
                    REFERENCES professions(id)
            );

            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profession_id INTEGER UNIQUE NOT NULL,
                vacancies_count INTEGER,
                discussions_count INTEGER,
                median_salary_midpoint_rub REAL,
                salary_sample_count INTEGER,
                top_skills TEXT,
                responsibility_examples TEXT,
                technical_question_examples TEXT,
                caveats TEXT,
                ai_analysis TEXT,
                updated_at TEXT,

                FOREIGN KEY (profession_id)
                    REFERENCES professions(id)
            );
        """)

        # Проверяем, существует ли столбец caveats
        columns = connection.execute(
            "PRAGMA table_info(knowledge_bases)"
        ).fetchall()

        column_names = [column["name"] for column in columns]

        # Если столбца нет, добавляем его
        if "caveats" not in column_names:
            connection.execute(
                "ALTER TABLE knowledge_bases ADD COLUMN caveats TEXT"
            )

        # Добавляем начальный список профессий
        professions = [
            ("Python Developer",),
            ("Java Developer",),
            ("Data Analyst",)
        ]

        connection.executemany(
            "INSERT OR IGNORE INTO professions (name) VALUES (?)",
            professions
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_available_professions(test_mode=False):
    """Возвращает список доступных профессий."""

    connection = get_connection(test_mode)

    rows = connection.execute(
        "SELECT name FROM professions ORDER BY name"
    ).fetchall()

    connection.close()

    return [row["name"] for row in rows]


def get_vacancies(profession: str, limit: int = 10, test_mode=False):
    """Возвращает вакансии выбранной профессии."""

    connection = get_connection(test_mode)

    rows = connection.execute("""
        SELECT vacancies.*
        FROM vacancies
        JOIN professions
        ON vacancies.profession_id = professions.id
        WHERE professions.name = ?
        ORDER BY vacancies.id DESC
        LIMIT ?
    """, (profession, limit)).fetchall()

    connection.close()

    result = []

    for row in rows:
        item = dict(row)

        item["requirements"] = json.loads(
            item["requirements"]
        ) if item["requirements"] else None

        item["skills"] = json.loads(
            item["skills"]
        ) if item["skills"] else None

        result.append(item)

    return result


def get_discussions(profession: str, limit: int = 20, test_mode=False):
    """Возвращает обсуждения выбранной профессии."""

    connection = get_connection(test_mode)

    rows = connection.execute("""
        SELECT forum_discussions.*
        FROM forum_discussions
        JOIN professions
        ON forum_discussions.profession_id = professions.id
        WHERE professions.name = ?
        ORDER BY forum_discussions.id DESC
        LIMIT ?
    """, (profession, limit)).fetchall()

    connection.close()

    result = []

    for row in rows:
        item = dict(row)

        item["answers"] = json.loads(
            item["answers"]
        ) if item["answers"] else None

        item["tags"] = json.loads(
            item["tags"]
        ) if item["tags"] else None

        result.append(item)

    return result


def get_knowledge_base(profession: str, test_mode=False):
    """Возвращает базу знаний выбранной профессии."""

    connection = get_connection(test_mode)

    row = connection.execute("""
        SELECT knowledge_bases.*, professions.name AS profession
        FROM knowledge_bases
        JOIN professions
        ON knowledge_bases.profession_id = professions.id
        WHERE professions.name = ?
    """, (profession,)).fetchone()

    connection.close()

    if row is None:
        return None

    result = dict(row)

    json_fields = [
        "top_skills",
        "responsibility_examples",
        "technical_question_examples",
        "caveats",
        "ai_analysis"
    ]

    for field in json_fields:
        result[field] = (
            json.loads(result[field])
            if result[field] else None
        )

    return result
