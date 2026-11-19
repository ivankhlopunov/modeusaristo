
from database.db_manager import (
    get_vacancies,
    get_discussions,
    get_knowledge_base
)


def build_facts(profession):
    """Формирует факты о профессии на основе SQLite."""

    vacancies = get_vacancies(profession, limit=1000)
    discussions = get_discussions(profession, limit=1000)
    knowledge_base = get_knowledge_base(profession)

    facts = []

    if knowledge_base is None:
        return facts

    analysis = knowledge_base.get("ai_analysis") or {}
    knowledge_id = knowledge_base["id"]

    # Профессиональные задачи из базы знаний
    for task in analysis.get("typical_tasks", []):
        if isinstance(task, str) and task.strip():
            facts.append({
                "task": task.strip(),
                "tool": [],
                "error": [],
                "quality_check": [],
                "evidence_ids": [f"knowledge_base:{knowledge_id}"]
            })

    # Технологии, используемые в профессии
    skills = analysis.get("key_skills") or []

    if skills:
        facts.append({
            "task": "Использование технологий при разработке приложений",
            "tool": skills,
            "error": [],
            "quality_check": [],
            "evidence_ids": [f"knowledge_base:{knowledge_id}"]
        })

    # Обязанности и способы проверки из вакансий
    for vacancy in vacancies:
        responsibilities = vacancy.get("responsibilities") or ""

        # Не добавляем слишком большие описания вакансий
        if not responsibilities.strip() or len(responsibilities) > 600:
            continue

        quality_check = []
        text = responsibilities.lower()

        if "pytest" in text:
            quality_check.append("Модульные и интеграционные тесты с pytest")

        if "тест" in text and not quality_check:
            quality_check.append("Проведение тестирования")

        if "кодревью" in text or "code review" in text:
            quality_check.append("Проверка кода (Code Review)")

        facts.append({
            "task": responsibilities.strip(),
            "tool": vacancy.get("skills") or [],
            "error": [],
            "quality_check": quality_check,
            "evidence_ids": [f"vacancy:{vacancy['id']}"]
        })

    # Проблемы из обсуждений
    problem_words = (
        "ошибка",
        "проблема",
        "не работает",
        "не могут",
        "не срабатывает",
        "missinggreenlet"
    )

    for discussion in discussions:
        title = discussion.get("title") or ""
        body = discussion.get("body") or ""

        if not title:
            continue

        title_lower = title.lower()

        # Берём только обсуждения с явными признаками проблемы
        if any(word in title_lower for word in problem_words):
            facts.append({
                "task": f"Решение технической проблемы: {title}",
                "tool": [],
                "error": [title],
                "quality_check": [],
                "evidence_ids": [f"discussion:{discussion['id']}"]
            })

    return facts
