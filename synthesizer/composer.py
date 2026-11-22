
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


def _as_list(value):
    """Возвращает список только для корректного списка."""
    return value if isinstance(value, list) else []


def _clean_strings(values):
    """Оставляет непустые строки без дубликатов."""
    result = []
    seen = set()

    for value in values:
        if not isinstance(value, str):
            continue

        value = value.strip()
        normalized = value.casefold()

        if value and normalized not in seen:
            seen.add(normalized)
            result.append(value)

    return result


def compose_map(profession, scout, transcript):
    if not isinstance(scout, dict):
        scout = {}

    if not isinstance(transcript, list):
        transcript = []

    # 1. Подготавливаем интервью
    messages = {
        message["id"]: message
        for message in transcript
        if (
            isinstance(message, dict)
            and isinstance(message.get("id"), str)
            and message["id"]
            and isinstance(message.get("text"), str)
        )
    }

    # 2. Получаем данные Backend
    vacancies = [
        item for item in _as_list(scout.get("vacancies"))
        if isinstance(item, dict)
    ]

    discussions = [
        item for item in _as_list(scout.get("forum_discussions"))
        if isinstance(item, dict)
    ]

    knowledge_base = scout.get("knowledge_base")
    if not isinstance(knowledge_base, dict):
        knowledge_base = {}

    ai_analysis = knowledge_base.get("ai_analysis")
    if not isinstance(ai_analysis, dict):
        ai_analysis = {}

    # 3. Собираем источники
    source_ids = []

    for item in vacancies + discussions:
        source_id = item.get("id")
        if source_id is not None and str(source_id).strip():
            source_ids.append(str(source_id))

    # Источники примеров обязанностей из knowledge_base
    responsibility_examples = []

    for example in _as_list(knowledge_base.get("responsibility_examples")):
        if not isinstance(example, dict):
            continue

        text = example.get("text")
        source_url = example.get("source_url")

        if not isinstance(text, str) or not text.strip():
            continue

        source_id = (
            source_url.strip()
            if isinstance(source_url, str) and source_url.strip()
            else None
        )

        if source_id:
            source_ids.append(source_id)

        responsibility_examples.append({
            "text": text.strip(),
            "source_id": source_id,
        })

    source_ids = list(dict.fromkeys(source_ids))

    # 4. Определяем демонстрационные данные
    is_mock = (
        scout.get("data_mode") == "mock"
        or any(item.get("is_mock", False) for item in vacancies + discussions)
        or any(message.get("is_mock", False) for message in messages.values())
    )

    data_mode = scout.get("data_mode", "unknown")
    if data_mode not in {"mock", "real", "unknown"}:
        data_mode = "unknown"

    if is_mock:
        data_mode = "mock"

    # 5. Формирование доказательств
    def make_evidence(message_ids=None, evidence_source_ids=None):
        message_ids = message_ids or []
        evidence_source_ids = evidence_source_ids or []

        valid_message_ids = [
            message_id
            for message_id in dict.fromkeys(message_ids)
            if message_id in messages
        ]

        valid_source_ids = [
            str(source_id)
            for source_id in dict.fromkeys(evidence_source_ids)
            if source_id is not None and str(source_id) in source_ids
        ]

        return {
            "evidence_message_ids": valid_message_ids,
            "evidence_source_ids": valid_source_ids,
            "quotes": [
                messages[message_id]["text"]
                for message_id in valid_message_ids
            ],
        }

    # 6. Извлекаем обязанности из вакансий
    responsibilities = []

    for vacancy in vacancies:
        vacancy_id = vacancy.get("id")
        vacancy_id = str(vacancy_id) if vacancy_id is not None else None

        for responsibility in _as_list(vacancy.get("responsibilities")):
            if isinstance(responsibility, str) and responsibility.strip():
                responsibilities.append({
                    "title": responsibility.strip(),
                    "source_id": vacancy_id,
                    "source_type": "vacancy",
                })

    # Добавляем примеры обязанностей из базы знаний.
    # Это кандидаты на проверку, а не подтверждённые задачи.
    for example in responsibility_examples:
        responsibilities.append({
            "title": example["text"],
            "source_id": example["source_id"],
            "source_type": "knowledge_base_example",
        })

    unique_responsibilities = []
    seen_responsibilities = set()

    for item in responsibilities:
        normalized = item["title"].casefold()

        if normalized not in seen_responsibilities:
            seen_responsibilities.add(normalized)
            unique_responsibilities.append(item)

    # 7. Навыки и требования из вакансий
    skills = []
    requirements = []
    vacancy_descriptions = []

    for vacancy in vacancies:
        skills.extend(
            item for item in _as_list(vacancy.get("skills"))
            if isinstance(item, str) and item.strip()
        )

        requirements.extend(
            item for item in _as_list(vacancy.get("requirements"))
            if isinstance(item, str) and item.strip()
        )

        description = vacancy.get("description")

        if isinstance(description, str) and description.strip():
            vacancy_descriptions.append({
                "text": description.strip(),
                "source_id": (
                    str(vacancy["id"])
                    if vacancy.get("id") is not None else None
                ),
            })

    # 8. Навыки из knowledge_base.top_skills
    top_skills = []

    for item in _as_list(knowledge_base.get("top_skills")):
        if not isinstance(item, dict):
            continue

        skill = item.get("skill")
        count = item.get("vacancies_count")

        if isinstance(skill, str) and skill.strip():
            top_skills.append({
                "skill": skill.strip(),
                "vacancies_count": count,
            })

    # 9. Данные обсуждений
    discussion_questions = []
    discussion_texts = []

    for discussion in discussions:
        questions = discussion.get("questions")

        if isinstance(questions, list):
            discussion_questions.extend(
                item for item in questions
                if isinstance(item, str) and item.strip()
            )

        title = discussion.get("title")
        text = discussion.get("text")

        discussion_id = discussion.get("id")
        discussion_id = (
            str(discussion_id) if discussion_id is not None else None
        )

        if isinstance(title, str) and title.strip():
            discussion_questions.append(title.strip())

        if isinstance(text, str) and text.strip():
            discussion_texts.append({
                "text": text.strip(),
                "source_id": discussion_id,
            })

    discussion_questions = _clean_strings(discussion_questions)
    skills = _clean_strings(skills)
    requirements = _clean_strings(requirements)

    # 10. Технические вопросы из базы знаний
    technical_questions = []

    for item in _as_list(
        knowledge_base.get("technical_question_examples")
    ):
        if not isinstance(item, dict):
            continue

        question = item.get("question")
        answer = item.get("answer_example")
        source_url = item.get("source_url")

        if not isinstance(question, str) or not question.strip():
            continue

        technical_questions.append({
            "question": question.strip(),
            "answer_example": answer if isinstance(answer, str) else "",
            "source_url": source_url if isinstance(source_url, str) else None,
            "published_at": item.get("published_at"),
        })

    # 11. Оговорки и AI-анализ
    caveats = _clean_strings(
        _as_list(knowledge_base.get("caveats"))
    )

    ai_context = {
        "profession_description": ai_analysis.get("profession_description"),
        "key_skills": _clean_strings(
            _as_list(ai_analysis.get("key_skills"))
        ),
        "typical_tasks": _clean_strings(
            _as_list(ai_analysis.get("typical_tasks"))
        ),
        "technical_challenges": _clean_strings(
            _as_list(ai_analysis.get("technical_challenges"))
        ),
        "interview_topics": _clean_strings(
            _as_list(ai_analysis.get("interview_topics"))
        ),
        "persona_context": _clean_strings(
            _as_list(ai_analysis.get("persona_context"))
        ),
    }

    # 12. Создаём корень карты
    profession_id = str(uuid4())

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

    # 13. Ищем сведения о профессиональных функциях в интервью
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
                "Функция сформирована на основе источников и/или интервью. Требуется проверка методологом."
            ],
        })

    else:
        methodologist_questions.append(
            "Какие основные функции выполняет специалист?"
        )

    # 14. Задачи и действия
    if function_id is not None:
        for responsibility in unique_responsibilities:
            is_example = (
                responsibility["source_type"] == "knowledge_base_example"
            )

            nodes.append({
                "id": str(uuid4()),
                "parent_id": function_id,
                "kind": "task",
                "title": responsibility["title"],
                "operationality": "uncertain" if is_example else "operational",
                "evidence": make_evidence(
                    evidence_source_ids=[responsibility["source_id"]]
                ),
                "review_status": "needs_review",
                "is_mock": is_mock,
                "review_notes": [
                    (
                        "Пример обязанности из базы знаний. "
                        "Необходимо подтвердить, что это реальная задача специалиста."
                        if is_example
                        else
                        "Задача извлечена из обязанностей вакансии. Требуется проверка методологом."
                    )
                ],
            })

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
                item["message_id"] for item in detected_actions
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

        if not unique_responsibilities and not detected_actions:
            methodologist_questions.append(
                "В источниках пока недостаточно конкретных обязанностей "
                "и действий. Уточните реальные задачи специалиста."
            )

    # 15. Вопросы методологу
    if skills or top_skills:
        skill_names = list(dict.fromkeys(
            skills + [item["skill"] for item in top_skills]
        ))

        methodologist_questions.append(
            "Проверьте необходимость следующих навыков: "
            + "; ".join(skill_names)
        )

    if requirements:
        methodologist_questions.append(
            "Проверьте требования к специалисту: "
            + "; ".join(requirements)
        )

    if discussion_questions:
        methodologist_questions.append(
            "Уточните следующие вопросы по профессии: "
            + "; ".join(discussion_questions)
        )

    if technical_questions:
        methodologist_questions.append(
            "Проверьте актуальность технических вопросов "
            "из базы знаний и их применимость к профессии."
        )

    if caveats:
        methodologist_questions.extend(caveats)

    if not source_ids and not messages:
        methodologist_questions.append(
            "Недостаточно исходных данных для построения карты."
        )

    # 16. Итоговая карта
    return {
        "profession": profession,
        "version": 1,
        "data_mode": data_mode,
        "nodes": nodes,
        "available_message_ids": list(messages.keys()),
        "available_source_ids": source_ids,
        "methodologist_questions": methodologist_questions,
        "scout_context": {
            "skills": skills,
            "requirements": requirements,
            "top_skills": top_skills,
            "discussion_questions": discussion_questions,
            "vacancy_descriptions": vacancy_descriptions,
            "discussion_texts": discussion_texts,
            "responsibility_examples": responsibility_examples,
            "technical_question_examples": technical_questions,
            "caveats": caveats,
            "ai_analysis": ai_context,
        },
    }
