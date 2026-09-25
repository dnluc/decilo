"""Bounded PCM ingress; no video or arbitrary file paths accepted."""
import asyncio
import struct
import tempfile
import wave
from pathlib import Path

from starlette.websockets import WebSocketDisconnect

from decilo.models import GapData
from decilo.pipeline import process_chunk

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
    def __init__(self, gateway):
        self.gateway = gateway
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
                await process_chunk(self.gateway.stream, self.gateway, path,
                                    seq, start * 1000 // RATE, end * 1000 // RATE)
            except Exception:
                self.gap(start, end, "processing_error")
            finally:
                if path:
                    path.unlink(missing_ok=True)
                self.queue.task_done()


async def receive_capture(websocket, gateway):
    buffer = CaptureBuffer(gateway)
    worker = asyncio.create_task(buffer.consume())
    disconnected = False
    try:
        await websocket.send_json({"type": "ready", "session": gateway.stream.session.model_dump()})
        while True:
            message = await asyncio.wait_for(websocket.receive(), timeout=15)
            if message['type'] == 'websocket.disconnect':
                disconnected = True
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
        disconnected = True
    finally:
        try:
            await asyncio.wait_for(buffer.queue.join(), timeout=90)
        except asyncio.TimeoutError:
            while not buffer.queue.empty():
                _, start, end, _ = buffer.queue.get_nowait()
                buffer.queue.task_done()
                buffer.gap(start, end, 'processing_error')
        finally:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
            session = gateway.stream.session.model_copy(update={"status": "ended"})
            gateway.publish_nowait(gateway.stream.record_status(session))
            if not disconnected:
                try:
                    await websocket.close()
                except (RuntimeError, WebSocketDisconnect):
                    pass
