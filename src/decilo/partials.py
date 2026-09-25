"""Transcripción provisional del segmento abierto: el texto aparece mientras
se habla y la pasada final lo corrige al cerrar la frase.

Cada vez que el segmento abierto crece lo suficiente, se re-transcribe una
copia de su audio y se publica como revisión provisional del MISMO segmento
que después confirmará la pasada final. El contrato ya soporta esto: las
revisiones reemplazan texto, el final es inmutable.

Presupuesto: hay a lo sumo UNA transcripción provisional en vuelo, y si el
audio creció mientras corría, solo se conserva la instantánea más nueva (la
del medio quedó vieja antes de nacer). Las provisionales usan beam_size=1:
son un anticipo barato; la calidad la pone la pasada final con beam completo.
"""

from __future__ import annotations

import asyncio

from decilo.models import CaptionData
from decilo.stt import transcribe_segments

RATE = 16000
# No transcribir aperturas minúsculas (nada útil que mostrar) ni re-transcribir
# por cada paquete de 100ms: el costo en CPU no acompañaría.
MIN_OPEN_SECONDS = 0.8
MIN_GROWTH_SECONDS = 0.5
# Corte por texto: si dentro de la provisional una oración terminó Y la
# siguiente ya empezó, se corta en el límite exacto (timestamp del segmento
# de Whisper) sin esperar la pausa acústica. Con orador rápido, la pausa
# puede no llegar nunca antes del tope de 6s y las oraciones se apilaban.
# Nunca se corta por el punto FINAL del texto: Whisper suele puntuar
# cualquier hipótesis a medias y eso cortaba palabras al medio.
SENTENCE_MIN_SECONDS = 2.0
SENTENCE_ENDINGS = ('.', '!', '?', '…')


def ends_sentence(text: str) -> bool:
    text = text.rstrip().rstrip('"\')]')
    # Un número al final ("versión 3.5") no es un punto final de oración.
    return (len(text) >= 12 and text.endswith(SENTENCE_ENDINGS)
            and not text[-2:-1].isdigit())


class PartialTranscriber:
    def __init__(self, stream, gateway, seq_for, language, on_sentence=None):
        self.stream = stream
        self.gateway = gateway
        self.seq_for = seq_for  # el buffer asigna la identidad del segmento
        self.language = language
        self.on_sentence = on_sentence  # avisa al buffer para cortar ahí
        self._latest: tuple[int, bytes] | None = None
        self._wake = asyncio.Event()
        self._snapshotted: dict[int, int] = {}  # start -> muestras ya instantaneadas
        self._revisions: dict[int, int] = {}    # start -> última revisión publicada
        self._last_text: dict[int, str] = {}    # start -> último texto publicado
        self._closed: set[int] = set()

    def observe(self, start: int, pcm: bytes, has_voice: bool) -> None:
        """Llamado en cada paquete con el estado del segmento abierto."""
        if not has_voice or start in self._closed:
            return
        samples = len(pcm) // 2
        if samples < RATE * MIN_OPEN_SECONDS:
            return
        if samples - self._snapshotted.get(start, 0) < RATE * MIN_GROWTH_SECONDS:
            return
        self._snapshotted[start] = samples
        self._latest = (start, pcm)  # la más nueva reemplaza a la pendiente
        self._wake.set()

    def close(self, start: int) -> int:
        """El segmento cerró: ninguna provisional posterior debe publicarse.

        Devuelve la revisión que corresponde a la pasada final (una más que
        la última provisional publicada).
        """
        self._closed.add(start)
        if self._latest is not None and self._latest[0] == start:
            self._latest = None
        self._snapshotted.pop(start, None)
        self._last_text.pop(start, None)
        return self._revisions.pop(start, 0) + 1

    async def worker(self) -> None:
        while True:
            await self._wake.wait()
            self._wake.clear()
            while self._latest is not None:
                start, pcm = self._latest
                self._latest = None
                try:
                    segments = await asyncio.to_thread(
                        transcribe_pcm, pcm, self.language, beam_size=1,
                    )
                except Exception:
                    continue  # la pasada final va a cubrir este audio igual
                text = ' '.join(part for part, _end in segments)
                # Sin await entre el chequeo y la publicación: si el segmento
                # cerró mientras se transcribía, este texto ya es viejo y la
                # revisión final podría chocar con su número.
                if start in self._closed or not text.strip():
                    continue
                if text.strip() == self._last_text.get(start):
                    continue  # nada nuevo que mostrar: ni revisión ni render
                self._last_text[start] = text.strip()
                revision = self._revisions.get(start, 0) + 1
                self._revisions[start] = revision
                seq = self.seq_for(start)
                self.gateway.publish_nowait(self.stream.upsert_caption(CaptionData(
                    segment_id=f"seg-{seq}",
                    segment_seq=seq,
                    kind="transcript",
                    language=self.language,
                    revision=revision,
                    source_revision=None,
                    text=text.strip(),
                    status="provisional",
                    start_ms=start * 1000 // RATE,
                    end_ms=(start + len(pcm) // 2) * 1000 // RATE,
                )))
                # Límite interno de oración: una terminó y la siguiente ya
                # empezó (hay otro segmento de Whisper después). Se corta en
                # el timestamp exacto del límite; el corte cierra este start
                # y lo que siga arranca un segmento nuevo. El último segmento
                # de Whisper nunca dispara: su puntito puede ser fantasma.
                if self.on_sentence is not None and len(segments) >= 2:
                    cut, accumulated = None, ''
                    for part, part_end in segments[:-1]:
                        accumulated = f'{accumulated} {part}'.strip()
                        if ends_sentence(accumulated):
                            cut = part_end
                    if cut is not None and cut >= SENTENCE_MIN_SECONDS:
                        self.on_sentence(start, start + int(cut * RATE))


def transcribe_pcm(pcm: bytes, language: str, *, beam_size: int) -> list[tuple[str, float]]:
    """PCM crudo → [(texto, fin_s)] por segmento de Whisper, vía WAV temporal."""
    import tempfile
    import wave
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as file:
        path = Path(file.name)
    try:
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes(pcm)
        # Modelo chico: el anticipo tiene que llegar antes que la frase
        # siguiente; la calidad la pone la pasada final con el modelo grande.
        return transcribe_segments(path, language, beam_size=beam_size, fast=True)
    finally:
        path.unlink(missing_ok=True)
