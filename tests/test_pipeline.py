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


def translation_stream():
    from decilo.models import CaptionData
    stream = SessionStream(Session(id='queue-test', title='Queue', source_language='en',
                                   translation_languages=['es'], status='live'))
    captions = [CaptionData(segment_id=f'seg-{i}', segment_seq=i, kind='transcript',
                            language='en', revision=1, text=f'Hello {i}', status='final',
                            start_ms=(i-1)*100, end_ms=i*100) for i in range(1, 5)]
    for caption in captions:
        stream.upsert_caption(caption)
    return stream, SessionGateway(stream), captions


@pytest.mark.asyncio
async def test_translation_queue_bounds_pending_work_and_drains(monkeypatch):
    stream, gateway, captions = translation_stream()
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = []

    async def slow_translate(text):
        calls.append(text)
        entered.set()
        await release.wait()
        return f'Traducido {text}'

    monkeypatch.setattr(pipeline, 'translate', slow_translate)
    observations = []
    async with pipeline.translation_queue(stream, gateway, observations.append, True) as submit:
        await submit(captions[0])
        await entered.wait()
        await submit(captions[1])
        await submit(captions[2])
        fourth = asyncio.create_task(submit(captions[3]))
        await asyncio.sleep(0)
        assert not fourth.done()  # one active, exactly two pending
        assert calls == ['Hello 1']
        release.set()
        await asyncio.wait_for(fourth, 2)
    assert calls == ['Hello 1', 'Hello 2', 'Hello 3', 'Hello 4']
    assert len(stream._captions) == 8  # drain includes all four translations
    assert len([s for s in observations if s['stage'] == 'translation']) == 4


@pytest.mark.asyncio
async def test_translation_queue_cancellation_cleans_worker(monkeypatch):
    stream, gateway, captions = translation_stream()
    entered = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow_translate(text):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(pipeline, 'translate', slow_translate)

    async def session():
        async with pipeline.translation_queue(stream, gateway, None, True) as submit:
            await submit(captions[0])
            await entered.wait()
            await submit(captions[1])
            await asyncio.Event().wait()

    task = asyncio.create_task(session())
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()
    assert len(stream._captions) == 4


@pytest.mark.asyncio
async def test_asr_advances_while_first_translation_is_blocked(monkeypatch, tmp_path):
    stream, gateway, _ = translation_stream()
    # Fresh session, two immediate chunks so only translation blocks progress.
    stream = SessionStream(stream.session)
    gateway = SessionGateway(stream)
    paths = [tmp_path / f'{i}.wav' for i in (1, 2)]
    for path in paths:
        path.write_bytes(b'audio')
    monkeypatch.setattr(pipeline, '_iter_chunks', lambda *args: iter([
        (paths[0], 0, 1), (paths[1], 1, 2),
    ]))
    loop = asyncio.get_running_loop()
    translated = asyncio.Event()
    second_asr = asyncio.Event()
    release = asyncio.Event()

    def transcribe(path, language):
        if path == paths[1]:
            loop.call_soon_threadsafe(second_asr.set)
        return path.stem

    async def translate(text):
        translated.set()
        await release.wait()
        return f'Texto {text}'

    monkeypatch.setattr(pipeline, 'transcribe', transcribe)
    monkeypatch.setattr(pipeline, 'translate', translate)
    task = asyncio.create_task(pipeline.run_file_session(
        stream, gateway, paths[0], overlap_translation=True,
    ))
    try:
        await asyncio.wait_for(translated.wait(), 2)
        await asyncio.wait_for(second_asr.wait(), 2)
        assert not task.done()
        assert stream.session.status == 'live'
    finally:
        release.set()
        await asyncio.wait_for(task, 2)
    assert stream.session.status == 'ended'
    assert len(stream._captions) == 4


@pytest.mark.asyncio
async def test_boundary_reason_preserved_on_original_and_translation(monkeypatch, tmp_path):
    from unittest.mock import AsyncMock
    chunk, stream, gateway = setup_worker(monkeypatch, tmp_path, 1000)
    stream.record.session = stream.session.model_copy(update={
        'source_language': 'en', 'translation_languages': ['es'],
    })
    monkeypatch.setattr(pipeline, 'transcribe', lambda *args: 'Hello')
    monkeypatch.setattr(pipeline, 'translate', AsyncMock(return_value='Hola'))
    await pipeline.process_chunk(stream, gateway, chunk, 1, 0, 1000, boundary_reason='deadline')
    assert len(stream._captions) == 2
    assert all(c.boundary_reason == 'deadline' for c in stream._captions.values())
