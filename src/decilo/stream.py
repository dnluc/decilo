"""Estado retenido y generación de eventos de una sesión (lado servidor).

Implementa la retención y el envelope de `caption-stream`: `seq` por
sesión, snapshot autoritativo, invalidación de traducciones obsoletas y
límites de retención (100 segmentos, 100 gaps).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from decilo.models import (
    CaptionData,
    CaptionUpsertEvent,
    GapData,
    Session,
    SessionErrorData,
    SessionErrorEvent,
    SessionGapEvent,
    SessionStatusData,
    SessionStatusEvent,
    SessionSnapshotEvent,
    SnapshotData,
)

MAX_SEGMENTS = 100
MAX_GAPS = 100


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionStream:
    """Estado retenido + generador de eventos ordenados para una sesión."""

    def __init__(self, session: Session):
        self.session = session
        self.stream_id = uuid.uuid4().hex[:12]
        self.seq = 0
        self._captions: dict[tuple[str, str, str], CaptionData] = {}
        self._segment_order: list[str] = []
        self.gaps: list[GapData] = []
        self.history_truncated = False

    def _next_seq(self) -> int:
        self.seq += 1
        return self.seq

    def snapshot(self) -> SessionSnapshotEvent:
        return SessionSnapshotEvent(
            session_id=self.session.id,
            stream_id=self.stream_id,
            seq=self.seq,
            emitted_at=_now(),
            data=SnapshotData(
                session=self.session,
                captions=list(self._captions.values()),
                gaps=list(self.gaps),
                history_truncated=self.history_truncated,
            ),
        )

    def _retain(self) -> None:
        if len(self._segment_order) <= MAX_SEGMENTS:
            return
        overflow = len(self._segment_order) - MAX_SEGMENTS
        evicted, self._segment_order = (
            self._segment_order[:overflow],
            self._segment_order[overflow:],
        )
        for seg_id in evicted:
            for k in [k for k in self._captions if k[0] == seg_id]:
                del self._captions[k]
        self.history_truncated = True

    def upsert_caption(self, caption: CaptionData) -> CaptionUpsertEvent:
        key = (caption.segment_id, caption.kind, caption.language)
        existing = self._captions.get(key)
        if existing is not None and existing.status == "final":
            raise ValueError("no se puede modificar un subtítulo ya confirmado")
        if caption.segment_id not in self._segment_order:
            self._segment_order.append(caption.segment_id)
        self._captions[key] = caption
        if caption.kind == "transcript":
            # Un original nuevo invalida traducciones que ya no refieren a
            # su revisión vigente (la misma regla que aplica el cliente).
            for k in list(self._captions):
                seg_id, kind, _lang = k
                if seg_id != caption.segment_id or kind != "translation":
                    continue
                cap = self._captions[k]
                if cap.status != "final" and cap.source_revision != caption.revision:
                    del self._captions[k]
        self._retain()
        return CaptionUpsertEvent(
            session_id=self.session.id,
            stream_id=self.stream_id,
            seq=self._next_seq(),
            emitted_at=_now(),
            data=caption,
        )

    def record_status(self, session: Session) -> SessionStatusEvent:
        self.session = session
        return SessionStatusEvent(
            session_id=self.session.id,
            stream_id=self.stream_id,
            seq=self._next_seq(),
            emitted_at=_now(),
            data=SessionStatusData(session=session),
        )

    def record_error(self, code: str, message: str, retryable: bool) -> SessionErrorEvent:
        return SessionErrorEvent(
            session_id=self.session.id,
            stream_id=self.stream_id,
            seq=self._next_seq(),
            emitted_at=_now(),
            data=SessionErrorData(code=code, message=message, retryable=retryable),
        )

    def record_gap(self, gap: GapData) -> SessionGapEvent:
        for c in gap.discard_captions:
            key = (c.segment_id, c.kind, c.language)
            existing = self._captions.get(key)
            if existing is not None and existing.status != "final":
                del self._captions[key]
        self.gaps.append(gap)
        if len(self.gaps) > MAX_GAPS:
            self.gaps = self.gaps[-MAX_GAPS:]
            self.history_truncated = True
        return SessionGapEvent(
            session_id=self.session.id,
            stream_id=self.stream_id,
            seq=self._next_seq(),
            emitted_at=_now(),
            data=gap,
        )
