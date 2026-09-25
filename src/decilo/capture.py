"""Bounded PCM ingress; no video or arbitrary file paths accepted."""
import asyncio
import math
import struct
import tempfile
import wave
from pathlib import Path

from starlette.websockets import WebSocketDisconnect

from decilo.models import GapData
from decilo.segmentation import AudioSegment, PauseSegmenter
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
    def __init__(self, gateway, submit_translation=None, segmentation=None):
        self.gateway = gateway
        self.submit_translation = submit_translation
        self.segmentation = segmentation
        self.segmenter = PauseSegmenter(segmentation) if segmentation else None
        self.budget_samples = round(2 * segmentation.max_seconds * RATE) if segmentation else 2 * MAX_SAMPLES
        capacity = math.ceil(2 * segmentation.max_seconds / segmentation.min_seconds) + 1 if segmentation else 2
        self.queue = asyncio.Queue(maxsize=capacity)
        self.queued_samples = 0
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
            self.finish()
            self.gap(self.last_end, start, "source_disconnect")
            if self.segmenter:
                self.segmenter = PauseSegmenter(self.segmentation, start=start)
        self.last_end = end
        if self.segmenter:
            for segment in self.segmenter.feed(pcm):
                self.enqueue(segment)
        else:
            self.enqueue(AudioSegment(pcm, start, end, None, True))

    def finish(self):
        if self.segmenter:
            for segment in self.segmenter.flush():
                self.enqueue(segment)

    def enqueue(self, segment):
        if not segment.has_voice:
            return
        self.seq += 1
        duration = segment.end - segment.start
        while self.queue.full() or self.queued_samples + duration > self.budget_samples:
            _, old_start, old_end, _, _ = self.queue.get_nowait()
            self.queued_samples -= old_end - old_start
            self.queue.task_done()
            self.gap(old_start, old_end, "overload")
        self.queue.put_nowait((self.seq, segment.start, segment.end, segment.pcm, segment.reason))
        self.queued_samples += duration

    async def consume(self):
        while True:
            seq, start, end, pcm, reason = await self.queue.get()
            self.queued_samples -= end - start
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
                if reason is not None:
                    options["boundary_reason"] = reason
                await process_chunk(self.gateway.stream, self.gateway, path,
                                    seq, start * 1000 // RATE, end * 1000 // RATE, **options)
            except Exception:
                self.gap(start, end, "processing_error")
            finally:
                if path:
                    path.unlink(missing_ok=True)
                self.queue.task_done()


async def _receive_audio(websocket, gateway, submit, deadline, segmentation):
    buffer = CaptureBuffer(gateway, submit, segmentation)
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
        buffer.finish()
        try:
            await buffer.queue.join()
        except asyncio.CancelledError:
            while not buffer.queue.empty():
                _, start, end, _, _ = buffer.queue.get_nowait()
                buffer.queued_samples -= end - start
                buffer.queue.task_done()
                buffer.gap(start, end, 'processing_error')
            raise
        finally:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)


async def receive_capture(websocket, gateway, *, overlap_translation=False, segmentation=None):
    try:
        async with asyncio.timeout(None) as deadline:
            async with translation_queue(gateway.stream, gateway, None, overlap_translation) as submit:
                await _receive_audio(websocket, gateway, submit, deadline, segmentation)
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
