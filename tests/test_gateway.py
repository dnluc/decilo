"""Gateway: texto, snapshot ordenado, presión de salida y desconexión."""
import asyncio
import json

import pytest

from decilo.gateway import MAX_QUEUE_MESSAGES, SLOW_CLIENT_CLOSE_CODE, SessionGateway
from decilo.models import CaptionData, Session
from decilo.stream import SessionStream


def make_session(**overrides):
    return Session(**(dict(id="s1", title="Charla", source_language="en",
                          translation_languages=["es"], status="live") | overrides))


class FakeWebSocket:
    def __init__(self, blocked=False):
        self.sent = []
        self.closed_code = None
        self.accepted = False
        self.started = asyncio.Event()
        self.ready = asyncio.Event()
        if not blocked:
            self.ready.set()
        self.received = asyncio.Queue()
        self.changed = asyncio.Condition()

    async def accept(self):
        self.accepted = True

    async def send_text(self, data):
        assert isinstance(data, str)
        self.started.set()
        await self.ready.wait()
        async with self.changed:
            self.sent.append(data)
            self.changed.notify_all()

    async def receive(self):
        return await self.received.get()

    async def close(self, code=1000):
        self.closed_code = code

    async def wait_count(self, count):
        async with self.changed:
            await asyncio.wait_for(self.changed.wait_for(lambda: len(self.sent) >= count), 2)

    def disconnect(self):
        self.received.put_nowait({"type": "websocket.disconnect", "code": 1000})


def event(stream, i=1):
    return stream.upsert_caption(CaptionData(
        segment_id=f"seg-{i}", segment_seq=i, kind="transcript", language="en",
        revision=1, text=f"texto {i}", status="final", start_ms=0, end_ms=100,
    ))


@pytest.mark.asyncio
async def test_snapshot_then_concurrent_publication_are_text_and_have_no_seq_gap():
    stream = SessionStream(make_session())
    gateway = SessionGateway(stream)
    ws = FakeWebSocket(blocked=True)
    task = asyncio.create_task(gateway.serve(ws))
    await asyncio.wait_for(ws.started.wait(), 1)
    gateway.publish_nowait(event(stream))
    ws.ready.set()
    await ws.wait_count(2)
    assert [json.loads(data)["seq"] for data in ws.sent] == [0, 1]
    assert json.loads(ws.sent[0])["type"] == "session.snapshot"
    ws.disconnect()
    await asyncio.wait_for(task, 1)
    assert not gateway._subscribers


@pytest.mark.asyncio
async def test_blocked_slow_client_closes_while_fast_client_continues():
    stream = SessionStream(make_session())
    gateway = SessionGateway(stream)
    slow, fast = FakeWebSocket(blocked=True), FakeWebSocket()
    tasks = [asyncio.create_task(gateway.serve(ws)) for ws in (slow, fast)]
    await asyncio.wait_for(slow.started.wait(), 1)
    await fast.wait_count(1)
    slow_sub = gateway._subscribers[0]
    for i in range(1, 201):
        gateway.publish_nowait(event(stream, i))
        assert slow_sub.queue.qsize() <= MAX_QUEUE_MESSAGES
        assert slow_sub.messages_pending <= MAX_QUEUE_MESSAGES
        await fast.wait_count(i + 1)
    await asyncio.wait_for(tasks[0], 1)
    assert slow.closed_code == SLOW_CLIENT_CLOSE_CODE
    assert slow_sub.bytes_pending == slow_sub.messages_pending == 0
    assert slow_sub.queue.empty()
    assert fast.closed_code is None
    fast.disconnect()
    await asyncio.wait_for(tasks[1], 1)
    assert not gateway._subscribers


@pytest.mark.asyncio
async def test_send_timeout_closes_even_without_new_publications(monkeypatch):
    monkeypatch.setattr("decilo.gateway.SEND_TIMEOUT_SECONDS", 0.02)
    gateway = SessionGateway(SessionStream(make_session()))
    ws = FakeWebSocket(blocked=True)
    await asyncio.wait_for(gateway.serve(ws), 1)
    assert ws.closed_code == SLOW_CLIENT_CLOSE_CODE
    assert not gateway._subscribers


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["live", "ended"])
async def test_disconnect_without_new_events_removes_subscriber(status):
    gateway = SessionGateway(SessionStream(make_session(status=status)))
    ws = FakeWebSocket()
    task = asyncio.create_task(gateway.serve(ws))
    await ws.wait_count(1)
    assert len(gateway._subscribers) == 1
    ws.disconnect()
    await asyncio.wait_for(task, 1)
    assert not gateway._subscribers


def test_snapshot_counts_toward_queue_budget_and_overflow_is_signaled_once(monkeypatch):
    stream = SessionStream(make_session())
    gateway = SessionGateway(stream)
    sub_id, sub, payload = gateway._register_and_snapshot()
    assert sub.messages_pending == 1
    assert sub.bytes_pending == len(payload.encode("utf-8"))
    monkeypatch.setattr("decilo.gateway.MAX_QUEUE_BYTES", sub.bytes_pending + 1)
    for i in range(1, 1001):
        gateway.publish_nowait(event(stream, i))
    assert sub.overflow.is_set()
    assert sub_id not in gateway._subscribers
    assert sub.queue.qsize() == 1
    assert sub.messages_pending == 1


@pytest.mark.asyncio
async def test_cancellation_cleans_subscriber_and_child_tasks():
    gateway = SessionGateway(SessionStream(make_session()))
    ws = FakeWebSocket(blocked=True)
    task = asyncio.create_task(gateway.serve(ws))
    await asyncio.wait_for(ws.started.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not gateway._subscribers
