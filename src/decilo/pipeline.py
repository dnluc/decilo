"""Worker de sesión: audio (archivo) → STT → traducción → eventos.

Soporta ventanas fijas de referencia y cortes acústicos por pausa con máximo.
El ASR publica cada segmento directamente
como `final`; la traducción permite provisionales opt-in. El ASR sin parciales — el contrato de `caption-stream` contempla explícitamente
que "un proveedor sin parciales puede emitir un resultado definitivo sin
simular incrementalidad".
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import wave
from pathlib import Path
from contextlib import asynccontextmanager, aclosing
from typing import Callable, Iterator

from decilo.gateway import SessionGateway
from decilo.models import CaptionData, GapData
from decilo.stream import SessionStream
from decilo.segmentation import PauseConfig, PauseSegmenter
from decilo.stt import transcribe
from decilo.translate import translate, translate_stream

CHUNK_SECONDS = 5.0


def _iter_chunks(audio_path: Path, chunk_seconds: float) -> Iterator[tuple[Path, int, int]]:
    """Divide un WAV en archivos temporales de duración fija, sin solapar."""
    with wave.open(str(audio_path), "rb") as src:
        rate = src.getframerate()
        channels = src.getnchannels()
        sampwidth = src.getsampwidth()
        n_frames = src.getnframes()
        frames_per_chunk = max(1, int(chunk_seconds * rate))
        offset = 0
        while offset < n_frames:
            src.setpos(offset)
            count = min(frames_per_chunk, n_frames - offset)
            frames = src.readframes(count)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            with wave.open(tmp.name, "wb") as out:
                out.setnchannels(channels)
                out.setsampwidth(sampwidth)
                out.setframerate(rate)
                out.writeframes(frames)
            start_ms = int(offset / rate * 1000)
            end_ms = int((offset + count) / rate * 1000)
            yield Path(tmp.name), start_ms, end_ms
            offset += count


def _iter_pause_chunks(audio_path: Path, config: PauseConfig):
    with wave.open(str(audio_path), 'rb') as src:
        if src.getnchannels() != 1 or src.getsampwidth() != 2:
            raise ValueError('La segmentación por pausas requiere WAV PCM16 mono')
        rate = src.getframerate()
        segmenter = PauseSegmenter(config, rate)

        def save(segment):
            if not segment.has_voice:
                return None, segment.start * 1000 // rate, segment.end * 1000 // rate, segment.reason
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as file:
                path = Path(file.name)
            with wave.open(str(path), 'wb') as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(rate)
                out.writeframes(segment.pcm)
            return path, segment.start * 1000 // rate, segment.end * 1000 // rate, segment.reason

        while pcm := src.readframes(max(1, rate // 50)):
            for segment in segmenter.feed(pcm):
                yield save(segment)
        for segment in segmenter.flush():
            yield save(segment)


async def run_file_session(
    stream: SessionStream, gateway: SessionGateway, audio_path: Path,
    *, started_at: float | None = None,
    observe: Callable[[dict], None] | None = None,
    max_backlog_seconds: float | None = 10.0,
    overlap_translation: bool = False,
    segmentation: PauseConfig | None = None,
) -> None:
    """Recorre un archivo de audio a velocidad real, publicando eventos en `gateway`.

    Un chunk recién está "disponible" cuando transcurrió su intervalo real
    de audio — así se simula una fuente en vivo (micrófono/stream) en vez
    de procesar el archivo completo tan rápido como puedan los modelos.
    Sin esto, la latencia medida no tiene sentido (el pipeline puede
    adelantarse al propio audio).
    """
    loop = asyncio.get_running_loop()
    t_start = loop.time() if started_at is None else started_at
    async with translation_queue(stream, gateway, observe, overlap_translation) as submit:
        chunks = (_iter_pause_chunks(audio_path, segmentation) if segmentation else
                  ((path, start, end, None) for path, start, end in _iter_chunks(audio_path, CHUNK_SECONDS)))
        for segment_seq, (chunk_path, start_ms, end_ms, boundary_reason) in enumerate(chunks, start=1):
            try:
                wait = t_start + end_ms / 1000 - loop.time()
                if wait > 0:
                    await asyncio.sleep(wait)
                if chunk_path is None:
                    continue  # Pautar también silencios sin invocar ASR.
                backlog = loop.time() - (t_start + end_ms / 1000)
                if max_backlog_seconds is not None and backlog > max_backlog_seconds:
                    gateway.publish_nowait(stream.record_gap(GapData(
                        gap_id=f"gap-overload-{segment_seq}", start_ms=start_ms, end_ms=end_ms,
                        reason="overload", discard_captions=[],
                    )))
                    if observe is not None:
                        observe({"session_id": stream.session.id, "segment_seq": segment_seq,
                                 "stage": "discard", "seconds": backlog, "outcome": "overload",
                                 "audio_seconds": (end_ms - start_ms) / 1000})
                    continue
                await process_chunk(
                    stream, gateway, chunk_path, segment_seq, start_ms, end_ms,
                    available_at=t_start + end_ms / 1000, observe=observe,
                    submit_translation=submit, boundary_reason=boundary_reason,
                )
            finally:
                if chunk_path is not None:
                    chunk_path.unlink(missing_ok=True)
    ended_session = stream.session.model_copy(update={"status": "ended"})
    gateway.publish_nowait(stream.record_status(ended_session))


async def process_chunk(
    stream, gateway, chunk_path, segment_seq, start_ms, end_ms, *,
    available_at: float | None = None, observe: Callable[[dict], None] | None = None,
    submit_translation=None, boundary_reason=None, revision=1,
):
    """Consume y elimina un WAV; comparte inferencia entre archivo y captura."""
    loop = asyncio.get_running_loop()
    started = loop.time()

    def report(stage, began, outcome="ok"):
        if observe is not None:
            observe({"session_id": stream.session.id, "segment_seq": segment_seq,
                     "stage": stage, "seconds": loop.time() - began, "outcome": outcome,
                     "audio_seconds": (end_ms - start_ms) / 1000})

    if available_at is not None and observe is not None:
        observe({"session_id": stream.session.id, "segment_seq": segment_seq,
                 "stage": "backlog", "seconds": max(0, started - available_at), "outcome": "ok",
                 "audio_seconds": (end_ms - start_ms) / 1000})
    source_language = stream.session.source_language
    segment_id = f"seg-{segment_seq}"
    try:
        text = await asyncio.to_thread(transcribe, chunk_path, source_language)
        report("asr", started)
    except Exception as exc:
        report("asr", started, "error")
        gateway.publish_nowait(
            stream.record_error("inference_unavailable", f"STT: {exc}", retryable=True)
        )
        gateway.publish_nowait(
            stream.record_gap(
                GapData(
                    gap_id=f"gap-stt-{segment_seq}",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    reason="processing_error",
                    discard_captions=[],
                )
            )
        )
        return
    finally:
        chunk_path.unlink(missing_ok=True)

    if not text.strip():
        # Silencio: no se inventa un subtítulo vacío. Pero si hubo revisiones
        # provisionales de este segmento, no pueden quedar huérfanas como si
        # alguien las hubiera dicho: se retiran con un gap explícito.
        if revision > 1:
            gateway.publish_nowait(stream.record_gap(GapData(
                gap_id=f"gap-empty-{segment_seq}", start_ms=start_ms, end_ms=end_ms,
                reason="processing_error",
                discard_captions=[{"segment_id": segment_id, "kind": "transcript",
                                   "language": source_language}],
            )))
        return

    transcript = CaptionData(
        segment_id=segment_id,
        segment_seq=segment_seq,
        kind="transcript",
        language=source_language,
        # Por encima de las revisiones provisionales ya publicadas: esta es
        # la pasada final que las corrige y confirma.
        revision=revision,
        source_revision=None,
        text=text.strip(),
        status="final",
        start_ms=start_ms,
        end_ms=end_ms, boundary_reason=boundary_reason,
    )
    gateway.publish_nowait(stream.upsert_caption(transcript))

    if submit_translation is None:
        await translate_caption(stream, gateway, transcript, observe)
    elif stream.session.translation_languages:
        await submit_translation(transcript)


def record_timing(observe, stream, caption, stage, began, outcome="ok"):
    if observe is not None:
        observe({"session_id": stream.session.id, "segment_seq": caption.segment_seq,
                 "stage": stage, "seconds": asyncio.get_running_loop().time() - began,
                 "outcome": outcome, "audio_seconds": (caption.end_ms - caption.start_ms) / 1000})


async def translate_caption(stream, gateway, transcript, observe=None):
    loop = asyncio.get_running_loop()
    for target_language in stream.session.translation_languages:
        translation_started = loop.time()
        try:
            if os.environ.get('DECILO_STREAM_TRANSLATION') == '1':
                await _stream_translation(stream, gateway, transcript, target_language, observe)
                record_timing(observe, stream, transcript, "translation", translation_started)
                continue
            translated_text = await translate(transcript.text)
            record_timing(observe, stream, transcript, "translation", translation_started)
        except Exception as exc:
            record_timing(observe, stream, transcript, "translation", translation_started, "error")
            gateway.publish_nowait(
                stream.record_error("inference_unavailable", f"Traducción: {exc}", retryable=True)
            )
            continue
        if not translated_text:
            continue
        translation = CaptionData(
            segment_id=transcript.segment_id,
            segment_seq=transcript.segment_seq,
            kind="translation",
            language=target_language,
            revision=1,
            source_revision=transcript.revision,
            text=translated_text,
            status="final",
            start_ms=transcript.start_ms,
            end_ms=transcript.end_ms, boundary_reason=transcript.boundary_reason,
        )
        gateway.publish_nowait(stream.upsert_caption(translation))


async def _stream_translation(stream, gateway, transcript, language, observe):
    """Stage B: stream translations of final originals without changing v1."""
    if transcript.status != 'final':
        raise ValueError('La etapa B requiere original confirmado')
    loop = asyncio.get_running_loop()
    began = loop.time()
    last_emitted = None
    last_text = None
    revision = 0
    # Explicit close releases HTTP resources even on cancellation/upsert failure.
    async with aclosing(translate_stream(transcript.text)) as updates:
        async for update in updates:
            now = loop.time()
            if not update.final and (update.text == last_text or
                    (last_emitted is not None and now - last_emitted < .3)):
                continue
            revision += 1
            caption = CaptionData(
                segment_id=transcript.segment_id, segment_seq=transcript.segment_seq,
                kind='translation', language=language, revision=revision,
                source_revision=transcript.revision, text=update.text,
                status='final' if update.final else 'provisional',
                start_ms=transcript.start_ms, end_ms=transcript.end_ms,
                boundary_reason=transcript.boundary_reason,
            )
            event = stream.upsert_caption(caption)
            if event is None:
                return  # Original retired/evicted; do not resurrect it.
            gateway.publish_nowait(event)
            if last_emitted is None:
                record_timing(observe, stream, transcript, 'translation_first_content', began)
            last_emitted, last_text = now, update.text
            if update.metrics is not None and observe is not None:
                observe({'session_id': stream.session.id, 'segment_seq': transcript.segment_seq,
                         'stage': 'ollama', 'outcome': 'ok', 'metrics': update.metrics})


@asynccontextmanager
async def translation_queue(stream, gateway, observe, enabled):
    """Experiment: two pending texts + one translation in flight per session.

    A full queue backpressures ASR; it never spawns unbounded model requests.
    Drain before ended; cancel on session failure/cancellation.
    """
    if not enabled or not stream.session.translation_languages:
        yield None
        return
    queue = asyncio.Queue(maxsize=2)
    loop = asyncio.get_running_loop()

    async def submit(caption):
        began = loop.time()
        await queue.put((caption, began))
        record_timing(observe, stream, caption, "translation_backpressure", began)

    async def consume():
        while True:
            caption, queued_at = await queue.get()
            try:
                record_timing(observe, stream, caption, "translation_queue", queued_at)
                await translate_caption(stream, gateway, caption, observe)
            except Exception:
                gateway.publish_nowait(stream.record_error(
                    "inference_unavailable", "Falló la traducción en cola.", retryable=True,
                ))
            finally:
                queue.task_done()

    worker = asyncio.create_task(consume())
    try:
        yield submit
        await queue.join()
    finally:
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
