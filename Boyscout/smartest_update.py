import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = Path(__file__).resolve().parent / "data" / "smart_update_status.json"
MAX_AGE = timedelta(hours=24)
VACANCY_LIMIT = 100
VACANCY_MAX_PAGES = 3
MODEL = "qwen2.5:3b"

ALIASES = {
    "python developer": "Python Developer",
    "python разработчик": "Python Developer",
    "python-разработчик": "Python Developer",
    "программист python": "Python Developer",
    "java developer": "Java Developer",
    "java разработчик": "Java Developer",
    "java-разработчик": "Java Developer",
    "программист java": "Java Developer",
    "data analyst": "Data Analyst",
    "аналитик данных": "Data Analyst",
    "sql аналитик": "Data Analyst",
}

_LOCK = threading.RLock()
_RUNNING = set()
_ERRORS = {}


def canonical_profession(name):
    key = " ".join(str(name or "").strip().casefold().split())
    profession = ALIASES.get(key)
    if not profession:
        raise ValueError(f"Профессия пока не поддерживается: {name}")
    return profession


def _read_status():
    if not STATUS_FILE.exists():
        return {}
    try:
        with STATUS_FILE.open("r", encoding="utf-8") as file:
            result = json.load(file)
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_status(status):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATUS_FILE.with_name(STATUS_FILE.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(status, file, ensure_ascii=False, indent=2)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, STATUS_FILE)


def _last_update(profession):
    record = _read_status().get(profession, {})
    raw = record.get("updated_at") if isinstance(record, dict) else None
    if not raw:
        return None
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _get_data(profession):
    from database.db_manager import get_vacancies, get_discussions, get_knowledge_base, init_db

    init_db()
    vacancies = get_vacancies(profession, limit=10)
    discussions = get_discussions(profession, limit=20)
    knowledge = get_knowledge_base(profession)
    return {
        "vacancies": vacancies or [],
        "forum_discussions": discussions or [],
        "knowledge_base": knowledge,
    }


def _perform_refresh(profession):
    from Boyscout.trudvsem_parcer_mass import search_vacancies
    from Boyscout.forum_parser import collect_profession, PROFESSIONS
    from Boyscout.BoyScout_AI import (
        normalize_vacancy,
        normalize_discussion,
        deduplicate,
        build_knowledge,
        ollama_summary,
    )
    from database.db_manager import init_db, import_boyscout_payload

    raw_vacancies = search_vacancies(
        profession,
        limit=VACANCY_LIMIT,
        max_pages=VACANCY_MAX_PAGES,
    )
    raw_discussions = collect_profession(
        profession,
        PROFESSIONS[profession],
    )

    vacancies = []
    for raw in raw_vacancies:
        normalized = normalize_vacancy(raw)
        if isinstance(normalized, dict) and not normalized.get("is_mock", False):
            vacancies.append(normalized)
    vacancies = deduplicate(vacancies, "vacancy")

    discussions = []
    for raw in raw_discussions:
        normalized = normalize_discussion(raw)
        if isinstance(normalized, dict) and not normalized.get("is_mock", False):
            discussions.append(normalized)
    discussions = deduplicate(discussions, "discussion")

    if not vacancies and not discussions:
        raise RuntimeError("Источники не предоставили подходящих данных; предыдущая база сохранена")

    knowledge = build_knowledge(profession, vacancies, discussions)
    if not isinstance(knowledge, dict):
        raise RuntimeError("build_knowledge не вернула словарь")

    analysis = ollama_summary(knowledge, MODEL)
    if not isinstance(analysis, dict):
        raise RuntimeError("Qwen не завершила анализ; предыдущая база сохранена")
    knowledge["ai_analysis"] = analysis

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vacancies": vacancies,
        "forum_discussions": discussions,
        "knowledge_bases": [knowledge],
    }

    init_db()
    import_boyscout_payload(payload)
    return len(vacancies), len(discussions)


def _refresh_worker(profession):
    try:
        vacancy_count, discussion_count = _perform_refresh(profession)
        with _LOCK:
            state = _read_status()
            state[profession] = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "vacancies_received": vacancy_count,
                "discussions_received": discussion_count,
            }
            _write_status(state)
            _ERRORS.pop(profession, None)
    except Exception as exc:
        with _LOCK:
            _ERRORS[profession] = str(exc)
        print(f"Smart Update: не удалось обновить {profession}: {exc}", flush=True)
    finally:
        with _LOCK:
            _RUNNING.discard(profession)


def maybe_schedule_refresh(profession, background_tasks: BackgroundTasks, force=False):
    profession = canonical_profession(profession)
    with _LOCK:
        last = _last_update(profession)
        stale = last is None or datetime.now(timezone.utc) - last >= MAX_AGE
        if profession in _RUNNING:
            return "processing", last
        if not force and not stale:
            return "fresh", last
        _RUNNING.add(profession)
        background_tasks.add_task(_refresh_worker, profession)
        return "scheduled", last


def research_for_site(profession, background_tasks: BackgroundTasks, force=False):
    try:
        profession = canonical_profession(profession)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        data = _get_data(profession)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения SQLite: {exc}") from exc

    state, last = maybe_schedule_refresh(profession, background_tasks, force=force)
    return {
        "profession": profession,
        "vacancies": data["vacancies"],
        "forum_discussions": data["forum_discussions"],
        "knowledge_base": data["knowledge_base"],
        "data_mode": "cached" if data["knowledge_base"] else "loading",
        "refresh_status": state,
        "updated_at": last.isoformat() if last else None,
        "error": _ERRORS.get(profession),
    }


def refresh_status(profession):
    try:
        profession = canonical_profession(profession)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with _LOCK:
        last = _last_update(profession)
        if profession in _RUNNING:
            state = "processing"
        elif profession in _ERRORS:
            state = "failed"
        elif last is not None:
            state = "completed"
        else:
            state = "not_started"
        return {
            "profession": profession,
            "status": state,
            "updated_at": last.isoformat() if last else None,
            "error": _ERRORS.get(profession),
        }
