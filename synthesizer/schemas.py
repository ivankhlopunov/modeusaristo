from typing import Any
from pydantic import BaseModel, Field


class TranscriptMessage(BaseModel):
    id: str
    speaker: str
    text: str
    version: int = 1
    is_mock: bool = False


class ComposeRequest(BaseModel):
    profession: str = Field(min_length=1, max_length=150)
    scout: dict[str, Any]
    transcript: list[TranscriptMessage]


class Evidence(BaseModel):
    evidence_message_ids: list[str] = []
    evidence_source_ids: list[str] = []
    quotes: list[str] = []


class MapNode(BaseModel):
    id: str
    parent_id: str | None = None
    kind: str
    title: str
    operationality: str
    evidence: Evidence
    review_status: str = "needs_review"
    is_mock: bool = False
    review_notes: list[str] = []