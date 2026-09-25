"""Estado autoritativo por sesión, revisiones y snapshots acotados."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from decilo.models import (
    CaptionData, CaptionUpsertEvent, GapData, Session, SessionErrorData,
    SessionErrorEvent, SessionGapEvent, SessionStatusData, SessionStatusEvent,
    SessionSnapshotEvent, SnapshotData,
)
from decilo.sessions import SessionRecord

MAX_SEGMENTS = 100
MAX_GAPS = 100
MAX_MESSAGE_BYTES = 1024 * 1024


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionStream:
    def __init__(self, session: Session | SessionRecord):
        self.record = session if isinstance(session, SessionRecord) else SessionRecord(session)
        self.stream_id = uuid.uuid4().hex[:12]
        self.seq = 0
        self._captions: dict[tuple[str, str, str], CaptionData] = {}
        self._segment_order: list[str] = []
        self._segments: dict[str, tuple[int, int]] = {}
        self._revisions: dict[tuple[str, str, str], int] = {}
        self._retired: set[tuple[str, str, str]] = set()
        self._highest_segment_seq = 0
        self.gaps: list[GapData] = []
        self.history_truncated = False

    @property
    def session(self) -> Session:
        return self.record.session

    def _envelope(self) -> dict:
        return dict(session_id=self.session.id, stream_id=self.stream_id,
                    seq=self.seq + 1, emitted_at=_now())

    def _snapshot(self) -> SessionSnapshotEvent:
        return SessionSnapshotEvent(
            **{**self._envelope(), "seq": self.seq},
            data=SnapshotData(session=self.session, captions=list(self._captions.values()),
                              gaps=list(self.gaps), history_truncated=self.history_truncated),
        )

    def _evict_oldest_segment(self) -> None:
        segment_id = self._segment_order.pop(0)
        del self._segments[segment_id]
        for mapping in (self._captions, self._revisions):
            for key in [k for k in mapping if k[0] == segment_id]:
                del mapping[key]
        self._retired = {key for key in self._retired if key[0] != segment_id}
        self.history_truncated = True

    def snapshot(self) -> SessionSnapshotEvent:
        while True:
            result = self._snapshot()
            if len(result.model_dump_json().encode("utf-8")) <= MAX_MESSAGE_BYTES:
                return result
            if self._segment_order:
                self._evict_oldest_segment()
            elif self.gaps:
                self.gaps.pop(0)
                self.history_truncated = True
            else:
                raise ValueError("los metadatos de sesión exceden el límite del snapshot")

    def upsert_caption(self, caption: CaptionData) -> CaptionUpsertEvent | None:
        key = (caption.segment_id, caption.kind, caption.language)
        meta = self._segments.get(caption.segment_id)
        if meta is None and caption.segment_seq <= self._highest_segment_seq:
            return None  # no resucitar segmentos evictados ni desordenar audio
        if meta is not None and meta != (caption.segment_seq, caption.start_ms):
            raise ValueError("segment_seq y start_ms son inmutables por segmento")
        if key in self._retired:
            return None
        existing = self._captions.get(key)
        if existing is not None and existing.status == "final":
            if caption.revision <= existing.revision:
                if caption.revision == existing.revision and caption != existing:
                    raise ValueError("una revisión confirmada no puede cambiar su contenido")
                return None
            raise ValueError("no se puede modificar un subtítulo ya confirmado")
        if caption.revision <= self._revisions.get(key, 0):
            return None
        if existing is not None and caption.end_ms < existing.end_ms:
            raise ValueError("end_ms no puede retroceder")
        if caption.kind == "transcript":
            if caption.language != self.session.source_language:
                raise ValueError("idioma original incorrecto")
        else:
            if caption.language not in self.session.translation_languages:
                raise ValueError("idioma de traducción no habilitado")
            original = self._captions.get((caption.segment_id, "transcript", self.session.source_language))
            if original is None:
                if (caption.segment_id, "transcript", self.session.source_language) in self._retired:
                    return None
                raise ValueError("la traducción requiere un original vigente")
            if caption.source_revision < original.revision:
                return None
            if caption.source_revision != original.revision:
                raise ValueError("la traducción refiere a una revisión desconocida")
            if (caption.start_ms, caption.end_ms) != (original.start_ms, original.end_ms):
                raise ValueError("la traducción debe conservar los tiempos del original")
            if caption.status == "final" and original.status != "final":
                raise ValueError("una traducción final requiere un original final")
        # Construir/validar antes de cambiar estado o consumir secuencia.
        event = CaptionUpsertEvent(**self._envelope(), data=caption)
        if meta is None:
            self._segment_order.append(caption.segment_id)
            self._segments[caption.segment_id] = (caption.segment_seq, caption.start_ms)
            self._highest_segment_seq = caption.segment_seq
        self._captions[key] = caption
        self._revisions[key] = caption.revision
        if caption.kind == "transcript":
            for k, value in list(self._captions.items()):
                if k[0] == caption.segment_id and k[1] == "translation" and value.source_revision != caption.revision:
                    del self._captions[k]
        self.seq = event.seq
        while len(self._segment_order) > MAX_SEGMENTS:
            self._evict_oldest_segment()
        return event

    def record_status(self, session: Session) -> SessionStatusEvent:
        if session.model_dump(exclude={"status"}) != self.session.model_dump(exclude={"status"}):
            raise ValueError("un cambio de estado no puede reemplazar la sesión")
        event = SessionStatusEvent(**self._envelope(), data=SessionStatusData(session=session))
        self.record.transition_to(session.status)
        self.seq = event.seq
        return event

    def record_error(self, code: str, message: str, retryable: bool) -> SessionErrorEvent:
        event = SessionErrorEvent(**self._envelope(), data=SessionErrorData(code=code, message=message, retryable=retryable))
        self.seq = event.seq
        return event

    def record_gap(self, gap: GapData) -> SessionGapEvent:
        event = SessionGapEvent(**self._envelope(), data=gap)
        for c in gap.discard_captions:
            key = (c.segment_id, c.kind, c.language)
            existing = self._captions.get(key)
            if existing is not None and existing.status != "final":
                del self._captions[key]
                self._retired.add(key)
                if c.kind == "transcript":
                    for k in [k for k in self._captions if k[0] == c.segment_id and k[1] == "translation"]:
                        del self._captions[k]
                        self._retired.add(k)
        self.gaps.append(gap)
        if len(self.gaps) > MAX_GAPS:
            self.gaps = self.gaps[-MAX_GAPS:]
            self.history_truncated = True
        self.seq = event.seq
        return event
