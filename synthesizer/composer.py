
from uuid import uuid4
import re


ACTION_PATTERNS = [
    {"pattern": r"\bизучаю\s+(логи|журналы)\b", "title": "Изучать логи"},
    {"pattern": r"\bвоспроизвожу\s+(проблему|ошибку)\b", "title": "Воспроизводить проблему"},
    {"pattern": r"\bисправляю\s+(код|ошибки)\b", "title": "Исправлять код"},
    {"pattern": r"\bзапускаю\s+тесты\b", "title": "Запускать тесты"},
    {"pattern": r"\bпишу\s+тесты\b", "title": "Писать тесты"},
    {"pattern": r"\bпроверяю\s+(код|работу|результат)\b", "title": "Проверять код и результат"},
    {"pattern": r"\bсоздаю\s+функции\b", "title": "Создавать функции"},
]


def compose_map(profession, scout, transcript):
    # Проверяем входные данные
    if not isinstance(scout, dict):
        scout = {}

    if not isinstance(transcript, list):
        transcript = []

    # Подготавливаем сообщения интервью
    messages = {
        message["id"]: message
        for message in transcript
        if isinstance(message, dict)
        and message.get("id")
        and isinstance(message.get("text"), str)
    }

    # Получаем вакансии и обсуждения Scout
    vacancies = [
        item for item in scout.get("vacancies", [])
        if isinstance(item, dict)
    ]

    discussions = [
        item for item in scout.get("forum_discussions", [])
        if isinstance(item, dict)
    ]

    # Собираем ID источников
    source_ids = []

    for item in vacancies + discussions:
        if item.get("id"):
            source_ids.append(item["id"])

    source_ids = list(dict.fromkeys(source_ids))

    # Определяем, являются ли данные демонстрационными
    is_mock = (
        scout.get("data_mode") == "mock"
        or any(item.get("is_mock", False) for item in vacancies + discussions)
        or any(message.get("is_mock", False) for message in messages.values())
    )

    # Формирование доказательств
    def make_evidence(message_ids=None, evidence_source_ids=None):
        message_ids = message_ids or []
        evidence_source_ids = evidence_source_ids or []

        valid_message_ids = [
            message_id
            for message_id in dict.fromkeys(message_ids)
            if message_id in messages
        ]

        valid_source_ids = [
            source_id
            for source_id in dict.fromkeys(evidence_source_ids)
            if source_id in source_ids
        ]

        return {
            "evidence_message_ids": valid_message_ids,
            "evidence_source_ids": valid_source_ids,
            "quotes": [
                messages[message_id]["text"]
                for message_id in valid_message_ids
            ],
        }

    # Извлекаем обязанности из вакансий
    responsibilities = []

    for vacancy in vacancies:
        vacancy_id = vacancy.get("id")

        vacancy_responsibilities = vacancy.get("responsibilities", [])

        if not isinstance(vacancy_responsibilities, list):
            continue

        for responsibility in vacancy_responsibilities:
            if isinstance(responsibility, str) and responsibility.strip():
                responsibilities.append({
                    "title": responsibility.strip(),
                    "source_id": vacancy_id,
                })

    # Убираем дубликаты обязанностей
    unique_responsibilities = []
    seen_responsibilities = set()

    for item in responsibilities:
        normalized = item["title"].casefold()

        if normalized not in seen_responsibilities:
            seen_responsibilities.add(normalized)
            unique_responsibilities.append(item)

    # Извлекаем навыки, требования и описания вакансий
    skills = []
    requirements = []
    vacancy_descriptions = []

    for vacancy in vacancies:
        vacancy_skills = vacancy.get("skills", [])
        vacancy_requirements = vacancy.get("requirements", [])

        if isinstance(vacancy_skills, list):
            skills.extend(
                item for item in vacancy_skills
                if isinstance(item, str) and item.strip()
            )

        if isinstance(vacancy_requirements, list):
            requirements.extend(
                item for item in vacancy_requirements
                if isinstance(item, str) and item.strip()
            )

        description = vacancy.get("description")

        if isinstance(description, str) and description.strip():
            vacancy_descriptions.append({
                "text": description.strip(),
                "source_id": vacancy.get("id"),
            })

    # Извлекаем данные обсуждений
    discussion_questions = []
    discussion_texts = []

    for discussion in discussions:
        questions = discussion.get("questions", [])

        if isinstance(questions, list):
            discussion_questions.extend(
                item for item in questions
                if isinstance(item, str) and item.strip()
            )

        discussion_text = discussion.get("text")

        if isinstance(discussion_text, str) and discussion_text.strip():
            discussion_texts.append({
                "text": discussion_text.strip(),
                "source_id": discussion.get("id"),
            })

    # Убираем повторяющиеся значения
    skills = list(dict.fromkeys(skills))
    requirements = list(dict.fromkeys(requirements))
    discussion_questions = list(dict.fromkeys(discussion_questions))

    profession_id = str(uuid4())

    # Создаём узел профессии
    nodes = [{
        "id": profession_id,
        "parent_id": None,
        "kind": "profession",
        "title": profession,
        "operationality": "non_operational",
        "evidence": make_evidence(evidence_source_ids=source_ids),
        "review_status": "needs_review",
        "is_mock": is_mock,
        "review_notes": [],
    }]

    methodologist_questions = []

    # Ищем профессиональные сведения в интервью
    function_message_ids = [
        message_id
        for message_id, message in messages.items()
        if re.search(
            r"\b(api|апи|программ\w*|код\w*)",
            message["text"],
            re.IGNORECASE,
        )
    ]

    has_professional_data = bool(
        unique_responsibilities or function_message_ids
    )

    function_id = None

    # Создаём функцию
    if has_professional_data:
        function_id = str(uuid4())

        software_context = bool(function_message_ids) or any(
            re.search(
                r"\b(python|программирование|разработка|software|api)\b",
                item["title"],
                re.IGNORECASE,
            )
            for item in unique_responsibilities
        )

        function_title = (
            "Разработка и поддержка программных решений"
            if software_context
            else "Выполнение профессиональных функций"
        )

        function_source_ids = [
            item["source_id"]
            for item in unique_responsibilities
            if item["source_id"]
        ]

        nodes.append({
            "id": function_id,
            "parent_id": profession_id,
            "kind": "function",
            "title": function_title,
            "operationality": "uncertain",
            "evidence": make_evidence(
                message_ids=function_message_ids,
                evidence_source_ids=function_source_ids,
            ),
            "review_status": "needs_review",
            "is_mock": is_mock,
            "review_notes": [
                "Функция сформирована на основе вакансий и/или интервью. Требуется проверка методологом."
            ],
        })

    else:
        methodologist_questions.append(
            "Какие основные функции выполняет специалист?"
        )

    # Создаём задачи и действия
    if function_id is not None:

        # Задачи из обязанностей вакансий
        for responsibility in unique_responsibilities:
            nodes.append({
                "id": str(uuid4()),
                "parent_id": function_id,
                "kind": "task",
                "title": responsibility["title"],
                "operationality": "operational",
                "evidence": make_evidence(
                    evidence_source_ids=[responsibility["source_id"]],
                ),
                "review_status": "needs_review",
                "is_mock": is_mock,
                "review_notes": [
                    "Задача извлечена из обязанностей вакансии. Требуется проверка методологом."
                ],
            })

        # Действия из интервью
        detected_actions = []

        for message_id, message in messages.items():
            for pattern in ACTION_PATTERNS:
                if re.search(
                    pattern["pattern"],
                    message["text"],
                    re.IGNORECASE,
                ):
                    detected_actions.append({
                        "title": pattern["title"],
                        "message_id": message_id,
                    })

        if detected_actions:
            task_id = str(uuid4())

            action_message_ids = list(dict.fromkeys(
                item["message_id"]
                for item in detected_actions
            ))

            nodes.append({
                "id": task_id,
                "parent_id": function_id,
                "kind": "task",
                "title": "Диагностировать и исправлять ошибки",
                "operationality": "operational",
                "evidence": make_evidence(
                    message_ids=action_message_ids
                ),
                "review_status": "needs_review",
                "is_mock": is_mock,
                "review_notes": [],
            })

            for action in detected_actions:
                nodes.append({
                    "id": str(uuid4()),
                    "parent_id": task_id,
                    "kind": "action",
                    "title": action["title"],
                    "operationality": "operational",
                    "evidence": make_evidence(
                        message_ids=[action["message_id"]]
                    ),
                    "review_status": "needs_review",
                    "is_mock": is_mock,
                    "review_notes": [],
                })

        # Если нет задач и действий, просим уточнить информацию
        if not unique_responsibilities and not detected_actions:
            methodologist_questions.append(
                "В источниках пока недостаточно конкретных обязанностей "
                "и действий. Уточните реальные задачи специалиста."
            )

    # Вопросы по навыкам
    if skills:
        methodologist_questions.append(
            "Проверьте необходимость следующих навыков: "
            + "; ".join(skills)
        )

    # Вопросы по требованиям
    if requirements:
        methodologist_questions.append(
            "Проверьте требования к специалисту: "
            + "; ".join(requirements)
        )

    # Вопросы по обсуждениям
    if discussion_questions:
        methodologist_questions.append(
            "Уточните следующие вопросы по профессии: "
            + "; ".join(discussion_questions)
        )

    # Если источников нет
    if not source_ids and not messages:
        methodologist_questions.append(
            "Недостаточно исходных данных для построения карты."
        )

    # Итоговая карта
    return {
        "profession": profession,
        "version": 1,
        "data_mode": "mock" if is_mock else "real",
        "nodes": nodes,
        "available_message_ids": list(messages.keys()),
        "available_source_ids": source_ids,
        "methodologist_questions": methodologist_questions,
        "scout_context": {
            "skills": skills,
            "requirements": requirements,
            "discussion_questions": discussion_questions,
            "vacancy_descriptions": vacancy_descriptions,
            "discussion_texts": discussion_texts,
        },
    }
