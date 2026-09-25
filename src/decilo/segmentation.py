"""Incremental pause boundaries, not semantic understanding.

PCM16 mono; one 20ms analysis frame plus at most max_seconds of audio retained.
Every sample is preserved. Long continuous speech is cut with reason deadline.
"""
from dataclasses import dataclass
import math
import os
import struct


@dataclass(frozen=True)
class PauseConfig:
    min_seconds: float = 1.0
    pause_seconds: float = 0.4
    max_seconds: float = 6.0
    silence_rms: float = 0.01

    def __post_init__(self):
        values = (self.min_seconds, self.pause_seconds, self.max_seconds, self.silence_rms)
        if not all(math.isfinite(x) for x in values):
            raise ValueError('La configuración de segmentación debe ser finita')
        if not .5 <= self.min_seconds <= self.max_seconds <= 15:
            raise ValueError('Segmentos: 0.5 <= mínimo <= máximo <= 15 segundos')
        if not .1 <= self.pause_seconds <= self.max_seconds:
            raise ValueError('Pausa fuera de rango')
        if not 0 < self.silence_rms < 1:
            raise ValueError('RMS debe estar entre 0 y 1')


def configured_segmentation():
    mode = os.environ.get('DECILO_SEGMENTATION', 'pause')
    if mode == 'fixed':
        return None
    if mode != 'pause':
        raise ValueError('DECILO_SEGMENTATION debe ser pause o fixed')
    return PauseConfig(
        min_seconds=float(os.environ.get('DECILO_MIN_SEGMENT_SECONDS', '1')),
        pause_seconds=float(os.environ.get('DECILO_PAUSE_SECONDS', '.4')),
        max_seconds=float(os.environ.get('DECILO_MAX_SEGMENT_SECONDS', '6')),
        silence_rms=float(os.environ.get('DECILO_SILENCE_RMS', '.01')),
    )


@dataclass(frozen=True)
class AudioSegment:
    pcm: bytes
    start: int
    end: int
    reason: str | None
    has_voice: bool


class PauseSegmenter:
    def __init__(self, config: PauseConfig, rate: int = 16000, start: int = 0):
        self.config = config
        self.rate = rate
        self.start = start
        self.frame_samples = max(1, round(rate * .02))
        self.max_samples = round(rate * config.max_seconds)
        self.min_samples = round(rate * config.min_seconds)
        self.pause_samples = round(rate * config.pause_seconds)
        self.pending = bytearray()
        self.audio = bytearray()
        self.silence = 0
        self.has_voice = False

    def _frame(self, frame):
        samples = struct.unpack(f'<{len(frame)//2}h', frame)
        voiced = sum(x*x for x in samples) > len(samples) * (self.config.silence_rms * 32768)**2
        self.has_voice |= voiced
        self.silence = 0 if voiced else self.silence + len(samples)
        self.audio.extend(frame)
        length = len(self.audio) // 2
        if length >= self.max_samples:
            return self._emit('deadline')
        if length >= self.min_samples and self.has_voice and self.silence >= self.pause_samples:
            return self._emit('pause')
        return None

    def _emit(self, reason):
        segment = AudioSegment(bytes(self.audio), self.start,
                               self.start + len(self.audio)//2, reason, self.has_voice)
        self.start = segment.end
        self.audio.clear()
        self.silence = 0
        self.has_voice = False
        return segment

    def feed(self, pcm):
        if len(pcm) % 2:
            raise ValueError('PCM16 incompleto')
        # Input messages are bounded by the caller; emit incrementally across packets.
        self.pending.extend(pcm)
        offset = 0
        while len(self.pending) - offset >= 2 * min(self.frame_samples, self.max_samples - len(self.audio)//2):
            size = 2 * min(self.frame_samples, self.max_samples - len(self.audio)//2)
            frame = self.pending[offset:offset+size]
            offset += size
            segment = self._frame(frame)
            if segment is not None:
                yield segment
        del self.pending[:offset]

    def flush(self, reason='end_of_stream'):
        result = []
        if self.pending:
            segment = self._frame(self.pending)
            self.pending.clear()
            if segment is not None:
                result.append(segment)
        if self.audio:
            result.append(self._emit(reason))
        return result

    def open_snapshot(self):
        """Estado del segmento abierto, para transcripción provisional.

        Devuelve (inicio_en_muestras, pcm, tiene_voz) del audio acumulado que
        todavía no cerró. El PCM es una copia: el buffer sigue creciendo.
        """
        return self.start, bytes(self.audio), self.has_voice

    def split_open(self, end_samples):
        """Cierra el segmento abierto hasta la muestra absoluta dada.

        Para cortes inferidos por texto: la transcripción provisional oyó un
        final de oración, así que no hace falta esperar la pausa acústica ni
        el tope de duración. El audio posterior al corte queda como inicio
        del siguiente segmento; ninguna muestra se pierde."""
        samples = end_samples - self.start
        if samples < self.min_samples or samples * 2 > len(self.audio):
            return None
        segment = AudioSegment(bytes(self.audio[:samples * 2]), self.start,
                               end_samples, 'pause', self.has_voice)
        del self.audio[:samples * 2]
        self.start = end_samples
        # La cuenta de silencio final sigue valiendo (es el final del audio
        # retenido); la voz del resto se recalcula sobre lo que quedó.
        self.has_voice = self._voiced(bytes(self.audio))
        return segment

    def _voiced(self, pcm):
        gate = (self.config.silence_rms * 32768) ** 2
        for i in range(0, len(pcm), self.frame_samples * 2):
            samples = struct.unpack(f'<{len(pcm[i:i + self.frame_samples * 2]) // 2}h',
                                    pcm[i:i + self.frame_samples * 2])
            if samples and sum(x * x for x in samples) > len(samples) * gate:
                return True
        return False
