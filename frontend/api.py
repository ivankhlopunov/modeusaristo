
import requests

API_URL = "https://httpbin.org/post"


def send_request(profession, description):
    # Данные для отправки
    data = {
        "profession": profession,
        "description": description
    }

    try:
        response = requests.post(
            API_URL,
            json=data,
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка HTTP-запроса:", error)
        return None


# Адрес нашего FastAPI
MODEUS_API_URL = "http://127.0.0.1:8000"


# Получаем список профессий
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


# Получаем вакансии профессии
def get_vacancies(profession, limit=10):
    try:
        response = requests.get(
            f"{MODEUS_API_URL}/api/professions/{profession}/vacancies",
            params={"limit": limit},
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка получения вакансий:", error)
        return None


# Получаем обсуждения профессии
def get_discussions(profession, limit=20):
    try:
        response = requests.get(
            f"{MODEUS_API_URL}/api/professions/{profession}/discussions",
            params={"limit": limit},
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка получения обсуждений:", error)
        return None


# Получаем базу знаний профессии
def get_knowledge_base(profession):
    try:
        response = requests.get(
            f"{MODEUS_API_URL}/api/professions/{profession}/knowledge-base",
            timeout=15
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка получения базы знаний:", error)
        return None
