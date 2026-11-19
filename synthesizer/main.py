from fastapi import FastAPI, HTTPException

from .schemas import ComposeRequest
from .composer import compose_map
from .validator import validate_map

app = FastAPI(
    title="ModeusAristo Synthesizer",
    version="1.0.0"
)


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

    errors = validate_map(result)
    result["validation_errors"] = errors

    if errors:
        raise HTTPException(
            status_code=422,
            detail=errors
        )

    return result