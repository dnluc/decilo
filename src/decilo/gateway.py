"""Fan-out de JSON de texto con snapshot atómico y presupuesto por cliente."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from starlette.websockets import WebSocket, WebSocketDisconnect

from decilo.stream import MAX_MESSAGE_BYTES, SessionStream

MAX_QUEUE_MESSAGES = 64
MAX_QUEUE_BYTES = 2 * 1024 * 1024
SEND_TIMEOUT_SECONDS = 10.0
CLOSE_TIMEOUT_SECONDS = 1.0
SLOW_CLIENT_CLOSE_CODE = 4008


@dataclass
class _Subscriber:
    queue: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(maxsize=MAX_QUEUE_MESSAGES))
    bytes_pending: int = 0
    messages_pending: int = 0
    overflow: asyncio.Event = field(default_factory=asyncio.Event)


class SessionGateway:
    def __init__(self, stream: SessionStream):
        self.stream = stream
        self._subscribers: dict[int, _Subscriber] = {}
        self._next_sub_id = 0

    @staticmethod
    def _serialize(event) -> str:
        payload = event.model_dump_json()
        if len(payload.encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise ValueError("el evento supera 1 MiB")
        return payload

    def _enqueue(self, sub: _Subscriber, payload: str) -> bool:
        size = len(payload.encode("utf-8"))
        # Incluye el mensaje que está en send_text, además de los encolados.
        if sub.messages_pending >= MAX_QUEUE_MESSAGES or sub.bytes_pending + size > MAX_QUEUE_BYTES:
            sub.overflow.set()
            return False
        sub.queue.put_nowait(payload)
        sub.bytes_pending += size
        sub.messages_pending += 1
        return True

    def _register_and_snapshot(self) -> tuple[int, _Subscriber, str]:
        # Sin await entre snapshot y registro: una publicación no puede
        # intercalarse en este loop. El snapshot consume presupuesto también.
        payload = self._serialize(self.stream.snapshot())
        sub_id = self._next_sub_id
        self._next_sub_id += 1
        sub = _Subscriber()
        self._enqueue(sub, payload)
        self._subscribers[sub_id] = sub
        return sub_id, sub, payload

    def publish_nowait(self, event) -> None:
        if event is None:  # revisión duplicada, obsoleta o segmento evictado
            return
        payload = self._serialize(event)
        for sub_id, sub in list(self._subscribers.items()):
            if not self._enqueue(sub, payload):
                # Una sola señal fuera de la cola; no acumular sentinelas.
                self._subscribers.pop(sub_id, None)

    async def _send(self, websocket: WebSocket, sub: _Subscriber) -> None:
        while True:
            payload = await sub.queue.get()
            try:
                await asyncio.wait_for(websocket.send_text(payload), SEND_TIMEOUT_SECONDS)
            finally:
                sub.bytes_pending -= len(payload.encode("utf-8"))
                sub.messages_pending -= 1

    @staticmethod
    async def _receive_disconnect(websocket: WebSocket) -> None:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return

    async def serve(self, websocket: WebSocket) -> None:
        await websocket.accept()
        sub_id, sub, _ = self._register_and_snapshot()
        sender = asyncio.create_task(self._send(websocket, sub))
        receiver = asyncio.create_task(self._receive_disconnect(websocket))
        overflow = asyncio.create_task(sub.overflow.wait())
        tasks = (sender, receiver, overflow)
        close_code = None
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            if receiver in done:
                receiver.result()
            elif overflow in done:
                close_code = SLOW_CLIENT_CLOSE_CODE
            elif sender in done:
                try:
                    sender.result()
                except TimeoutError:
                    close_code = SLOW_CLIENT_CLOSE_CODE
        except (WebSocketDisconnect, OSError):
            pass
        finally:
            self._subscribers.pop(sub_id, None)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            while not sub.queue.empty():
                sub.queue.get_nowait()
            sub.bytes_pending = sub.messages_pending = 0
            if close_code is not None:
                try:
                    await asyncio.wait_for(websocket.close(code=close_code), CLOSE_TIMEOUT_SECONDS)
                except (TimeoutError, WebSocketDisconnect, OSError, RuntimeError):
                    pass  # el transporte puede haberse cerrado mientras se cancelaba el envío
