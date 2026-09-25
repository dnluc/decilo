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


@pytest.mark.asyncio
async def test_late_chunk_does_not_wait_again(monkeypatch, tmp_path):
    chunk, stream, gateway = setup_worker(monkeypatch, tmp_path, 1000)
    from unittest.mock import AsyncMock
    sleep = AsyncMock()
    monkeypatch.setattr(pipeline.asyncio, "sleep", sleep)
    monkeypatch.setattr(pipeline, "transcribe", lambda *args: "Hola")
    await pipeline.run_file_session(
        stream, gateway, chunk, started_at=asyncio.get_running_loop().time() - 2,
    )
    sleep.assert_not_awaited()
    assert stream.session.status == "ended"


@pytest.mark.asyncio
async def test_observations_cover_backlog_asr_translation_and_error(monkeypatch, tmp_path):
    from unittest.mock import AsyncMock
    chunk, stream, gateway = setup_worker(monkeypatch, tmp_path, 30)
    stream.record.session = stream.session.model_copy(update={
        'source_language': 'en', 'translation_languages': ['es'],
    })
    monkeypatch.setattr(pipeline, 'transcribe', lambda *args: 'Hello')
    monkeypatch.setattr(pipeline, 'translate', AsyncMock(return_value='Hola'))
    observations = []
    await pipeline.run_file_session(stream, gateway, chunk, observe=observations.append)
    assert [s['stage'] for s in observations] == ['backlog', 'asr', 'translation']
    assert all(s['seconds'] >= 0 and s['session_id'] == 'test' for s in observations)
    assert all(s['outcome'] == 'ok' for s in observations)
    # Model failures must still contribute timing, not silently bias success-only reports.
    chunk.write_bytes(b'audio')
    monkeypatch.setattr(pipeline, 'transcribe', Mock(side_effect=RuntimeError('offline')))
    observations.clear()
    await pipeline.process_chunk(stream, gateway, chunk, 2, 30, 60, observe=observations.append)
    assert observations[0]['stage'] == 'asr'
    assert observations[0]['outcome'] == 'error'


@pytest.mark.asyncio
async def test_file_overload_reports_omission_without_inference(monkeypatch, tmp_path):
    chunk, stream, gateway = setup_worker(monkeypatch, tmp_path, 1000)
    transcribe = Mock()
    monkeypatch.setattr(pipeline, 'transcribe', transcribe)
    observations = []
    await pipeline.run_file_session(
        stream, gateway, chunk, started_at=asyncio.get_running_loop().time() - 20,
        observe=observations.append,
    )
    transcribe.assert_not_called()
    assert stream.gaps[0].reason == 'overload'
    assert (stream.gaps[0].start_ms, stream.gaps[0].end_ms) == (0, 1000)
    assert observations[0]['stage'] == 'discard'
    assert observations[0]['audio_seconds'] == 1
    assert stream.session.status == 'ended'
    assert not chunk.exists()
