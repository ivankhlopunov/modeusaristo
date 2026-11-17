import requests
import json

from pathlib import Path
from bs4 import BeautifulSoup


# Адрес API
API_URL = "https://www.arbeitnow.com/api/job-board-api"


def clean_html(html):

    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    return soup.get_text(separator=" ", strip=True)


def search_vacancies(profession, limit=10, max_pages=3):

    profession = profession.strip()

    if not profession:
        raise ValueError("Название профессии не может быть пустым")

    vacancies = []

    search_words = profession.casefold().split()

    for page in range(1, max_pages + 1):

        params = {
            "page": page
        }

        response = requests.get(
            API_URL,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        jobs = data.get("data", [])

        if not jobs:
            break

        for job in jobs:

            title = job.get("title") or ""

            title_lower = title.casefold()

            if not all(
                word in title_lower
                for word in search_words
            ):
                continue

            vacancy = {
                "id": job.get("slug"),
                "name": title,
                "company": job.get("company_name"),
                "salary": None,
                "experience": None,
                "skills": job.get("tags") or [],
                "requirements": [],
                "responsibilities": [],
                "description": clean_html(
                    job.get("description")
                ),
                "location": job.get("location"),
                "remote": job.get("remote", False),
                "url": job.get("url"),
                "source": "arbeitnow",
                "is_mock": False
            }

            vacancies.append(vacancy)

            if len(vacancies) >= limit:
                return vacancies

    return vacancies


def save_vacancies(profession, vacancies):

    result = {
        "profession": profession,
        "source": "arbeitnow",
        "vacancies": vacancies
    }

    folder = Path(__file__).resolve().parent / "data"

    folder.mkdir(exist_ok=True)

    file_path = folder / "arbeitnow_vacancies.json"

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=4
        )

    return file_path


if __name__ == "__main__":

    profession = input("Введите профессию: ")

    try:

        vacancies = search_vacancies(
            profession,
            limit=10,
            max_pages=3
        )

        file_path = save_vacancies(
            profession,
            vacancies
        )

        print("Поиск завершён!")
        print("Профессия:", profession)
        print("Найдено вакансий:", len(vacancies))
        print("Файл:", file_path)

        for vacancy in vacancies:

            print()
            print("Название:", vacancy["name"])
            print("Компания:", vacancy["company"])
            print("Город:", vacancy["location"])
            print("Ссылка:", vacancy["url"])

    except requests.RequestException as error:

        print("Ошибка запроса к Arbeitnow:", error)

    except ValueError as error:

        print("Ошибка:", error)
        