KINDS = {"profession", "function", "task", "action"}
OPERATIONALITY = {"operational", "non_operational", "uncertain"}


def validate_map(data: dict) -> list[str]:
    errors = []
    nodes = data.get("nodes", [])

    if not nodes:
        return ["Карта пустая"]

    ids = [node.get("id") for node in nodes]

    if len(ids) != len(set(ids)):
        errors.append("Повторяются ID узлов")

    known_ids = set(ids)
    message_ids = set(data.get("available_message_ids", []))
    source_ids = set(data.get("available_source_ids", []))

    for node in nodes:
        node_id = node.get("id")

        if node.get("kind") not in KINDS:
            errors.append(f"{node_id}: неправильный kind")

        if node.get("operationality") not in OPERATIONALITY:
            errors.append(f"{node_id}: неправильный operationality")

        parent_id = node.get("parent_id")
        if parent_id is not None and parent_id not in known_ids:
            errors.append(f"{node_id}: родитель не найден")

        evidence = node.get("evidence", {})

        for mid in evidence.get("evidence_message_ids", []):
            if mid not in message_ids:
                errors.append(f"{node_id}: сообщение {mid} не найдено")

        for sid in evidence.get("evidence_source_ids", []):
            if sid not in source_ids:
                errors.append(f"{node_id}: источник {sid} не найден")

    return errors