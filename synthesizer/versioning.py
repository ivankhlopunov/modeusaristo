
from copy import deepcopy


def invalidate_stale_evidence(map_data: dict, transcript: list[dict]) -> dict:
    result = deepcopy(map_data)

    active_messages = {
        message["id"]: message
        for message in transcript
    }

    versions = [message.get("version", 1) for message in transcript]
    result["transcript_version"] = max(versions, default=1)

    for node in result.get("nodes", []):
        evidence = node.get("evidence", {})
        message_ids = evidence.get("evidence_message_ids", [])
        quotes = evidence.get("quotes", [])

        stale = len(message_ids) != len(quotes)

        if not stale:
            for message_id, quote in zip(message_ids, quotes):
                current = active_messages.get(message_id)
                if current is None or current["text"] != quote:
                    stale = True
                    break

        node["evidence_status"] = "stale" if stale else "active"

        if stale:
            node["review_status"] = "needs_evidence"
            note = "Доказательство устарело: требуется повторная проверка."
            if note not in node.setdefault("review_notes", []):
                node["review_notes"].append(note)

    return result


def compare_with_previous_map(
    new_map: dict,
    previous_map: dict | None,
    transcript: list[dict],
) -> dict:
    result = deepcopy(new_map)

    if not previous_map:
        return result

    current_messages = {m["id"]: m for m in transcript}
    previous_nodes = previous_map.get("nodes", [])

    previous_by_key = {
        (node.get("kind"), node.get("title")): node
        for node in previous_nodes
    }

    changed = False

    for node in result.get("nodes", []):
        key = (node.get("kind"), node.get("title"))
        old_node = previous_by_key.get(key)

        if not old_node:
            continue

        old_evidence = old_node.get("evidence", {})
        old_ids = old_evidence.get("evidence_message_ids", [])
        old_quotes = old_evidence.get("quotes", [])

        stale = len(old_ids) != len(old_quotes)

        if not stale:
            for message_id, old_quote in zip(old_ids, old_quotes):
                current = current_messages.get(message_id)

                if current is None or current.get("text") != old_quote:
                    stale = True
                    break

        if stale:
            changed = True
            node["evidence_status"] = "stale"
            node["review_status"] = "needs_evidence"

            note = (
                "Стенограмма изменилась после предыдущей версии. "
                "Требуется повторная проверка методистом."
            )
            if note not in node.setdefault("review_notes", []):
                node["review_notes"].append(note)

    old_version = previous_map.get("transcript_version", 1)
    current_version = max(
        (m.get("version", 1) for m in transcript),
        default=1,
    )

    result["transcript_version"] = (
        max(old_version + 1, current_version)
        if changed
        else max(old_version, current_version)
    )

    return result
