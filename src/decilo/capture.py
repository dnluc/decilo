"""Bounded PCM ingress; no video or arbitrary file paths accepted."""
import asyncio
import struct
import tempfile
import wave
from pathlib import Path

from starlette.websockets import WebSocketDisconnect

from decilo.models import GapData
from decilo.pipeline import process_chunk, translation_queue

RATE = 16000
MAX_SAMPLES = RATE * 5


def decode_packet(packet: bytes, previous_end: int):
    if not 6 <= len(packet) <= 4 + MAX_SAMPLES * 2 or (len(packet) - 4) % 2:
        raise ValueError("Tamaño PCM inválido")
    start = struct.unpack_from('<I', packet)[0]
    end = start + (len(packet) - 4) // 2
    if start < previous_end or end > RATE * 3600:
        raise ValueError("Orden o duración de audio inválidos")
    return start, end, packet[4:]


class CaptureBuffer:
    def __init__(self, gateway, submit_translation=None):
        self.gateway = gateway
        self.submit_translation = submit_translation
        self.queue = asyncio.Queue(maxsize=2)
        self.last_end = 0
        self.seq = 0
        self.gaps = 0

    def gap(self, start, end, reason):
        self.gaps += 1
        self.gateway.publish_nowait(self.gateway.stream.record_gap(GapData(
            gap_id=f"capture-gap-{self.gaps}", start_ms=start * 1000 // RATE,
            end_ms=end * 1000 // RATE, reason=reason, discard_captions=[],
        )))

    def add(self, packet):
        start, end, pcm = decode_packet(packet, self.last_end)
        if start > self.last_end:
            self.gap(self.last_end, start, "source_disconnect")
        self.last_end = end
        self.seq += 1
        if self.queue.full():
            _, old_start, old_end, _ = self.queue.get_nowait()
            self.queue.task_done()
            self.gap(old_start, old_end, "overload")
        self.queue.put_nowait((self.seq, start, end, pcm))

    async def consume(self):
        while True:
            seq, start, end, pcm = await self.queue.get()
            path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as file:
                    path = Path(file.name)
                with wave.open(str(path), 'wb') as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(RATE)
                    wav.writeframes(pcm)
                options = {"submit_translation": self.submit_translation} if self.submit_translation else {}
                await process_chunk(self.gateway.stream, self.gateway, path,
                                    seq, start * 1000 // RATE, end * 1000 // RATE, **options)
            except Exception:
                self.gap(start, end, "processing_error")
            finally:
                if path:
                    path.unlink(missing_ok=True)
                self.queue.task_done()


async def _receive_audio(websocket, gateway, submit, deadline):
    buffer = CaptureBuffer(gateway, submit)
    worker = asyncio.create_task(buffer.consume())
    try:
        await websocket.send_json({"type": "ready", "session": gateway.stream.session.model_dump()})
        while True:
            message = await asyncio.wait_for(websocket.receive(), timeout=15)
            if message['type'] == 'websocket.disconnect':
                buffer.gap(buffer.last_end, buffer.last_end, "source_disconnect")
                break
            if message.get('text') == 'stop':
                break
            if message.get('bytes') is None:
                raise ValueError('Se esperaba PCM binario o stop')
            buffer.add(message['bytes'])
    except (ValueError, asyncio.TimeoutError) as error:
        gateway.publish_nowait(gateway.stream.record_error(
            'inference_unavailable', str(error) or 'Captura sin audio durante 15 segundos', retryable=False,
        ))
        buffer.gap(buffer.last_end, buffer.last_end, "source_disconnect")
    except WebSocketDisconnect:
        pass
    finally:
        # One shared deadline includes both ASR and translation queue draining.
        deadline.reschedule(asyncio.get_running_loop().time() + 90)
        try:
            await buffer.queue.join()
        except asyncio.CancelledError:
            while not buffer.queue.empty():
                _, start, end, _ = buffer.queue.get_nowait()
                buffer.queue.task_done()
                buffer.gap(start, end, 'processing_error')
            raise
        finally:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)


async def receive_capture(websocket, gateway, *, overlap_translation=False):
    try:
        async with asyncio.timeout(None) as deadline:
            async with translation_queue(gateway.stream, gateway, None, overlap_translation) as submit:
                await _receive_audio(websocket, gateway, submit, deadline)
    except TimeoutError:
        gateway.publish_nowait(gateway.stream.record_error(
            'inference_unavailable', 'Se agotó el tiempo para terminar el audio pendiente.', retryable=False,
        ))
    finally:
        session = gateway.stream.session.model_copy(update={"status": "ended"})
        gateway.publish_nowait(gateway.stream.record_status(session))
        try:
            await websocket.close()
        except (RuntimeError, WebSocketDisconnect):
            pass
