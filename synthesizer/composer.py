
from uuid import uuid4
import re


ACTION_PATTERNS = [
    {
        "pattern": r"\bизучаю\s+(логи|журналы)\b",
        "title": "Изучать логи",
    },
    {
        "pattern": r"\bвоспроизвожу\s+(проблему|ошибку)\b",
        "title": "Воспроизводить проблему",
    },
    {
        "pattern": r"\bисправляю\s+(код|ошибки)\b",
        "title": "Исправлять код",
    },
    {
        "pattern": r"\bзапускаю\s+тесты\b",
        "title": "Запускать тесты",
    },
    {
        "pattern": r"\bпишу\s+тесты\b",
        "title": "Писать тесты",
    },
    {
        "pattern": r"\bпроверяю\s+(код|работу|результат)\b",
        "title": "Проверять код и результат",
    },
    {
        "pattern": r"\bсоздаю\s+функции\b",
        "title": "Создавать функции",
    },
]


def compose_map(profession, scout, transcript):

    # Сохраняем исходные сообщения без изменения текста.
    messages = {
        message["id"]: message
        for message in transcript
        if message.get("id") and isinstance(message.get("text"), str)
    }

    source_ids = []

    for section in ("vacancies", "forum_discussions"):
        for item in scout.get(section, []):
            if isinstance(item, dict) and item.get("id"):
                source_ids.append(item["id"])

    source_ids = list(dict.fromkeys(source_ids))

    is_mock = (
        scout.get("data_mode") == "mock"
        or any(
            message.get("is_mock", False)
            for message in transcript
        )
    )

    # Создание доказательств.
    def make_evidence(message_ids):
        valid_ids = [
            message_id
            for message_id in dict.fromkeys(message_ids)
            if message_id in messages
        ]

        return {
            "evidence_message_ids": valid_ids,
            "evidence_source_ids": [],
            "quotes": [
                messages[message_id]["text"]
                for message_id in valid_ids
            ],
        }

    profession_id = str(uuid4())
    function_id = str(uuid4())

    # Ищем сообщения, подтверждающие функцию.
    function_message_ids = [
        message_id
        for message_id, message in messages.items()
        if re.search(
            r"\b(api|апи|программ\w*|код\w*)",
            message["text"],
            re.IGNORECASE,
        )
    ]

    nodes = [
        {
            "id": profession_id,
            "parent_id": None,
            "kind": "profession",
            "title": profession,
            "operationality": "non_operational",
            "evidence": {
                "evidence_message_ids": [],
                "evidence_source_ids": source_ids,
                "quotes": [],
            },
            "review_status": "needs_review",
            "is_mock": is_mock,
            "review_notes": [],
        },
        {
            "id": function_id,
            "parent_id": profession_id,
            "kind": "function",
            "title": "Разработка и поддержка программных решений",
            "operationality": "uncertain",
            "evidence": make_evidence(function_message_ids),
            "review_status": "needs_review",
            "is_mock": is_mock,
            "review_notes": [
                "Функция сформирована по ключевым словам. "
                "Требуется проверка методологом."
            ],
        },
    ]

    methodologist_questions = []

    # Ищем задачу по разработке API.
    api_message_ids = [
        message_id
        for message_id, message in messages.items()
        if re.search(
            r"\b(разрабатываю|создаю|пишу)\s+"
            r"(простые?\s+)?api\b",
            message["text"],
            re.IGNORECASE,
        )
    ]

    if api_message_ids:
        nodes.append({
            "id": str(uuid4()),
            "parent_id": function_id,
            "kind": "task",
            "title": "Разрабатывать API на Python",
            "operationality": "operational",
            "evidence": make_evidence(api_message_ids),
            "review_status": "needs_review",
            "is_mock": is_mock,
            "review_notes": [],
        })
    else:
        methodologist_questions.append(
            "Какие API специалист разрабатывает "
            "и какие этапы работы выполняет?"
        )

    # Ищем конкретные действия.
    error_actions = []

    for message_id, message in messages.items():
        for item in ACTION_PATTERNS:
            if re.search(
                item["pattern"],
                message["text"],
                re.IGNORECASE,
            ):
                error_actions.append({
                    "title": item["title"],
                    "message_id": message_id,
                })

    # Группируем действия в задачу.
    if error_actions:
        errors_task_id = str(uuid4())

        error_message_ids = list(dict.fromkeys(
            item["message_id"]
            for item in error_actions
        ))

        nodes.append({
            "id": errors_task_id,
            "parent_id": function_id,
            "kind": "task",
            "title": "Диагностировать и исправлять ошибки",
            "operationality": "operational",
            "evidence": make_evidence(error_message_ids),
            "review_status": "needs_review",
            "is_mock": is_mock,
            "review_notes": [],
        })

        for item in error_actions:
            nodes.append({
                "id": str(uuid4()),
                "parent_id": errors_task_id,
                "kind": "action",
                "title": item["title"],
                "operationality": "operational",
                "evidence": make_evidence([item["message_id"]]),
                "review_status": "needs_review",
                "is_mock": is_mock,
                "review_notes": [],
            })
    else:
        methodologist_questions.append(
            "Какие конкретные действия выполняет специалист "
            "при диагностике и исправлении ошибок?"
        )

    # Вопросы методологу.
    if function_message_ids:
        methodologist_questions.append(
            "Какие именно функции выполняет специалист "
            "при разработке и поддержке программных решений?"
        )
    else:
        methodologist_questions.append(
            "Какие основные функции выполняет специалист?"
        )

    # Отмечаем недостаток доказательств.
    if not api_message_ids and not error_actions:
        nodes[1]["review_status"] = "needs_evidence"
        nodes[1]["review_notes"].append(
            "Не удалось извлечь задачи и действия. "
            "Требуется дополнительная стенограмма."
        )

    return {
        "profession": profession,
        "version": 1,
        "data_mode": "mock" if is_mock else "real",
        "nodes": nodes,
        "available_message_ids": list(messages.keys()),
        "available_source_ids": source_ids,
        "methodologist_questions": methodologist_questions,
    }
