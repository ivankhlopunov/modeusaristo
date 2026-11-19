
import requests


class N8NClient:
    """Stateless-клиент для взаимодействия с AI-агентами в n8n."""

    def __init__(self):
        self.persona_url = "http://localhost:5678/webhook/persona"

        self.interviewer_url = (
            "http://localhost:5678/webhook/"
            "633fd7b3-de53-4967-a744-a2c4c202a99b"
        )

        self.expert_url = (
            "http://localhost:5678/webhook/persona/respond"
        )

        self.timeout = 120

    def _post(self, url, payload):
        """Отправляет POST-запрос и возвращает JSON-ответ."""

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            result = response.json()

            if not result.get("ok"):
                raise RuntimeError(
                    f"Ошибка n8n: {result.get('error')}"
                )

            return result

        except requests.exceptions.Timeout:
            raise RuntimeError(
                "Превышено время ожидания ответа от n8n."
            )

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Не удалось подключиться к n8n. "
                "Проверь, запущен ли n8n."
            )

        except requests.exceptions.HTTPError as error:
            raise RuntimeError(
                f"HTTP-ошибка: {error}"
            )

        except ValueError:
            raise RuntimeError(
                "n8n вернул некорректный JSON."
            )

    def build_persona(self, facts):
        """Создаёт синтетическую персону."""

        return self._post(
            self.persona_url,
            {"facts": facts}
        )

    def get_question(self, message, history):
        """Получает следующий вопрос интервьюера."""

        return self._post(
            self.interviewer_url,
            {
                "message": message,
                "history": history
            }
        )

    def ask_expert(self, question, persona, facts, history):
        """Передаёт вопрос синтетическому эксперту."""

        return self._post(
            self.expert_url,
            {
                "question": question,
                "persona": persona,
                "facts": facts,
                "history": history
            }
        )
