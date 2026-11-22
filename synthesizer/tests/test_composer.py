
from copy import deepcopy
from fastapi.testclient import TestClient
from synthesizer.main import app

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


def test_composer_creates_expected_nodes():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)

    nodes = result["nodes"]

    assert len(nodes) == 7
    assert any(node["kind"] == "profession" for node in nodes)
    assert any(node["kind"] == "function" for node in nodes)
    assert any(node["kind"] == "task" for node in nodes)
    assert any(node["kind"] == "action" for node in nodes)
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
def test_accountant_does_not_get_software_development_function():
    scout = {
        "data_mode": "real",
        "vacancies": [],
        "forum_discussions": [],
    }

    transcript = [
        {
            "id": "msg-001",
            "speaker": "specialist",
            "text": (
                "Я проверяю первичные документы, "
                "сверяю счета и готовлю отчетность."
            ),
            "version": 1,
            "is_mock": False,
        }
    ]

    result = compose_map("Бухгалтер", scout, transcript)

    # Synthesizer не должен приписывать бухгалтеру функции программиста.
    functions = [
        node["title"]
        for node in result["nodes"]
        if node["kind"] == "function"
    ]

    assert "Разработка и поддержка программных решений" not in functions

    # Если функция не определена, система должна запросить уточнение.
    assert result["methodologist_questions"]
def test_compose_api_handles_empty_transcript(tmp_path, monkeypatch):
    import synthesizer.main as main

    # Сохраняем тестовую карту во временную папку,
    # чтобы не менять настоящую map.json.
    monkeypatch.setattr(
        main,
        "MAP_PATH",
        tmp_path / "map.json",
    )

    client = TestClient(app)

    response = client.post(
        "/compose",
        json={
            "profession": "Бухгалтер",
            "level": "Junior",
            "transcript": [],
            "scout": {
                "status": "success",
                "data_mode": "real",
                "vacancies": [],
                "forum_discussions": [],
            },
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["profession"] == "Бухгалтер"
    assert len(result["nodes"]) == 1
    assert result["nodes"][0]["kind"] == "profession"

def test_validator_rejects_non_dict_node():
    broken_map = {
        "nodes": [
            "это не словарь"
        ],
        "available_message_ids": [],
        "available_source_ids": [],
    }

    errors = validate_map(broken_map)

    assert errors
    assert any("должен быть объектом" in error for error in errors)


def test_validator_rejects_non_dict_evidence():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)
    broken_map = deepcopy(result)

    broken_map["nodes"][0]["evidence"] = "не объект"

    errors = validate_map(broken_map)

    assert any("evidence должен быть объектом" in error for error in errors)


def test_validator_rejects_invalid_evidence_fields():
    scout, transcript = sample_data()

    result = compose_map("Python Developer", scout, transcript)
    broken_map = deepcopy(result)

    broken_map["nodes"][0]["evidence"]["evidence_message_ids"] = "msg-001"

    errors = validate_map(broken_map)

    assert any(
        "evidence_message_ids должен быть списком" in error
        for error in errors
    )


def test_validator_rejects_non_dict_map():
    errors = validate_map(["это не карта"])

    assert errors == ["Карта должна быть объектом"]
