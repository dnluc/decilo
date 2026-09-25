"""Regresiones de ritmo y cancelación sin cargar modelos."""
import asyncio
from unittest.mock import Mock

import pytest

from decilo import pipeline
from decilo.gateway import SessionGateway
from decilo.models import Session
from decilo.stream import SessionStream


def setup_worker(monkeypatch, tmp_path, end_ms):
    chunk = tmp_path / "chunk.wav"
    chunk.write_bytes(b"fake audio")
    monkeypatch.setattr(pipeline, "_iter_chunks", lambda *args: iter([(chunk, 0, end_ms)]))
    stream = SessionStream(Session(id="test", title="Test", source_language="es",
                                   translation_languages=[], target_locale="es-AR", status="live"))
    return chunk, stream, SessionGateway(stream)


@pytest.mark.asyncio
async def test_waits_until_audio_available(monkeypatch, tmp_path):
    chunk, stream, gateway = setup_worker(monkeypatch, tmp_path, 30)
    calls = []
    loop = asyncio.get_running_loop()
    started = loop.time()
    monkeypatch.setattr(pipeline, "transcribe", lambda *args: calls.append(loop.time()) or "Hola")
    await pipeline.run_file_session(stream, gateway, chunk, started_at=started)
    assert calls[0] >= started + .03
    assert stream.session.status == "ended"
    assert not chunk.exists()


@pytest.mark.asyncio
async def test_cancel_during_wait_removes_chunk(monkeypatch, tmp_path):
    chunk, stream, gateway = setup_worker(monkeypatch, tmp_path, 60000)
    transcribe = Mock()
    monkeypatch.setattr(pipeline, "transcribe", transcribe)
    task = asyncio.create_task(pipeline.run_file_session(stream, gateway, chunk))
    await asyncio.sleep(.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    transcribe.assert_not_called()
    assert not chunk.exists()
