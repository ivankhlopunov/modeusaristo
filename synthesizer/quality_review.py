
def quality_review(map_data: dict) -> dict:
    """Проверяет качество карты профессии."""

    nodes = map_data.get("nodes", [])
    issues = []
    checked_nodes = 0

    node_by_id = {
        node["id"]: node
        for node in nodes
        if isinstance(node, dict) and node.get("id")
    }

    for node in nodes:
        if not isinstance(node, dict):
            issues.append({
                "type": "invalid_node",
                "message": "Узел карты должен быть объектом."
            })
            continue

        checked_nodes += 1
        node_id = node.get("id", "unknown")
        kind = node.get("kind")
        title = node.get("title", "")
        evidence = node.get("evidence", {})

        if not isinstance(title, str) or not title.strip():
            issues.append({
                "type": "empty_title",
                "node_id": node_id,
                "message": "У узла отсутствует название."
            })

        if not isinstance(evidence, dict):
            evidence = {}

        if kind in {"task", "action"}:
            if node.get("operationality") != "operational":
                issues.append({
                    "type": "non_operational",
                    "node_id": node_id,
                    "message": "Задача или действие недостаточно операциональны."
                })

        if node.get("operationality") == "uncertain":
            issues.append({
                "type": "uncertain_operationality",
                "node_id": node_id,
                "message": "Требуется уточнить операциональность узла."
            })

        if (
            not evidence.get("evidence_message_ids")
            and not evidence.get("evidence_source_ids")
        ):
            issues.append({
                "type": "missing_evidence",
                "node_id": node_id,
                "message": "У узла отсутствуют подтверждающие доказательства."
            })

        if node.get("review_status") != "approved":
            issues.append({
                "type": "not_approved",
                "node_id": node_id,
                "message": "Узел ещё не утверждён методологом."
            })

        parent_id = node.get("parent_id")

        if kind != "profession" and parent_id not in node_by_id:
            issues.append({
                "type": "missing_parent",
                "node_id": node_id,
                "message": "У узла отсутствует родитель."
            })

    return {
        "status": "passed" if not issues else "needs_review",
        "checked_nodes": checked_nodes,
        "issues_count": len(issues),
        "issues": issues,
        "recommendation": (
            "Карта прошла проверку."
            if not issues
            else "Перед утверждением карты требуется проверка методологом."
        )
    }
