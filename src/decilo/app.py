"""Punto de entrada de la aplicacion Decilo (backend)."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket

from decilo.gateway import SessionGateway
from decilo.models import Session, SessionCatalog
from decilo.pipeline import run_file_session
from decilo.sessions import SessionNotFound, SessionRegistry
from decilo.stream import SessionStream

SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"

registry = SessionRegistry()
gateways: dict[str, SessionGateway] = {}
_background_tasks: set[asyncio.Task] = set()


def _gateway_for(session_id: str) -> SessionGateway:
    gateway = gateways.get(session_id)
    if gateway is None:
        record = registry.get(session_id)
        gateway = SessionGateway(SessionStream(record))
        gateways[session_id] = gateway
    return gateway


def _start_background(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _start_sample_sessions() -> None:
    """Arranca las dos sesiones de prueba definidas en samples/ (ver README).

    Requiere DECILO_DEMO_SESSIONS=1: correr modelos reales (Whisper/Ollama)
    en cada import de `app` rompería los tests (deben poder correr sin
    modelos, ver docs/ci.md) y el arranque de TestClient en cualquier test.
    """
    if os.environ.get("DECILO_DEMO_SESSIONS") != "1":
        return
    samples = [
        ("konex-sala-1-charla-1", "Building reliable systems", "en", ["es"], SAMPLES_DIR / "en_tech_talk.wav"),
        ("konex-sala-2-charla-1", "Arquitectura de microservicios", "es", [], SAMPLES_DIR / "es_tech_talk.wav"),
    ]
    for session_id, title, lang, translations, audio_path in samples:
        if not audio_path.exists():
            continue
        session = Session(
            id=session_id, title=title, source_language=lang,
            translation_languages=translations, target_locale="es-AR", status="live",
        )
        registry.register(session)
        gateway = _gateway_for(session_id)
        _start_background(run_file_session(gateway.stream, gateway, audio_path))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _start_sample_sessions()
    yield


app = FastAPI(title="Decilo", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/sessions", response_model=SessionCatalog)
async def list_sessions() -> SessionCatalog:
    return SessionCatalog(sessions=registry.list_sessions())


@app.get("/api/v1/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str) -> Session:
    try:
        return registry.get(session_id).session
    except SessionNotFound:
        raise HTTPException(status_code=404, detail="sesión no encontrada") from None


@app.websocket("/api/v1/sessions/{session_id}/events")
async def session_events(websocket: WebSocket, session_id: str) -> None:
    try:
        registry.get(session_id)
    except SessionNotFound:
        await websocket.close(code=4404)
        return
    gateway = _gateway_for(session_id)
    await gateway.serve(websocket)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
