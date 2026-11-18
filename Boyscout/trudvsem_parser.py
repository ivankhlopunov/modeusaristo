import json
import requests
from pathlib import Path
import re
import time
from datetime import datetime, timezone
professions = {"Python Developer": ["Python Developer", "Python разработчик", "Программист Python"],
                "Java Developer": ["Java Developer", "Java разработчик", "Программист Java"],
                "Data Analyst": ["Аналитик данных", "Data Analyst", "SQL аналитик"]}

API_URL = "https://opendata.trudvsem.ru/api/v1/vacancies"
MAX_PAGES = 3
PAGE_SIZE = 100
REQUEST_DELAY = 1
DATA_DIR = Path(__file__).resolve().parent / "data"
HEADERS = {"User-Agent": "ModeusAristoBoyScout/1.0", "Accept": "application/json"}
def clean(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

SKILLS = {
    "Python": ["python"],
    "Java": ["java"],
    "Django": ["django"],
    "FastAPI": ["fastapi"],
    "Flask": ["flask"],
    "Spring": ["spring"],
    "SQL": ["sql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "Redis": ["redis"],
    "RabbitMQ": ["rabbitmq"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Git": ["git"],
    "GitLab CI": ["gitlab-ci", "gitlab ci"],
    "Linux": ["linux"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Power BI": ["power bi"],
    "Excel": ["excel"],
    "aiohttp": ["aiohttp"],
    "dramatiq": ["dramatiq"],
    "APScheduler": ["apscheduler"],
}


def extract_skills(text):

    found_skills = []

    text = text.lower()

    for skill, keywords in SKILLS.items():

        for keyword in keywords:

            pattern = (
                r"(?<![a-zа-яё0-9])"
                + re.escape(keyword)
                + r"(?![a-zа-яё0-9])"
            )

            if re.search(pattern, text):

                found_skills.append(skill)
                break

    return found_skills

def fetch_vacancies(query, offset=0, limit=100):
    params = {
        "text": query,
        "offset": offset,
        "limit": limit,
    }

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):

        try:
            print(
                f"\nЗапрос: {query}, "
                f"offset={offset}, "
                f"попытка {attempt}/{max_attempts}"
            )

            response = requests.get(
                API_URL,
                params=params,
                headers=HEADERS,
                timeout=8,
            )

            print(
                f"HTTP-статус: {response.status_code}"
            )

            if response.status_code in [500, 502, 503, 504, 429]:

                if attempt < max_attempts:

                    wait_time = 2 ** attempt

                    print(
                        f"Сервер временно недоступен. "
                        f"Повтор через {wait_time} сек."
                    )

                    time.sleep(wait_time)

                    continue

                print("Превышено количество попыток")
                return None

            response.raise_for_status()

            data = response.json()

            if str(data.get("status", "200")) != "200":
                print(
                    "Ошибка внутри JSON:",
                    data.get("meta")
                )
                return None

            results = data.get("results", {})

            if not isinstance(results, dict):
                print("Неожиданный формат results")
                return None

            vacancies = results.get("vacancies", [])

            if not isinstance(vacancies, list):
                print("Неожиданный формат vacancies")
                return None

            print(
                f"Загружено вакансий: {len(vacancies)}"
            )

            return vacancies

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError
        ) as error:

            print(f"Ошибка подключения: {error}")

            if attempt < max_attempts:
                time.sleep(2 ** attempt)
                continue

            return None

        except requests.exceptions.RequestException as error:

            print(f"Ошибка HTTP: {error}")
            return None

        except ValueError as error:

            print(f"Ошибка обработки JSON: {error}")
            return None

    return None
    
def normalize_vacancy(item, profession):
    """
    Преобразует вакансию из API «Работы России»
    в единый формат для Scout.
    """

    vacancy = item.get("vacancy", {})

    if not isinstance(vacancy, dict):
        return None

    # 1. Получаем основные данные

    vacancy_id = vacancy.get("id")

    company = vacancy.get("company") or {}
    if not isinstance(company, dict):
        company = {}

    region = vacancy.get("region") or {}
    if not isinstance(region, dict):
        region = {}

    title = clean(vacancy.get("job-name"))

    if not title:
        return None

    external_id = (
        str(vacancy_id)
        if vacancy_id is not None
        else clean(vacancy.get("vac_url"))
    )
    requirements = vacancy.get("requirement") or {}
    if isinstance(requirements, str):
        try:
            requirements = json.loads(requirements)
        except json.JSONDecodeError:
            requirements = {"text": requirements}
    if not isinstance(requirements, dict):
        requirements = {"text": clean(requirements)}
    responsibilities = clean(
        vacancy.get("duty")
    )
    description = clean(
        vacancy.get("description")
    )
    skills_text = " ".join([
        title,
        responsibilities,
        description,
        clean(requirements)
    ])
    skills = extract_skills(skills_text)
    experience = requirements.get("experience")
    result = {
        "id": external_id,
        "profession": profession,
        "name": title,
        "company": clean(company.get("name")),
        "salary_min": vacancy.get("salary_min"),
        "salary_max": vacancy.get("salary_max"),
        "currency": vacancy.get("currency") or "RUB",
        "region": clean(region.get("name")),
        "experience": experience,
        "schedule": clean(vacancy.get("schedule")),
        "employment": clean(vacancy.get("employment")),
        "requirements": requirements,
        "responsibilities": responsibilities,
        "description": description,
        "skills": skills,
        "url": vacancy.get("vac_url"),
        "published_at": vacancy.get("creation-date"),
        "source": "trudvsem",
        "is_mock": False,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }

    return result

def is_relevant_vacancy(vacancy, profession):
    title = vacancy.get("name", "").lower()

    if profession == "Python Developer":
        return (
            "python" in title
            or "питон" in title
        )

    elif profession == "Java Developer":
        return (
            bool(re.search(r"\bjava\b", title))
            and "javascript" not in title
        )

    elif profession == "Data Analyst":
        return (
            "аналитик данных" in title
            or "data analyst" in title
            or "sql аналитик" in title
            or "sql-аналитик" in title
        )

    return False

def collect_profession(profession, queries):
    print(f"\nПоиск профессии: {profession}")
    collected = {}
    for query in queries:
        print(f"\nПоисковый запрос: {query}")
        for page in range(MAX_PAGES):
            offset = page * PAGE_SIZE
            vacancies = fetch_vacancies(
                query=query,
                offset=offset,
                limit=PAGE_SIZE,
            )
            if vacancies is None:
                print("Не удалось загрузить страницу")
                break
            if not vacancies:
                print("Больше вакансий нет")
                break
            print(f"Получено вакансий: {len(vacancies)}")
            for item in vacancies:
                normalized = normalize_vacancy(
                    item,
                    profession,
                )
                if normalized is None:
                    continue
                if not is_relevant_vacancy(
                    normalized,
                    profession,
                ):
                    continue
                vacancy_id = normalized["id"]
                if not vacancy_id:
                    continue
                unique_key = f"trudvsem:{vacancy_id}"
                collected[unique_key] = normalized
            time.sleep(REQUEST_DELAY)
            if len(vacancies) < PAGE_SIZE:
                break
    result = list(collected.values())
    print(
        f"\nНайдено уникальных вакансий "
        f"для {profession}: {len(result)}"
    )
    return result

def save_to_json(data):
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    today = datetime.now().strftime("%Y-%m-%d")
    filename = DATA_DIR / f"trudvsem_{today}.json"
    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4,
        )

    print(f"\nДанные сохранены: {filename}")

def search_vacancies(profession, limit=10, max_pages=3):
    if limit <= 0 or max_pages <= 0:
        return []
    profession_mapping = {
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

    normalized_name = profession.strip().lower()

    canonical_profession = profession_mapping.get(
        normalized_name
    )

    if canonical_profession is None:
        raise ValueError(
            f"Профессия «{profession}» пока не поддерживается"
        )

    queries = professions[canonical_profession]

    unique_vacancies = {}

    for query in queries:

        for page in range(max_pages):

            offset = page * PAGE_SIZE

            items = fetch_vacancies(
                query=query,
                offset=offset,
                limit=PAGE_SIZE
            )

            if items is None:
                break

            if not items:
                break

            for item in items:

                vacancy = normalize_vacancy(
                    item,
                    canonical_profession
                )

                if vacancy is None:
                    continue

                if not is_relevant_vacancy(
                    vacancy,
                    canonical_profession
                ):
                    continue

                vacancy_id = vacancy.get("id")

                if not vacancy_id:
                    continue

                unique_key = f"trudvsem:{vacancy_id}"

                unique_vacancies[unique_key] = vacancy

                if len(unique_vacancies) >= limit:
                    return list(unique_vacancies.values())

            if len(items) < PAGE_SIZE:
                break

            time.sleep(REQUEST_DELAY)

    return list(unique_vacancies.values())

def main():
    print("=" * 50)
    print("MODEUSARISTO — SCOUT")
    print("Парсинг вакансий «Работы России»")
    print("=" * 50)
    all_vacancies = []
    for profession, queries in professions.items():
        vacancies = collect_profession(
            profession,
            queries,
        )

        all_vacancies.extend(vacancies)

    print("\n" + "=" * 50)

    print(
        f"ВСЕГО СОБРАНО: "
        f"{len(all_vacancies)} вакансий"
    )

    print("=" * 50)

    result = {
        "source": "trudvsem",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "professions": list(professions.keys()),
        "total": len(all_vacancies),
        "vacancies": all_vacancies,
    }

    save_to_json(result)

if __name__ == "__main__":
    main()