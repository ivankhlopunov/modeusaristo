
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
    level: str = "Junior"
    transcript: list[TranscriptMessage]
    scout: dict[str, Any] | None = None


class Evidence(BaseModel):
    evidence_message_ids: list[str] = Field(default_factory=list)
    evidence_source_ids: list[str] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)


class MapNode(BaseModel):
    id: str
    parent_id: str | None = None
    kind: str
    title: str
    operationality: str
    evidence: Evidence
    review_status: str = "needs_review"
    is_mock: bool = False
    review_notes: list[str] = Field(default_factory=list)
