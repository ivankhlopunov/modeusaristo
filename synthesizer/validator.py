
KINDS = {"profession", "function", "task", "action"}
OPERATIONALITY = {"operational", "non_operational", "uncertain"}
REVIEW_STATUSES = {
    "needs_review",
    "needs_evidence",
    "approved",
    "rejected",
}

EXPECTED_PARENT = {
    "profession": None,
    "function": "profession",
    "task": "function",
    "action": "task",
}


def validate_map(data: dict) -> list[str]:
    errors = []
    nodes = data.get("nodes", [])

    if not isinstance(nodes, list) or not nodes:
        return ["Карта пустая или nodes не является списком"]

    ids = [node.get("id") for node in nodes]
    if any(not isinstance(node_id, str) or not node_id for node_id in ids):
        errors.append("У каждого узла должен быть непустой строковый ID")

    if len(ids) != len(set(ids)):
        errors.append("Повторяются ID узлов")

    node_by_id = {
        node["id"]: node
        for node in nodes
        if isinstance(node.get("id"), str) and node["id"]
    }

    roots = [node for node in nodes if node.get("parent_id") is None]
    if len(roots) != 1 or roots[0].get("kind") != "profession":
        errors.append("Должен быть ровно один корневой узел kind=profession")

    message_ids = set(data.get("available_message_ids", []))
    source_ids = set(data.get("available_source_ids", []))

    for node in nodes:
        node_id = node.get("id", "<без ID>")
        kind = node.get("kind")

        if kind not in KINDS:
            errors.append(f"{node_id}: неправильный kind")
            continue

        if not isinstance(node.get("title"), str) or not node["title"].strip():
            errors.append(f"{node_id}: пустое название")

        if node.get("operationality") not in OPERATIONALITY:
            errors.append(f"{node_id}: неправильный operationality")

        if node.get("review_status", "needs_review") not in REVIEW_STATUSES:
            errors.append(f"{node_id}: неправильный review_status")

        parent_id = node.get("parent_id")
        expected_parent = EXPECTED_PARENT[kind]

        if expected_parent is None:
            if parent_id is not None:
                errors.append(f"{node_id}: профессия не должна иметь родителя")
        elif parent_id is None:
            errors.append(f"{node_id}: отсутствует родитель")
        elif parent_id not in node_by_id:
            errors.append(f"{node_id}: родитель не найден")
        elif node_by_id[parent_id].get("kind") != expected_parent:
            errors.append(
                f"{node_id}: для {kind} родитель должен иметь kind={expected_parent}"
            )

        evidence = node.get("evidence", {})
        if not isinstance(evidence, dict):
            errors.append(f"{node_id}: evidence должен быть объектом")
            continue

        evidence_messages = evidence.get("evidence_message_ids", [])
        evidence_sources = evidence.get("evidence_source_ids", [])
        quotes = evidence.get("quotes", [])

        if len(evidence_messages) != len(quotes):
            errors.append(f"{node_id}: количество цитат не совпадает с сообщениями")

        for message_id in evidence_messages:
            if message_id not in message_ids:
                errors.append(f"{node_id}: сообщение {message_id} не найдено")

        for source_id in evidence_sources:
            if source_id not in source_ids:
                errors.append(f"{node_id}: источник {source_id} не найден")

    return errors
