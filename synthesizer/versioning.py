from copy import deepcopy


def invalidate_stale_evidence(map_data: dict, transcript: list[dict]) -> dict:
    """
    Проверяет, актуальны ли доказательства после изменения стенограммы.
    Если сообщение удалено или его текст изменился,
    соответствующий узел требует повторной проверки.
    """
    result = deepcopy(map_data)

    active_messages = {
        message["id"]: message
        for message in transcript
    }

    versions = [
        message.get("version", 1)
        for message in transcript
    ]

    result["transcript_version"] = max(versions, default=1)

    for node in result.get("nodes", []):
        evidence = node.get("evidence", {})
        message_ids = evidence.get("evidence_message_ids", [])
        quotes = evidence.get("quotes", [])

        stale = False

        if len(message_ids) != len(quotes):
            stale = True
        else:
            for message_id, quote in zip(message_ids, quotes):
                current_message = active_messages.get(message_id)

                if current_message is None:
                    stale = True
                    break

                if current_message["text"] != quote:
                    stale = True
                    break

        node["evidence_status"] = "stale" if stale else "active"

        if stale:
            node["review_status"] = "needs_evidence"

            note = "Доказательство устарело: требуется повторная проверка."
            if note not in node.setdefault("review_notes", []):
                node["review_notes"].append(note)

    return result
