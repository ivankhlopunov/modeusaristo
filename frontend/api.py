import requests
from urllib.parse import quote

# Адрес FastAPI
MODEUS_API_URL = "http://127.0.0.1:8000"

N8N_WEBHOOK_URL = "http://localhost:5678/webhook/compose"

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


# Создание профиля эксперта
def build_persona(profession):

    try:
        response = requests.post(
            f"{MODEUS_API_URL}/api/ai/persona",
            json={"profession": profession},
            timeout=150
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка создания профиля эксперта:", error)
        return None


# Получение вопроса от Interviewer
def get_question(message, history=None):

    data = {
        "message": message,
        "history": history or []
    }

    try:
        response = requests.post(
            f"{MODEUS_API_URL}/api/ai/question",
            json=data,
            timeout=150
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка получения вопроса:", error)
        return None


# Получение ответа от Expert
def ask_expert(question, persona, facts, history=None):

    data = {
        "question": question,
        "persona": persona,
        "facts": facts,
        "history": history or []
    }

    try:
        response = requests.post(
            f"{MODEUS_API_URL}/api/ai/answer",
            json=data,
            timeout=150
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка получения ответа эксперта:", error)
        return None


# Формирование карты профессии через Synthesizer
def compose_via_n8n(profession, level, transcript, scout=None):

    data = {
        "profession": profession,
        "level": level,
        "transcript": transcript,
        "scout": scout
    }

    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=data,
            timeout=180
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("Ошибка формирования карты профессии:", error)
        return None
