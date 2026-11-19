
from copy import deepcopy

from synthesizer.composer import compose_map
from synthesizer.validator import validate_map
from synthesizer.versioning import (
    invalidate_stale_evidence,
    compare_with_previous_map,
)


def sample_data():
    scout = {
        "status": "success",
        "data_mode": "mock",
        "vacancies": [
            {"id": "mock-vacancy-001"}
        ],
        "forum_discussions": [
            {"id": "mock-forum-001"}
        ],
    }

    transcript = [
        {
            "id": "msg-001",
            "speaker": "specialist",
            "text": "Я разрабатываю простые API на Python.",
            "version": 1,
            "is_mock": True,
        },
        {
            "id": "msg-002",
            "speaker": "specialist",
            "text": (
                "Когда API возвращает ошибку, я изучаю логи "
                "и воспроизвожу проблему."
            ),
            "version": 1,
            "is_mock": True,
        },
        {
            "id": "msg-003",
            "speaker": "specialist",
            "text": "После этого исправляю код и запускаю тесты.",
            "version": 1,
            "is_mock": True,
        },
    ]

    return scout, transcript


def test_composer_creates_eight_nodes():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)

    assert len(result["nodes"]) == 8


def test_all_node_types_exist():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)

    kinds = {node["kind"] for node in result["nodes"]}

    assert kinds == {"profession", "function", "task", "action"}


def test_mock_data_is_marked():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)

    assert result["data_mode"] == "mock"
    assert all(node["is_mock"] for node in result["nodes"])


def test_evidence_is_valid():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)

    errors = validate_map(result)

    assert errors == []


def test_every_action_has_parent():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)

    nodes = {node["id"]: node for node in result["nodes"]}

    for node in result["nodes"]:
        if node["kind"] == "action":
            assert node["parent_id"] in nodes
            assert nodes[node["parent_id"]]["kind"] == "task"


def test_edited_message_invalidates_evidence():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)

    edited_transcript = deepcopy(transcript)
    edited_transcript[0]["text"] = "Я разрабатываю приложения на Django."
    edited_transcript[0]["version"] = 2

    updated = invalidate_stale_evidence(result, edited_transcript)

    affected = [
        node for node in updated["nodes"]
        if "msg-001" in node.get("evidence", {}).get(
            "evidence_message_ids", []
        )
    ]

    assert affected
    assert all(node["evidence_status"] == "stale" for node in affected)


def test_deleted_message_invalidates_evidence():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)

    edited_transcript = [
        message for message in transcript
        if message["id"] != "msg-001"
    ]

    updated = invalidate_stale_evidence(result, edited_transcript)

    affected = [
        node for node in updated["nodes"]
        if "msg-001" in node.get("evidence", {}).get(
            "evidence_message_ids", []
        )
    ]

    assert affected
    assert all(node["evidence_status"] == "stale" for node in affected)


def test_previous_map_detects_edited_message():
    scout, transcript = sample_data()

    previous = compose_map("Python Developer", scout, transcript)

    edited_transcript = [
        {
            **message,
            "text": "Я разрабатываю приложения на Django.",
            "version": 2,
        }
        if message["id"] == "msg-001"
        else message
        for message in transcript
    ]

    new_map = compose_map(
        "Python Developer",
        scout,
        edited_transcript,
    )

    updated = compare_with_previous_map(
        new_map,
        previous,
        edited_transcript,
    )

    assert updated["transcript_version"] == 2


def test_validator_rejects_wrong_hierarchy():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)

    broken_map = deepcopy(result)

    action = next(
        node for node in broken_map["nodes"]
        if node["kind"] == "action"
    )

    action["parent_id"] = broken_map["nodes"][0]["id"]

    errors = validate_map(broken_map)

    assert errors
