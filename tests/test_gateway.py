"""Tests del gateway WebSocket (sin servidor real ni modelos de IA)."""

import asyncio
import json

import pytest

from decilo.gateway import MAX_QUEUE_MESSAGES, SLOW_CLIENT_CLOSE_CODE, SessionGateway
from decilo.models import CaptionData, Session
from decilo.stream import SessionStream


def make_session(**overrides) -> Session:
    defaults = dict(id="s1", title="Charla", source_language="en", translation_languages=["es"], status="live")
    defaults.update(overrides)
    return Session(**defaults)


class FakeWebSocket:
    def __init__(self):
        self.sent: list[bytes] = []
        self.closed_code: int | None = None
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_bytes(self, data: bytes):
        self.sent.append(data)

    async def close(self, code: int = 1000):
        self.closed_code = code


@pytest.mark.asyncio
async def test_serve_sends_snapshot_first():
    stream = SessionStream(make_session())
    stream.upsert_caption(
        CaptionData(segment_id="seg-1", segment_seq=1, kind="transcript", language="en",
                    revision=1, text="hola", status="final", start_ms=0, end_ms=100)
    )
    gateway = SessionGateway(stream)
    ws = FakeWebSocket()

    serve_task = asyncio.create_task(gateway.serve(ws))
    await asyncio.sleep(0)  # deja correr hasta el primer await (recibir snapshot)

    assert ws.accepted
    assert len(ws.sent) == 1
    snapshot = json.loads(ws.sent[0])
    assert snapshot["type"] == "session.snapshot"
    assert len(snapshot["data"]["captions"]) == 1

    serve_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await serve_task


@pytest.mark.asyncio
async def test_publish_reaches_connected_subscriber():
    stream = SessionStream(make_session())
    gateway = SessionGateway(stream)
    ws = FakeWebSocket()
    serve_task = asyncio.create_task(gateway.serve(ws))
    await asyncio.sleep(0)

    event = stream.upsert_caption(
        CaptionData(segment_id="seg-1", segment_seq=1, kind="transcript", language="en",
                    revision=1, text="hola", status="final", start_ms=0, end_ms=100)
    )
    gateway.publish_nowait(event)
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert len(ws.sent) == 2  # snapshot + el evento nuevo
    assert json.loads(ws.sent[1])["type"] == "caption.upsert"

    serve_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await serve_task


@pytest.mark.asyncio
async def test_slow_subscriber_gets_close_signal_without_affecting_others():
    """publish_nowait() aplica la cola acotada por suscriptor de forma
    independiente: uno que no se drena recibe la señal de cierre (None,
    que serve() traduce a 4008) sin que eso afecte a otro suscriptor cuya
    cola sí se va vaciando."""
    stream = SessionStream(make_session())
    gateway = SessionGateway(stream)

    slow_id, slow_sub, _ = gateway._register_and_snapshot()
    fast_id, fast_sub, _ = gateway._register_and_snapshot()

    def make_event(i: int):
        return stream.upsert_caption(
            CaptionData(segment_id=f"seg-{i}", segment_seq=i, kind="transcript", language="en",
                        revision=1, text=f"texto {i}", status="final", start_ms=0, end_ms=100)
        )

    for i in range(1, MAX_QUEUE_MESSAGES + 5):
        gateway.publish_nowait(make_event(i))
        # El "rápido" se drena en cada vuelta; el "lento" nunca se lee.
        while not fast_sub.queue.empty():
            payload = fast_sub.queue.get_nowait()
            if payload is not None:
                fast_sub.bytes_pending -= len(payload)

    assert fast_sub.queue.empty()  # nunca se le encoló una señal de cierre
    # El lento superó el límite: en algún punto se encoló None (cierre).
    drained = []
    while not slow_sub.queue.empty():
        drained.append(slow_sub.queue.get_nowait())
    assert None in drained
