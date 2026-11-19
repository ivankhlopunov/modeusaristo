from synthesizer.composer import compose_map
from synthesizer.validator import validate_map


def sample_data():
    scout = {
        "data_mode": "mock",
        "vacancies": [{"id": "mock-001"}],
        "forum_discussions": []
    }

    transcript = [
        {
            "id": "msg-001",
            "speaker": "specialist",
            "text": "Я разрабатываю простые API на Python.",
            "is_mock": True
        },
        {
            "id": "msg-002",
            "speaker": "specialist",
            "text": "Я изучаю логи и воспроизвожу проблему.",
            "is_mock": True
        },
        {
            "id": "msg-003",
            "speaker": "specialist",
            "text": "Я исправляю код и запускаю тесты.",
            "is_mock": True
        }
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

    assert validate_map(result) == []


def test_every_action_has_parent():
    scout, transcript = sample_data()
    result = compose_map("Python Developer", scout, transcript)

    for node in result["nodes"]:
        if node["kind"] == "action":
            assert node["parent_id"] is not None