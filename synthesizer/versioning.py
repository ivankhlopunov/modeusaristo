
from copy import deepcopy


def invalidate_stale_evidence(map_data: dict, transcript: list[dict]) -> dict:
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

            note = (
                "Доказательство устарело: "
                "требуется повторная проверка."
            )

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

    current_messages = {
        message["id"]: message
        for message in transcript
    }

    previous_nodes = previous_map.get("nodes", [])

    transcript_changed = False

    for old_node in previous_nodes:
        evidence = old_node.get("evidence", {})

        message_ids = evidence.get("evidence_message_ids", [])
        quotes = evidence.get("quotes", [])

        if len(message_ids) != len(quotes):
            transcript_changed = True
            break

        for message_id, old_quote in zip(message_ids, quotes):
            current = current_messages.get(message_id)

            if current is None or current.get("text") != old_quote:
                transcript_changed = True
                break

        if transcript_changed:
            break

    old_version = previous_map.get("transcript_version", 1)

    current_version = max(
        (message.get("version", 1) for message in transcript),
        default=1,
    )

    if transcript_changed:
        result["transcript_version"] = max(
            old_version + 1,
            current_version,
        )
    else:
        result["transcript_version"] = max(
            old_version,
            current_version,
        )

    return result
