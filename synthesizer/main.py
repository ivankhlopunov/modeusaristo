
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

from .schemas import ComposeRequest
from .composer import compose_map
from .validator import validate_map
from .versioning import invalidate_stale_evidence

app = FastAPI(
    title="ModeusAristo Synthesizer",
    version="1.0.0"
)

MAP_PATH = Path(__file__).parent / "data" / "map.json"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "synthesizer"
    }


@app.post("/compose")
def compose(request: ComposeRequest):
    transcript = [
        message.model_dump()
        for message in request.transcript
    ]

    result = compose_map(
        request.profession,
        request.scout,
        transcript
    )
    result = invalidate_stale_evidence(result, transcript)
    
    errors = validate_map(result)
    result["validation_errors"] = errors

    if errors:
        raise HTTPException(status_code=422, detail=errors)

    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    MAP_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return result


@app.get("/export")
def export_map():
    if not MAP_PATH.exists() or MAP_PATH.stat().st_size == 0:
        raise HTTPException(
            status_code=404,
            detail="Карта ещё не создана"
        )

    return json.loads(MAP_PATH.read_text(encoding="utf-8"))
