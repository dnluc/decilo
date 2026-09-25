"""Distribución de eventos por sesión vía WebSocket.

Snapshot atómico al conectar (sin punto de suspensión entre registrar al
suscriptor y capturar el estado, para que ningún evento publicado en el
medio se pierda ni se duplique) y cola acotada por cliente (64 mensajes /
2 MiB), cerrando con el código `4008` al espectador lento sin bloquear a
los demás — según `caption-stream`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from starlette.websockets import WebSocket, WebSocketDisconnect

from decilo.stream import SessionStream

MAX_QUEUE_MESSAGES = 64
MAX_QUEUE_BYTES = 2 * 1024 * 1024
SLOW_CLIENT_CLOSE_CODE = 4008


@dataclass
class _Subscriber:
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    bytes_pending: int = 0


class SessionGateway:
    """Une el estado retenido (`SessionStream`) con las conexiones WebSocket."""

    def __init__(self, stream: SessionStream):
        self.stream = stream
        self._subscribers: dict[int, _Subscriber] = {}
        self._next_sub_id = 0

    def _register_and_snapshot(self) -> tuple[int, _Subscriber, bytes]:
        # Sincrónico a propósito: no hay `await` entre registrar el
        # suscriptor y capturar el snapshot, así ningún `publish()`
        # concurrente puede colarse en el medio (asyncio es cooperativo,
        # solo cede control en un `await`).
        sub_id = self._next_sub_id
        self._next_sub_id += 1
        sub = _Subscriber()
        self._subscribers[sub_id] = sub
        payload = self.stream.snapshot().model_dump_json().encode("utf-8")
        return sub_id, sub, payload

    def publish_nowait(self, event) -> None:
        payload = event.model_dump_json().encode("utf-8")
        for sub in list(self._subscribers.values()):
            if (
                sub.queue.qsize() >= MAX_QUEUE_MESSAGES
                or sub.bytes_pending + len(payload) > MAX_QUEUE_BYTES
            ):
                sub.queue.put_nowait(None)  # señal de cierre por cliente lento
                continue
            sub.bytes_pending += len(payload)
            sub.queue.put_nowait(payload)

    async def serve(self, websocket: WebSocket) -> None:
        await websocket.accept()
        sub_id, sub, snapshot_payload = self._register_and_snapshot()
        try:
            await websocket.send_bytes(snapshot_payload)
            while True:
                payload = await sub.queue.get()
                if payload is None:
                    await websocket.close(code=SLOW_CLIENT_CLOSE_CODE)
                    return
                sub.bytes_pending -= len(payload)
                await websocket.send_bytes(payload)
        except WebSocketDisconnect:
            pass
        finally:
            self._subscribers.pop(sub_id, None)
