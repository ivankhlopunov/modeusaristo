
KINDS = {"profession", "function", "task", "action"}

OPERATIONALITY = {
    "operational",
    "non_operational",
    "uncertain",
}

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

    # Проверяем саму карту
    if not isinstance(data, dict):
        return ["Карта должна быть объектом"]

    nodes = data.get("nodes", [])

    if not isinstance(nodes, list) or not nodes:
        return ["Карта пустая или nodes не является списком"]

    # Проверяем, что каждый узел является словарём
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(
                f"Узел с индексом {index} должен быть объектом"
            )

    # Оставляем только корректные словари для дальнейшей проверки
    valid_nodes = [
        node for node in nodes
        if isinstance(node, dict)
    ]

    # Проверяем ID
    ids = [node.get("id") for node in valid_nodes]

    if any(
        not isinstance(node_id, str) or not node_id.strip()
        for node_id in ids
    ):
        errors.append("У каждого узла должен быть непустой строковый ID")

    valid_ids = [
        node_id for node_id in ids
        if isinstance(node_id, str) and node_id.strip()
    ]

    if len(valid_ids) != len(set(valid_ids)):
        errors.append("Повторяются ID узлов")

    node_by_id = {
        node["id"]: node
        for node in valid_nodes
        if isinstance(node.get("id"), str)
        and node["id"].strip()
    }

    # Проверяем корневой узел
    roots = [
        node for node in valid_nodes
        if node.get("parent_id") is None
    ]

    if len(roots) != 1 or roots[0].get("kind") != "profession":
        errors.append(
            "Должен быть ровно один корневой узел kind=profession"
        )

    # Проверяем доступные ID сообщений и источников
    available_messages = data.get("available_message_ids", [])
    available_sources = data.get("available_source_ids", [])

    if not isinstance(available_messages, list):
        errors.append("available_message_ids должен быть списком")
        available_messages = []

    if not isinstance(available_sources, list):
        errors.append("available_source_ids должен быть списком")
        available_sources = []

    message_ids = {
        item for item in available_messages
        if isinstance(item, str)
    }

    source_ids = {
        item for item in available_sources
        if isinstance(item, str)
    }

    # Проверяем каждый узел
    for node in valid_nodes:
        node_id = node.get("id", "<без ID>")
        kind = node.get("kind")

        if kind not in KINDS:
            errors.append(f"{node_id}: неправильный kind")
            continue

        # Название
        if (
            not isinstance(node.get("title"), str)
            or not node["title"].strip()
        ):
            errors.append(f"{node_id}: пустое название")

        # Операционность
        if node.get("operationality") not in OPERATIONALITY:
            errors.append(f"{node_id}: неправильный operationality")

        # Статус проверки
        if node.get("review_status", "needs_review") not in REVIEW_STATUSES:
            errors.append(f"{node_id}: неправильный review_status")

        # Проверка родителя
        parent_id = node.get("parent_id")
        expected_parent = EXPECTED_PARENT[kind]

        if expected_parent is None:
            if parent_id is not None:
                errors.append(
                    f"{node_id}: профессия не должна иметь родителя"
                )

        elif parent_id is None:
            errors.append(f"{node_id}: отсутствует родитель")

        elif not isinstance(parent_id, str):
            errors.append(f"{node_id}: ID родителя должен быть строкой")

        elif parent_id not in node_by_id:
            errors.append(f"{node_id}: родитель не найден")

        elif node_by_id[parent_id].get("kind") != expected_parent:
            errors.append(
                f"{node_id}: для {kind} родитель должен иметь "
                f"kind={expected_parent}"
            )

        # Проверка evidence
        evidence = node.get("evidence", {})

        if not isinstance(evidence, dict):
            errors.append(f"{node_id}: evidence должен быть объектом")
            continue

        evidence_messages = evidence.get("evidence_message_ids", [])
        evidence_sources = evidence.get("evidence_source_ids", [])
        quotes = evidence.get("quotes", [])

        if not isinstance(evidence_messages, list):
            errors.append(
                f"{node_id}: evidence_message_ids должен быть списком"
            )
            evidence_messages = []

        if not isinstance(evidence_sources, list):
            errors.append(
                f"{node_id}: evidence_source_ids должен быть списком"
            )
            evidence_sources = []

        if not isinstance(quotes, list):
            errors.append(f"{node_id}: quotes должен быть списком")
            quotes = []

        if len(evidence_messages) != len(quotes):
            errors.append(
                f"{node_id}: количество цитат не совпадает с сообщениями"
            )

        for message_id in evidence_messages:
            if not isinstance(message_id, str):
                errors.append(
                    f"{node_id}: ID сообщения должен быть строкой"
                )
            elif message_id not in message_ids:
                errors.append(
                    f"{node_id}: сообщение {message_id} не найдено"
                )

        for source_id in evidence_sources:
            if not isinstance(source_id, str):
                errors.append(
                    f"{node_id}: ID источника должен быть строкой"
                )
            elif source_id not in source_ids:
                errors.append(
                    f"{node_id}: источник {source_id} не найден"
                )

        for quote in quotes:
            if not isinstance(quote, str):
                errors.append(
                    f"{node_id}: каждая цитата должна быть строкой"
                )

    return errors
