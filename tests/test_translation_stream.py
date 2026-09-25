import asyncio
import json

import httpx
import pytest

from decilo import pipeline
from decilo.ollama_runtime import ollama_client, ollama_lifespan, _clients
from decilo.translate import translate_stream, translate
from test_pipeline import translation_stream


class BytesStream(httpx.AsyncByteStream):
    def __init__(self, parts):
        self.parts = parts
        self.closed = False

    async def __aiter__(self):
        for part in self.parts:
            if isinstance(part, asyncio.Event):
                await part.wait()
            else:
                yield part

    async def aclose(self):
        self.closed = True


def line(content='', done=False, **kwargs):
    return (json.dumps({'message': {'content': content}, 'done': done, **kwargs}) + '\n').encode()


def client_for(body):
    return httpx.AsyncClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, stream=body)))


@pytest.mark.asyncio
async def test_real_stream_handles_fragmented_utf8_and_ignores_thinking():
    raw = line('Código')
    body = BytesStream([b'{"message":{"thinking":"hidden"},"done":false}\n',
                        raw[:14], raw[14:], line(' listo', True, done_reason='stop',
                        load_duration=1_000_000_000, eval_count=4)])
    async with client_for(body) as client, ollama_lifespan(client):
        updates = [u async for u in translate_stream('Code ready')]
    assert [(u.text, u.final) for u in updates] == [('Código', False), ('Código listo', True)]
    assert updates[-1].metrics == {'load_seconds': 1, 'eval_count': 4}
    assert body.closed


@pytest.mark.parametrize('ending', [b'', line('', True, done_reason='length'),
    b'not json\n', b'{"error":"private server details"}\n', b'x' * 65537])
@pytest.mark.asyncio
async def test_incomplete_stream_never_finalizes(ending):
    body = BytesStream([line('Hola'), ending])
    updates = []
    async with client_for(body) as client, ollama_lifespan(client):
        with pytest.raises(RuntimeError) as exc:
            async for update in translate_stream('Hello'):
                updates.append(update)
    assert updates and not any(u.final for u in updates)
    assert 'private server details' not in str(exc.value)
    assert body.closed


@pytest.mark.asyncio
async def test_timeout_bounds_whole_stream_and_closes_response():
    body = BytesStream([line('Hola'), asyncio.Event()])
    async with client_for(body) as client, ollama_lifespan(client):
        with pytest.raises(RuntimeError, match='tiempo'):
            async for _ in translate_stream('Hello', timeout=.03):
                pass
    assert body.closed


@pytest.mark.asyncio
async def test_client_reused_and_closed_by_owner():
    assert asyncio.get_running_loop() not in _clients
    async with ollama_lifespan() as client:
        async with ollama_client() as first, ollama_client() as second:
            assert client is first is second
    assert client.is_closed
    assert asyncio.get_running_loop() not in _clients


@pytest.mark.asyncio
async def test_final_only_path_uses_same_client():
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={'message': {'content': 'Hola'}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        async with ollama_lifespan(client):
            assert await translate('Hello') == 'Hola'
            assert await translate('Hello again') == 'Hola'
        assert not client.is_closed  # injected client belongs to caller
    assert len(requests) == 2


@pytest.mark.asyncio
async def test_pipeline_provisional_visible_before_final_and_snapshot(monkeypatch):
    monkeypatch.setenv('DECILO_STREAM_TRANSLATION', '1')
    stream, gateway, originals = translation_stream()
    release = asyncio.Event()
    emitted = asyncio.Event()
    events = []
    original_publish = gateway.publish_nowait
    def publish(event):
        events.append(event)
        original_publish(event)
        if event.type == 'caption.upsert' and event.data.status == 'provisional':
            emitted.set()
    monkeypatch.setattr(gateway, 'publish_nowait', publish)
    body = BytesStream([line('Hola'), release, line(' mundo'), line('', True, done_reason='stop')])
    observations = []
    async with client_for(body) as client, ollama_lifespan(client):
        task = asyncio.create_task(pipeline.translate_caption(stream, gateway, originals[0], observations.append))
        await asyncio.wait_for(emitted.wait(), 1)
        assert not task.done()
        provisional = [c for c in stream.snapshot().data.captions if c.kind == 'translation']
        assert provisional[0].text == 'Hola' and provisional[0].status == 'provisional'
        release.set()
        await asyncio.wait_for(task, 1)
    captions = [e.data for e in events if e.type == 'caption.upsert']
    assert [c.status for c in captions] == ['provisional', 'final']
    assert [c.revision for c in captions] == [1, 2]
    assert captions[-1].text == 'Hola mundo'
    assert captions[-1].source_revision == originals[0].revision
    assert [o['stage'] for o in observations] == ['translation_first_content', 'ollama', 'translation']
    assert body.closed


@pytest.mark.asyncio
async def test_pipeline_error_leaves_partial_unconfirmed(monkeypatch):
    monkeypatch.setenv('DECILO_STREAM_TRANSLATION', '1')
    stream, gateway, originals = translation_stream()
    events = []
    monkeypatch.setattr(gateway, 'publish_nowait', events.append)
    body = BytesStream([line('Hola'), line('', True, done_reason='length')])
    async with client_for(body) as client, ollama_lifespan(client):
        await pipeline.translate_caption(stream, gateway, originals[0])
    assert [e.type for e in events] == ['caption.upsert', 'session.error']
    assert events[0].data.status == 'provisional'


@pytest.mark.asyncio
async def test_pipeline_cancellation_closes_stream_without_final(monkeypatch):
    monkeypatch.setenv('DECILO_STREAM_TRANSLATION', '1')
    stream, gateway, originals = translation_stream()
    emitted = asyncio.Event()
    events = []
    def publish(event):
        events.append(event)
        emitted.set()
    monkeypatch.setattr(gateway, 'publish_nowait', publish)
    body = BytesStream([line('Hola'), asyncio.Event()])
    async with client_for(body) as client, ollama_lifespan(client):
        task = asyncio.create_task(pipeline.translate_caption(stream, gateway, originals[0]))
        await asyncio.wait_for(emitted.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert body.closed
    assert len(events) == 1 and events[0].data.status == 'provisional'


@pytest.mark.asyncio
async def test_evicted_original_cannot_be_resurrected_by_stream(monkeypatch):
    import decilo.stream as stream_module
    from decilo.models import CaptionData
    monkeypatch.setenv('DECILO_STREAM_TRANSLATION', '1')
    monkeypatch.setattr(stream_module, 'MAX_SEGMENTS', 4)
    stream, gateway, originals = translation_stream()
    release = asyncio.Event()
    entered = asyncio.Event()
    events = []
    def publish(event):
        events.append(event)
        entered.set()
    monkeypatch.setattr(gateway, 'publish_nowait', publish)
    body = BytesStream([line('Hola'), release, line(' mundo', True, done_reason='stop')])
    async with client_for(body) as client, ollama_lifespan(client):
        task = asyncio.create_task(pipeline.translate_caption(stream, gateway, originals[0]))
        await asyncio.wait_for(entered.wait(), 1)
        stream.upsert_caption(CaptionData(segment_id='seg-5', segment_seq=5, kind='transcript',
            language='en', revision=1, text='Next', status='final', start_ms=400, end_ms=500))
        release.set()
        await asyncio.wait_for(task, 1)
    assert all(c.segment_id != 'seg-1' for c in stream.snapshot().data.captions)
    assert len(events) == 1 and events[0].data.status == 'provisional'
    assert body.closed


@pytest.mark.asyncio
async def test_blocked_session_does_not_block_another_stream(monkeypatch):
    monkeypatch.setenv('DECILO_STREAM_TRANSLATION', '1')
    one, gateway_one, originals_one = translation_stream()
    two, gateway_two, originals_two = translation_stream()
    two.record.session = two.session.model_copy(update={'id': 'other-session'})
    entered = asyncio.Event()
    slow_body = BytesStream([line('Uno'), asyncio.Event()])
    fast_body = BytesStream([line('Dos', True, done_reason='stop')])
    def handle(request):
        text = json.loads(request.content)['messages'][-1]['content']
        return httpx.Response(200, stream=slow_body if text == 'Hello 1' else fast_body)
    monkeypatch.setattr(gateway_one, 'publish_nowait', lambda _: entered.set())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client, ollama_lifespan(client):
        task = asyncio.create_task(pipeline.translate_caption(one, gateway_one, originals_one[0]))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            await asyncio.wait_for(pipeline.translate_caption(two, gateway_two, originals_two[1]), 1)
            assert not task.done()
            assert any(c.text == 'Dos' and c.status == 'final' for c in two.snapshot().data.captions)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert slow_body.closed and fast_body.closed
