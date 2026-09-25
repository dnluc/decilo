"""Bounded PCM ingress; no video or arbitrary file paths accepted."""
import asyncio
import math
import struct
import tempfile
import wave
from pathlib import Path

from starlette.websockets import WebSocketDisconnect

import os

from decilo.models import GapData
from decilo.partials import PartialTranscriber
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
    def __init__(self, gateway, submit_translation=None, segmentation=None, partials=None):
        self.gateway = gateway
        self.submit_translation = submit_translation
        self.segmentation = segmentation
        self.segmenter = PauseSegmenter(segmentation) if segmentation else None
        # La identidad del segmento (seq) se asigna por su inicio en muestras,
        # no al cerrarse: las revisiones provisionales y la pasada final tienen
        # que compartir el mismo segment_id.
        self.partials = partials
        self._seqs = {}
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
            if self.partials:
                self.partials.observe(*self.segmenter.open_snapshot())
        else:
            self.enqueue(AudioSegment(pcm, start, end, None, True))

    def finish(self):
        if self.segmenter:
            for segment in self.segmenter.flush():
                self.enqueue(segment)

    def seq_for(self, start):
        if start not in self._seqs:
            self.seq += 1
            self._seqs[start] = self.seq
        return self._seqs[start]

    def enqueue(self, segment):
        # Cerrar ANTES de encolar: desde acá ninguna provisional del segmento
        # puede publicarse, así la revisión de la pasada final queda estable.
        revision = self.partials.close(segment.start) if self.partials else 1
        if not segment.has_voice:
            self._seqs.pop(segment.start, None)
            return
        seq = self.seq_for(segment.start)
        self._seqs.pop(segment.start, None)
        duration = segment.end - segment.start
        while self.queue.full() or self.queued_samples + duration > self.budget_samples:
            _, old_start, old_end, _, _, _ = self.queue.get_nowait()
            self.queued_samples -= old_end - old_start
            self.queue.task_done()
            self.gap(old_start, old_end, "overload")
        self.queue.put_nowait((seq, segment.start, segment.end, segment.pcm, segment.reason, revision))
        self.queued_samples += duration

    async def consume(self):
        while True:
            seq, start, end, pcm, reason, revision = await self.queue.get()
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
                                    seq, start * 1000 // RATE, end * 1000 // RATE,
                                    revision=revision, **options)
            except Exception:
                self.gap(start, end, "processing_error")
            finally:
                if path:
                    path.unlink(missing_ok=True)
                self.queue.task_done()


async def _receive_audio(websocket, gateway, submit, deadline, segmentation, prebuffered=()):
    partials = None
    if segmentation and os.environ.get('DECILO_PARTIALS', '1') == '1':
        partials = PartialTranscriber(
            gateway.stream, gateway,
            seq_for=None,  # se resuelve abajo: necesita el buffer
            language=gateway.stream.session.source_language,
        )
    buffer = CaptureBuffer(gateway, submit, segmentation, partials)
    if partials:
        partials.seq_for = buffer.seq_for
    worker = asyncio.create_task(buffer.consume())
    partial_worker = asyncio.create_task(partials.worker()) if partials else None
    try:
        await websocket.send_json({"type": "ready", "session": gateway.stream.session.model_dump()})
        for packet in prebuffered:
            buffer.add(packet)
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
                _, start, end, _, _, _ = buffer.queue.get_nowait()
                buffer.queued_samples -= end - start
                buffer.queue.task_done()
                buffer.gap(start, end, 'processing_error')
            raise
        finally:
            if partial_worker:
                partial_worker.cancel()
                await asyncio.gather(partial_worker, return_exceptions=True)
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)


async def _start_live(gateway, submit):
    """Nube: transcripción en streaming contra Gemini Live si se puede.

    Devuelve el transcriptor conectado, o None para seguir por segmentos
    (proveedor local, camino desactivado, o Google no contestó)."""
    from decilo import gemini_live
    from decilo.providers import provider

    if provider('stt') != 'gemini' or not gemini_live.live_enabled():
        return None
    live = gemini_live.GeminiLiveTranscriber(
        gateway, submit, gateway.stream.session.source_language)
    try:
        await live.connect()
        return live
    except Exception as error:
        gateway.publish_nowait(gateway.stream.record_error(
            'inference_unavailable',
            f'Gemini Live no disponible ({error}); se sigue por segmentos.',
            retryable=True,
        ))
        return None


async def _receive_audio_live(websocket, gateway, live, deadline, prebuffered=()):
    """Cada paquete del navegador va directo a Gemini; acá solo se validan
    offsets y se registran huecos. Las captions las publica el lector."""
    last_end = 0
    gaps = 0

    def add(packet):
        nonlocal last_end, gaps
        start, end, pcm = decode_packet(packet, last_end)
        if start > last_end:
            gaps += 1
            gateway.publish_nowait(gateway.stream.record_gap(GapData(
                gap_id=f"capture-gap-{gaps}", start_ms=last_end * 1000 // RATE,
                end_ms=start * 1000 // RATE, reason="source_disconnect",
                discard_captions=[],
            )))
        last_end = end
        return pcm

    try:
        await websocket.send_json({"type": "ready", "session": gateway.stream.session.model_dump()})
        for packet in prebuffered:
            await live.feed(add(packet))
        while True:
            message = await asyncio.wait_for(websocket.receive(), timeout=15)
            if message['type'] == 'websocket.disconnect':
                break
            if message.get('text') == 'stop':
                break
            if message.get('bytes') is None:
                raise ValueError('Se esperaba PCM binario o stop')
            await live.feed(add(message['bytes']))
    except (ValueError, asyncio.TimeoutError) as error:
        gateway.publish_nowait(gateway.stream.record_error(
            'inference_unavailable', str(error) or 'Captura sin audio durante 15 segundos', retryable=False,
        ))
    except WebSocketDisconnect:
        pass
    except Exception as error:  # enlace con Gemini irrecuperable
        gateway.publish_nowait(gateway.stream.record_error(
            'inference_unavailable', f'Gemini Live: {error}', retryable=False,
        ))
    finally:
        deadline.reschedule(asyncio.get_running_loop().time() + 90)
        await live.finish()


VOICE_RMS_GATE = (0.01 * 32768) ** 2


async def detect_capture_language(websocket):
    """Junta audio hasta poder detectar el idioma; devuelve (idioma, paquetes).

    La sesión no puede crearse sin idioma (el contrato lo exige), y el idioma
    no puede detectarse sin audio: esta fase intermedia recibe paquetes antes
    de que exista la sesión y los conserva para que no se pierda ni una
    muestra. Corta al juntar ~2.5s con voz, o a los 12s de audio total.
    """
    import struct as _struct

    from decilo.stt import detect_language

    packets, voiced, total, last_end = [], 0, 0, 0
    while voiced < RATE * 2.5 and total < RATE * 12:
        message = await asyncio.wait_for(websocket.receive(), timeout=15)
        if message['type'] == 'websocket.disconnect':
            return None
        if message.get('text') == 'stop':
            return None
        if message.get('bytes') is None:
            raise ValueError('Se esperaba PCM binario o stop')
        start, end, pcm = decode_packet(message['bytes'], last_end)
        last_end = end
        packets.append(message['bytes'])
        total += len(pcm) // 2
        samples = _struct.unpack(f'<{len(pcm) // 2}h', pcm)
        if samples and sum(x * x for x in samples) > len(samples) * VOICE_RMS_GATE:
            voiced += len(samples)
    pcm = b''.join(packet[4:] for packet in packets)
    language = await asyncio.to_thread(detect_language, pcm)
    return language, packets


async def receive_capture(websocket, gateway, *, overlap_translation=False, segmentation=None,
                          prebuffered=()):
    try:
        async with asyncio.timeout(None) as deadline:
            async with translation_queue(gateway.stream, gateway, None, overlap_translation) as submit:
                live = await _start_live(gateway, submit)
                if live is not None:
                    await _receive_audio_live(websocket, gateway, live, deadline, prebuffered)
                else:
                    await _receive_audio(websocket, gateway, submit, deadline, segmentation, prebuffered)
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
