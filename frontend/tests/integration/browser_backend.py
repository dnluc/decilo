"""Servidor exclusivo de pruebas: app/gateway reales, publicaciones sin IA.

Estos endpoints solo se agregan al importar este módulo desde Playwright;
no forman parte de decilo.app ni del servidor de producción.
"""
from decilo.app import app, registry, gateways, _gateway_for
from decilo.models import CaptionData, Session

for session_id, language in (("integration-en", "en"), ("integration-es", "es")):
    registry.register(Session(id=session_id, title=f"Integración {language}",
        source_language=language, translation_languages=["es"] if language == "en" else [],
        status="live"))


@app.post("/api/_test/{session_id}/publish")
async def publish(session_id: str, body: dict):
    gateway = _gateway_for(session_id)
    if body["type"] == "caption":
        event = gateway.stream.upsert_caption(CaptionData.model_validate(body["data"]))
    else:
        event = gateway.stream.record_status(gateway.stream.session.model_copy(update={"status": body["status"]}))
    gateway.publish_nowait(event)
    return {"seq": gateway.stream.seq}


@app.get("/api/_test/subscribers")
async def subscribers():
    return {key: len(value._subscribers) for key, value in gateways.items()}

# Playback test uses a real WAV/HTTP/WS/player; inference is explicitly fake.
import asyncio
import os
import decilo.app as application

os.environ["DECILO_DEMO_SESSIONS"] = "1"
os.environ["DECILO_DEMO_AUTOSTART"] = "0"


async def playback_worker(stream, gateway, path, **kwargs):
    await asyncio.sleep(.15)
    gateway.publish_nowait(stream.upsert_caption(CaptionData(
        segment_id="audio-1", segment_seq=1, kind="transcript", language="en",
        revision=1, source_revision=None, text="Playback integration test", status="final",
        start_ms=0, end_ms=5000,
    )))
    gateway.publish_nowait(stream.record_status(stream.session.model_copy(update={"status": "ended"})))


application.run_file_session = playback_worker

import decilo.capture as capture_module


async def fake_capture_chunk(stream, gateway, path, seq, start, end):
    gateway.publish_nowait(stream.upsert_caption(CaptionData(
        segment_id=f'captured-{seq}', segment_seq=seq, kind='transcript', language='en',
        revision=1, source_revision=None, text='Captured audio test', status='final',
        start_ms=start, end_ms=end,
    )))


capture_module.process_chunk = fake_capture_chunk
