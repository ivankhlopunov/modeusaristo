
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
