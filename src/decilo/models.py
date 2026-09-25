"""Modelos Pydantic del contrato de sesiones y subtitulos.

Implementa el envelope y los tipos de evento definidos en
`openspec/changes/contrato-sesiones-subtitulos/design.md` y sus specs
(`session-catalog`, `caption-stream`). Validacion estricta: un dato
invalido debe fallar con un error claro, no truncarse en silencio.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

Language = Literal["en", "es"]
SessionStatus = Literal["starting", "live", "degraded", "error", "ended"]
CaptionKind = Literal["transcript", "translation"]
CaptionStatus = Literal["provisional", "final"]
BoundaryReason = Literal["pause", "semantic", "deadline", "end_of_stream"]
GapReason = Literal["overload", "source_disconnect", "processing_error"]


class Session(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_language: Language
    translation_languages: list[Language] = Field(default_factory=list)
    target_locale: str | None = None
    status: SessionStatus

    def model_post_init(self, __context: object) -> None:
        if self.source_language in self.translation_languages:
            raise ValueError("translation_languages no debe incluir el idioma original")


class SessionCatalog(BaseModel):
    sessions: list[Session]


class CaptionData(BaseModel):
    segment_id: str = Field(min_length=1)
    segment_seq: int = Field(ge=1)
    kind: CaptionKind
    language: Language
    revision: int = Field(ge=1)
    source_revision: int | None = Field(default=None, ge=1)
    text: str = Field(min_length=1, max_length=8192)
    status: CaptionStatus
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    speaker_id: str | None = None
    boundary_reason: BoundaryReason | None = None

    def model_post_init(self, __context: object) -> None:
        if self.end_ms < self.start_ms:
            raise ValueError("end_ms no puede ser menor que start_ms")
        if self.kind == "translation" and self.source_revision is None:
            raise ValueError("una traduccion debe indicar source_revision")
        if self.kind == "transcript" and self.source_revision is not None:
            raise ValueError("un transcript no debe tener source_revision")


class DiscardedCaption(BaseModel):
    segment_id: str
    kind: CaptionKind
    language: Language


class GapData(BaseModel):
    gap_id: str = Field(min_length=1)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    reason: GapReason
    discard_captions: list[DiscardedCaption] = Field(default_factory=list)


class SnapshotData(BaseModel):
    session: Session
    captions: list[CaptionData] = Field(default_factory=list)
    gaps: list[GapData] = Field(default_factory=list)
    history_truncated: bool = False


class SessionStatusData(BaseModel):
    session: Session


class SessionErrorData(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool


class _EnvelopeBase(BaseModel):
    protocol_version: Literal[1] = 1
    session_id: str = Field(min_length=1)
    stream_id: str = Field(min_length=1)
    seq: int = Field(ge=0)
    emitted_at: datetime


class SessionSnapshotEvent(_EnvelopeBase):
    type: Literal["session.snapshot"] = "session.snapshot"
    data: SnapshotData


class CaptionUpsertEvent(_EnvelopeBase):
    type: Literal["caption.upsert"] = "caption.upsert"
    data: CaptionData


class SessionStatusEvent(_EnvelopeBase):
    type: Literal["session.status"] = "session.status"
    data: SessionStatusData


class SessionErrorEvent(_EnvelopeBase):
    type: Literal["session.error"] = "session.error"
    data: SessionErrorData


class SessionGapEvent(_EnvelopeBase):
    type: Literal["session.gap"] = "session.gap"
    data: GapData


Event = Annotated[
    Union[
        SessionSnapshotEvent,
        CaptionUpsertEvent,
        SessionStatusEvent,
        SessionErrorEvent,
        SessionGapEvent,
    ],
    Field(discriminator="type"),
]
