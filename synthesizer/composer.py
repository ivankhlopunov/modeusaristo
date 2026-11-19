from uuid import uuid4


def compose_map(profession, scout, transcript):
    messages = {m["id"]: m for m in transcript}

    source_ids = []
    for section in ("vacancies", "forum_discussions"):
        for item in scout.get(section, []):
            if item.get("id"):
                source_ids.append(item["id"])

    is_mock = scout.get("data_mode") == "mock" or any(
        m.get("is_mock", False) for m in transcript
    )

    def make_evidence(message_id=None):
        message = messages.get(message_id) if message_id else None
        return {
            "evidence_message_ids": [message_id] if message else [],
            "evidence_source_ids": [],
            "quotes": [message["text"]] if message else [],
        }

    profession_id = str(uuid4())
    function_id = str(uuid4())
    task1_id = str(uuid4())
    task2_id = str(uuid4())

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
            "evidence": make_evidence("msg-001"),
            "review_status": "needs_evidence",
            "is_mock": is_mock,
            "review_notes": ["Требуется подтверждение"],
        },
        {
            "id": task1_id,
            "parent_id": function_id,
            "kind": "task",
            "title": "Разрабатывать простые API",
            "operationality": "operational",
            "evidence": make_evidence("msg-001"),
            "review_status": "needs_review",
            "is_mock": is_mock,
            "review_notes": [],
        },
        {
            "id": task2_id,
            "parent_id": function_id,
            "kind": "task",
            "title": "Диагностировать и исправлять ошибки",
            "operationality": "operational",
            "evidence": make_evidence("msg-002"),
            "review_status": "needs_review",
            "is_mock": is_mock,
            "review_notes": [],
        },
    ]

    actions = [
        ("Изучать логи", "msg-002"),
        ("Воспроизводить проблему", "msg-002"),
        ("Исправлять код", "msg-003"),
        ("Запускать тесты", "msg-003"),
    ]

    for title, message_id in actions:
        nodes.append({
            "id": str(uuid4()),
            "parent_id": task2_id,
            "kind": "action",
            "title": title,
            "operationality": "operational",
            "evidence": make_evidence(message_id),
            "review_status": "needs_review",
            "is_mock": is_mock,
            "review_notes": [],
        })

    return {
        "profession": profession,
        "version": 1,
        "data_mode": "mock" if is_mock else "real",
        "nodes": nodes,
        "available_message_ids": list(messages.keys()),
        "available_source_ids": source_ids,
    }