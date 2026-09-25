"""Punto de entrada de la aplicacion Decilo (backend)."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse

from decilo.gateway import SessionGateway
from decilo.models import Session, SessionCatalog
from decilo.pipeline import run_file_session
from decilo.sessions import SessionNotFound, SessionRegistry
from decilo.stream import SessionStream

SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"

registry = SessionRegistry()
gateways: dict[str, SessionGateway] = {}
_background_tasks: set[asyncio.Task] = set()
audio_sources: dict[str, Path] = {}
file_tasks: dict[str, asyncio.Task] = {}


def _gateway_for(session_id: str) -> SessionGateway:
    gateway = gateways.get(session_id)
    if gateway is None:
        record = registry.get(session_id)
        gateway = SessionGateway(SessionStream(record))
        gateways[session_id] = gateway
    return gateway


def _start_background(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


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
            translation_languages=translations, target_locale="es-AR", status="starting",
        )
        registry.register(session)
        audio_sources[session_id] = audio_path
        if os.environ.get("DECILO_DEMO_AUTOSTART", "1") == "1":
            await start_session(session_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _start_sample_sessions()
    try:
        yield
    finally:
        tasks = list(_background_tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


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




def _audio_source(session_id: str) -> Path:
    try:
        registry.get(session_id)
    except SessionNotFound:
        raise HTTPException(404, "sesión no encontrada") from None
    path = audio_sources.get(session_id)
    if path is None or not path.is_file():
        raise HTTPException(404, "audio no disponible")
    return path


def _require_demo() -> None:
    if os.environ.get("DECILO_DEMO_SESSIONS") != "1":
        raise HTTPException(404, "modo de pruebas no habilitado")


@app.get("/api/v1/sessions/{session_id}/audio")
async def session_audio(session_id: str):
    return FileResponse(_audio_source(session_id), media_type="audio/wav")


@app.post("/api/v1/sessions/{session_id}/runs", response_model=Session, status_code=201)
async def create_run(session_id: str):
    _require_demo()
    path = _audio_source(session_id)
    if len(audio_sources) >= 20:
        raise HTTPException(429, "Límite de pruebas alcanzado; reiniciá el servidor local.")
    source = registry.get(session_id).session
    session = source.model_copy(update={"id": f"run-{uuid4().hex}", "status": "starting"})
    registry.register(session)
    audio_sources[session.id] = path
    return session


@app.post("/api/v1/sessions/{session_id}/start", response_model=Session)
async def start_session(session_id: str):
    _require_demo()
    path = _audio_source(session_id)
    record = registry.get(session_id)
    if session_id in file_tasks and not file_tasks[session_id].done():
        return record.session
    if record.session.status != "starting":
        raise HTTPException(409, "Creá una nueva prueba para volver a empezar.")
    if sum(not task.done() for task in file_tasks.values()) >= 2:
        raise HTTPException(429, "Ya hay dos pruebas procesando audio; esperá a que terminen.")
    gateway = _gateway_for(session_id)
    gateway.publish_nowait(gateway.stream.record_status(record.session.model_copy(update={"status": "live"})))

    async def run():
        try:
            await run_file_session(gateway.stream, gateway, path)
        except Exception:
            gateway.publish_nowait(gateway.stream.record_error(
                "inference_unavailable", "No se pudo procesar el audio de esta prueba.", retryable=False,
            ))
            gateway.publish_nowait(gateway.stream.record_status(
                gateway.stream.session.model_copy(update={"status": "error"}),
            ))
        finally:
            file_tasks.pop(session_id, None)

    file_tasks[session_id] = _start_background(run())
    return record.session




@app.websocket('/api/v1/capture')
async def capture_audio(websocket: WebSocket, language: str = 'en'):
    from decilo.capture import receive_capture

    if os.environ.get('DECILO_DEMO_SESSIONS') != '1' or language not in {'en', 'es'}:
        await websocket.close(code=4403)
        return
    if sum(not task.done() for task in file_tasks.values()) >= 2 or len(registry.list_sessions()) >= 20:
        await websocket.close(code=4429)
        return
    session = Session(id=f'capture-{uuid4().hex}', title='Audio de pestaña',
                      source_language=language, translation_languages=['es'] if language == 'en' else [],
                      target_locale='es-AR', status='live')
    registry.register(session)
    task = asyncio.current_task()
    file_tasks[session.id] = task
    try:
        await websocket.accept()
        await receive_capture(websocket, _gateway_for(session.id))
    finally:
        file_tasks.pop(session.id, None)


if __name__ == "__main__":
    main()
