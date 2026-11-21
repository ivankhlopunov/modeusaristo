import requests
from urllib.parse import quote

# Адрес FastAPI
MODEUS_API_URL = "http://127.0.0.1:8000"


# Начало исследования профессии
def send_request(profession, level):

    data = {
        "profession": profession,
        "level": level
    }

    try:
        response = requests.post(
            f"{MODEUS_API_URL}/scout/search",
            json=data,
            timeout=60
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка начала исследования:", error)
        return None


# Получение списка профессий
def get_professions():

    try:
        response = requests.get(
            f"{MODEUS_API_URL}/api/professions",
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка получения профессий:", error)
        return None


# Получение вакансий профессии
def get_vacancies(profession, limit=10):

    try:
        response = requests.get(
            f"{MODEUS_API_URL}/api/professions/{quote(profession, safe='')}/vacancies",
            params={"limit": limit},
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка получения вакансий:", error)
        return None


# Получение обсуждений профессии
def get_discussions(profession, limit=20):

    try:
        response = requests.get(
            f"{MODEUS_API_URL}/api/professions/{quote(profession, safe='')}/discussions",
            params={"limit": limit},
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка получения обсуждений:", error)
        return None


# Получение базы знаний профессии
def get_knowledge_base(profession):

    try:
        response = requests.get(
            f"{MODEUS_API_URL}/api/professions/{quote(profession, safe='')}/knowledge-base",
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка получения базы знаний:", error)
        return None
