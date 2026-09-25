"""Registro de sesiones en memoria y transiciones de estado.

Implementa `specs/session-catalog` de `contrato-sesiones-subtitulos`: sin
persistencia (memoria local, ver `arquitectura-base`), transiciones de
estado acotadas según lo definido en el contrato.
"""

from __future__ import annotations

from dataclasses import dataclass

from decilo.models import Session, SessionStatus

ALLOWED_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    "starting": frozenset({"live", "degraded", "error", "ended"}),
    "live": frozenset({"live", "degraded", "error", "ended"}),
    "degraded": frozenset({"live", "degraded", "error", "ended"}),
    "error": frozenset({"starting", "ended"}),
    "ended": frozenset(),
}


class InvalidTransition(ValueError):
    """Se intentó una transición de estado no permitida por el contrato."""


@dataclass
class SessionRecord:
    session: Session

    def transition_to(self, new_status: SessionStatus) -> Session:
        current = self.session.status
        if new_status not in ALLOWED_TRANSITIONS[current]:
            raise InvalidTransition(f"transición no permitida: {current} -> {new_status}")
        self.session = self.session.model_copy(update={"status": new_status})
        return self.session


class SessionNotFound(KeyError):
    pass


class SessionRegistry:
    """Registro en memoria. No persiste entre reinicios del proceso."""

    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}

    def register(self, session: Session) -> SessionRecord:
        if session.id in self._records:
            raise ValueError(f"la sesión {session.id!r} ya está registrada")
        record = SessionRecord(session=session)
        self._records[session.id] = record
        return record

    def get(self, session_id: str) -> SessionRecord:
        try:
            return self._records[session_id]
        except KeyError:
            raise SessionNotFound(session_id) from None

    def list_sessions(self) -> list[Session]:
        return [r.session for r in self._records.values()]
