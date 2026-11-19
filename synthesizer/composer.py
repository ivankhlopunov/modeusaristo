
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
]


def compose_map(profession, scout, transcript):
    messages = {
        message["id"]: message
        for message in transcript
    }

    source_ids = []

    for section in ("vacancies", "forum_discussions"):
        for item in scout.get(section, []):
            if item.get("id"):
                source_ids.append(item["id"])

    is_mock = (
        scout.get("data_mode") == "mock"
        or any(
            message.get("is_mock", False)
            for message in transcript
        )
    )

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

    function_message_ids = [
        message_id
        for message_id, message in messages.items()
        if re.search(
            r"\b(api|апи|программ|код)\w*",
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

    # Задача: разработка простых API.
    api_task_id = str(uuid4())

    api_message_ids = [
        message_id
        for message_id, message in messages.items()
        if re.search(
            r"\b(разрабатываю|создаю|пишу)\s+простые?\s+api\b",
            message["text"],
            re.IGNORECASE,
        )
    ]

    if api_message_ids:
        nodes.append(
            {
                "id": api_task_id,
                "parent_id": function_id,
                "kind": "task",
                "title": "Разрабатывать простые API",
                "operationality": "operational",
                "evidence": make_evidence(api_message_ids),
                "review_status": "needs_review",
                "is_mock": is_mock,
                "review_notes": [],
            }
        )

    # Задача: диагностика и исправление ошибок.
    error_actions = []

    for message_id, message in messages.items():
        for item in ACTION_PATTERNS:
            if re.search(
                item["pattern"],
                message["text"],
                re.IGNORECASE,
            ):
                error_actions.append(
                    {
                        "title": item["title"],
                        "message_id": message_id,
                    }
                )

    if error_actions:
        errors_task_id = str(uuid4())

        error_message_ids = list(
            dict.fromkeys(
                item["message_id"]
                for item in error_actions
            )
        )

        nodes.append(
            {
                "id": errors_task_id,
                "parent_id": function_id,
                "kind": "task",
                "title": "Диагностировать и исправлять ошибки",
                "operationality": "operational",
                "evidence": make_evidence(error_message_ids),
                "review_status": "needs_review",
                "is_mock": is_mock,
                "review_notes": [],
            }
        )

        for item in error_actions:
            nodes.append(
                {
                    "id": str(uuid4()),
                    "parent_id": errors_task_id,
                    "kind": "action",
                    "title": item["title"],
                    "operationality": "operational",
                    "evidence": make_evidence(
                        [item["message_id"]]
                    ),
                    "review_status": "needs_review",
                    "is_mock": is_mock,
                    "review_notes": [],
                }
            )

    # Если конкретные задачи не найдены, требуется проверка методологом.
    if not api_message_ids and not error_actions:
        nodes[1]["operationality"] = "uncertain"
        nodes[1]["review_status"] = "needs_evidence"
        nodes[1]["review_notes"].append(
            "Не удалось извлечь задачи и действия. "
            "Требуется дополнительная стенограмма."
        )

    methodologist_questions = []

    if not api_message_ids:
        methodologist_questions.append(
            "Какие API специалист разрабатывает и какие этапы работы выполняет?"
        )

    if not error_actions:
        methodologist_questions.append(
            "Какие конкретные действия специалист выполняет при диагностике ошибок?"
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
