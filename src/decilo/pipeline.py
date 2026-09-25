"""Worker de sesión: audio (archivo) → STT → traducción → eventos.

v1 usa chunks de duración fija (no VAD) y publica cada chunk directamente
como `final` — el contrato de `caption-stream` contempla explícitamente
que "un proveedor sin parciales puede emitir un resultado definitivo sin
simular incrementalidad".
"""

from __future__ import annotations

import asyncio
import tempfile
import wave
from pathlib import Path
from typing import Iterator

from decilo.gateway import SessionGateway
from decilo.models import CaptionData, GapData
from decilo.stream import SessionStream
from decilo.stt import transcribe
from decilo.translate import translate

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


async def run_file_session(
    stream: SessionStream, gateway: SessionGateway, audio_path: Path,
    *, started_at: float | None = None,
) -> None:
    """Recorre un archivo de audio a velocidad real, publicando eventos en `gateway`.

    Un chunk recién está "disponible" cuando transcurrió su intervalo real
    de audio — así se simula una fuente en vivo (micrófono/stream) en vez
    de procesar el archivo completo tan rápido como puedan los modelos.
    Sin esto, la latencia medida no tiene sentido (el pipeline puede
    adelantarse al propio audio).
    """
    source_language = stream.session.source_language
    translation_languages = stream.session.translation_languages
    segment_seq = 0
    loop = asyncio.get_running_loop()
    # Optional origin uses this event loop’s monotonic clock (never wall time).
    t_start = loop.time() if started_at is None else started_at

    for chunk_path, start_ms, end_ms in _iter_chunks(audio_path, CHUNK_SECONDS):
        segment_seq += 1
        segment_id = f"seg-{segment_seq}"
        try:
            wait = t_start + end_ms / 1000 - loop.time()
            if wait > 0:
                await asyncio.sleep(wait)
            text = await asyncio.to_thread(transcribe, chunk_path, source_language)
        except Exception as exc:
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
            continue
        finally:
            chunk_path.unlink(missing_ok=True)

        if not text.strip():
            continue  # silencio: no se inventa un subtítulo vacío

        transcript = CaptionData(
            segment_id=segment_id,
            segment_seq=segment_seq,
            kind="transcript",
            language=source_language,
            revision=1,
            source_revision=None,
            text=text.strip(),
            status="final",
            start_ms=start_ms,
            end_ms=end_ms,
        )
        gateway.publish_nowait(stream.upsert_caption(transcript))

        for target_language in translation_languages:
            try:
                translated_text = await translate(text.strip())
            except Exception as exc:
                gateway.publish_nowait(
                    stream.record_error("inference_unavailable", f"Traducción: {exc}", retryable=True)
                )
                continue
            if not translated_text:
                continue
            translation = CaptionData(
                segment_id=segment_id,
                segment_seq=segment_seq,
                kind="translation",
                language=target_language,
                revision=1,
                source_revision=1,
                text=translated_text,
                status="final",
                start_ms=start_ms,
                end_ms=end_ms,
            )
            gateway.publish_nowait(stream.upsert_caption(translation))

    ended_session = stream.session.model_copy(update={"status": "ended"})
    gateway.publish_nowait(stream.record_status(ended_session))
